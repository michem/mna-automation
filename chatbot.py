import json
import os
import shutil
import time
from datetime import datetime

import streamlit as st
from openai import OpenAI
from smolagents import CodeAgent, LiteLLMModel, ToolCallingAgent

from agent1 import managed_strategist
from agent2 import managed_critic, managed_researcher
from agent3n4 import managed_analyst
from agent5 import managed_valuator
from config import MODEL_API_KEY, MODEL_ID
from prompts import RESEARCHER_PROMPT
from run import MANAGER_PROMPT, manager
from tools import get_companies, get_options, read_from_markdown, save_to_json

# Define paths for directories
outputs_dir = "outputs"
fmp_data_dir = os.path.join(outputs_dir, "fmp_data")
valuation_dir = os.path.join(fmp_data_dir, "valuation")
metrics_dir = os.path.join(fmp_data_dir, "metrics")

# Create 'outputs/fmp_data/', 'outputs/fmp_data/valuation', and 'outputs/fmp_data/metrics' directories if they don't exist
os.makedirs(valuation_dir, exist_ok=True)
os.makedirs(metrics_dir, exist_ok=True)

# Initialize the LiteLLM model
model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.4,
)

# Initialize the multiagent
agent = manager


class MAStrategyBot:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []
        self.thread_id = None
        self.assistant_id = None
        self.current_stage = "industry"

        # Initialize the state dictionary to store collected information
        self.collected_info = {
            "industry": None,
            "specific_company": None,
            "goals": None,
            "budget": None,
            "timeline": None,
            "financial_health": None,
            "market_position": None,
            "risks_concern": None,
            "risks_details": None,
        }

        # Define the system instructions
        self.system_instructions = """You are an M&A strategy consultant chatbot. Your role is to gather specific information in a sequential order and maintain a state of collected information.

1. First, determine if they have a specific target company or industry
2. Then, understand their goals for the M&A
3. Next, get their budget information
4. Finally, get their timeline
5. Additionally, ask about the financial health, market position, and any concerns regarding risks of their target company.

Current question stages:
- industry: Ask if they have a specific company in mind or if they're targeting a market/sector
- goals: Ask about their primary goals for this M&A
- budget: Ask about their budget range
- timeline: Ask about their expected timeline
- financial_health: Ask about the financial health of the target company
- market_position: Ask about the market position of the target company
- risks: Ask if they have any concerns regarding risks involved in the acquisition or partnership

For each response:
- Extract the relevant information from the user's response
- If the user answers multiple questions in one response then update those in the json. Do not ask again to confirm their response.
- Only ask again if critical information is completely missing
- Be decisive in interpretation - if you can reasonably extract the required information, consider it complete
- Move to the next stage as soon as you have any reasonable understanding of the current topic
- Don't ask for clarification or confirmation unless the answer is completely unclear
- Don't ask multiple things at once

Response format:
{
    "answer_complete": true/false,
    "current_stage": "industry/goals/budget/timeline/financial_health/market_position/risks",
    "collected_info": {
        "industry": "extracted market info or null",
        "specific_company": "extracted company info or null",
        "goals": "extracted goals or null",
        "budget": "extracted budget or null",
        "timeline": "extracted timeline or null",
        "financial_health": "extracted financial health or null",
        "market_position": "extracted market position or null",
        "risks_concern": "extracted risks concern or null",
        "risks_details": "extracted risk details or null"
    },
    "next_message": "your next message to the user"
}

Always respond in this JSON format. Be decisive and direct - if you can extract meaningful information from a response, accept it and move forward rather than asking for clarification or confirmation."""

        self._initialize_assistant()
        os.makedirs("outputs", exist_ok=True)

    def _initialize_assistant(self):
        self.assistant = self.client.beta.assistants.create(
            name="M&A Strategy Consultant",
            instructions=self.system_instructions,
            model="gpt-4-turbo-preview",
            temperature=0.4,
        )
        self.assistant_id = self.assistant.id
        thread = self.client.beta.threads.create()
        self.thread_id = thread.id

    def save_strategy_info(self):
        # Save the collected information as JSON
        with open("outputs/strategy_info.json", "w") as f:
            json.dump(self.collected_info, f, indent=4)
        return "outputs/strategy_info.json"

    def get_bot_response(self, user_message=None):
        if user_message:
            # Add the user's message to the thread
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=f"Current stage: {self.current_stage}\nCurrent state: {json.dumps(self.collected_info)}\nUser message: {user_message}",
            )

            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread_id, assistant_id=self.assistant_id
            )

            # Wait for the response
            while True:
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread_id, run_id=run.id
                )
                if run_status.status == "completed":
                    break
                time.sleep(0.5)

            # Get the latest message
            messages = self.client.beta.threads.messages.list(thread_id=self.thread_id)
            latest_message = messages.data[0].content[0].text.value

            try:
                # Parse the JSON response
                response_data = json.loads(latest_message)

                # Update the collected information
                self.collected_info.update(response_data["collected_info"])

                # Update the current stage if the answer was complete
                if response_data["answer_complete"]:
                    if self.current_stage == "industry":
                        self.current_stage = "goals"
                    elif self.current_stage == "goals":
                        self.current_stage = "budget"
                    elif self.current_stage == "budget":
                        self.current_stage = "timeline"
                    elif self.current_stage == "timeline":
                        self.current_stage = "financial_health"
                    elif self.current_stage == "financial_health":
                        self.current_stage = "market_position"
                    elif self.current_stage == "market_position":
                        self.current_stage = "risks"
                    elif self.current_stage == "risks":
                        self.current_stage = "complete"

                return response_data["next_message"]
            except json.JSONDecodeError:
                return "I apologize, but I encountered an error. Could you please repeat your last message?"
        else:
            # Initial message
            return "Hello! To begin our M&A strategy discussion, do you have a specific company in mind for acquisition, or are you targeting a particular market or sector?"


def print_directory_structure(startpath, output_container=None):
    """Print the directory structure starting from startpath"""
    structure = []
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, "").count(os.sep)
        indent = "│   " * level
        structure.append(f"{indent}└── {os.path.basename(root)}/")
        subindent = "│   " * (level + 1)
        for f in files:
            structure.append(f"{subindent}└── {f}")

    structure_text = "\n".join(structure)
    if output_container:
        output_container.text(f"Directory Structure:\n{structure_text}")
    return structure_text


def main():
    st.title("M&A Strategy Assessment System")
    st.write("Let's discuss your merger and acquisition strategy.")
    # dir_container = st.empty()
    # print_directory_structure("outputs", dir_container)

    # Initialize session states
    if "bot" not in st.session_state:
        st.session_state.bot = MAStrategyBot()
        # Print initial directory structure

    if "conversation_ended" not in st.session_state:
        st.session_state.conversation_ended = False
    if "analysis_started" not in st.session_state:
        st.session_state.analysis_started = False

    bot = st.session_state.bot

    # Display conversation history
    for message in bot.conversation_history:
        if message["role"] == "bot":
            st.write(f"🤖 Bot: {message['text']}")
        else:
            st.write(f"👤 You: {message['text']}")

    # If conversation hasn't ended, show input field
    if not st.session_state.conversation_ended:
        # Get initial message if conversation is just starting
        if not bot.conversation_history:
            initial_message = bot.get_bot_response()
            bot.conversation_history.append({"role": "bot", "text": initial_message})
            st.rerun()

        # Get user input
        user_input = st.text_input("Your response:", key="user_input")

        if st.button("Submit"):
            if user_input:
                # Add user message to history
                bot.conversation_history.append({"role": "user", "text": user_input})

                # Get bot response
                bot_response = bot.get_bot_response(user_input)

                # Add bot response to history
                bot.conversation_history.append({"role": "bot", "text": bot_response})

                # Check if we've completed all stages
                if bot.current_stage == "complete":
                    st.session_state.conversation_ended = True

                st.rerun()

    else:
        if not st.session_state.analysis_started:
            # Save strategy information
            filename = bot.save_strategy_info()

            st.success(f"Thank you! Strategy information has been saved to: {filename}")

            # Print updated directory structure
            # dir_container = st.empty()
            # print_directory_structure("outputs", dir_container)

            # Display the collected information
            st.json(bot.collected_info)

            # Add a button to start the analysis
            if st.button("Generate Strategy Analysis"):
                st.session_state.analysis_started = True
                st.rerun()

        else:
            if not st.session_state.get("analysis_complete", False):
                # Create a container for the analysis output
                analysis_container = st.empty()
                analysis_container.write("Running strategy analysis...")

                # Run the multiagent analysis
                result = agent.run(MANAGER_PROMPT, stream=True)

                analysis_container.empty()

                # Store results in session state
                valuation_file = "outputs/valuation.md"
                st.session_state.analysis_results = []
                files_already_written = (
                    False  # Flag to track if we've written the files
                )

                for step in result:
                    if not files_already_written and os.path.exists(
                        "outputs/critic_companies.json"
                    ):
                        with open("outputs/critic_companies.json", "r") as f:
                            companies_data = json.load(f)

                        # Create array of expected valuation files
                        valuation_files = [
                            f"outputs/fmp_data/valuation/{company['symbol']}_valuation.md"
                            for company in companies_data
                        ]

                        # Check if all valuation files exist
                        if all(os.path.exists(file) for file in valuation_files):
                            # Display existing valuation files
                            for file in valuation_files:
                                with open(file, "r") as f:
                                    st.write(f.read())
                            files_already_written = (
                                True  # Set flag to prevent future writes
                            )
                            continue  # Skip to next iteration

                    # Original step processing
                    if hasattr(step, "action_output") and step.action_output:
                        st.write("Action Output:")
                        st.write(step.action_output)
                        st.session_state.analysis_results.append(
                            ("output", step.action_output)
                        )
                    elif os.path.exists(valuation_file):
                        st.write("Evaluation completed successfully!")
                        break

                st.session_state.analysis_complete = True

            else:
                # Display stored results
                for result_type, content in st.session_state.analysis_results:
                    st.write(f"{result_type.title()}:")
                    st.write(content)


if __name__ == "__main__":
    main()
