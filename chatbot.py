import json
import os
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

# Initialize the LiteLLM model
model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)

# Initialize the multiagent
agent = manager


class MAStrategyBot:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.conversation_history = []
        self.thread_id = None
        self.assistant_id = None
        self.current_stage = "target"

        # Initialize the state dictionary to store collected information
        self.collected_info = {
            "target_market": None,
            "specific_company": None,
            "goals": None,
            "budget": None,
            "timeline": None,
        }

        # Define the system instructions
        self.system_instructions = """You are an M&A strategy consultant chatbot. Your role is to gather specific information in a sequential order and maintain a state of collected information.

1. First, determine if they have a specific target company or target market
2. Then, understand their goals for the M&A
3. Next, get their budget information
4. Finally, get their timeline

Current question stages:
- target: Ask if they have a specific company in mind or if they're targeting a market/sector
- goals: Ask about their primary goals for this M&A
- budget: Ask about their budget range
- timeline: Ask about their expected timeline

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
    "current_stage": "target/goals/budget/timeline",
    "collected_info": {
        "target_market": "extracted market info or null",
        "specific_company": "extracted company info or null",
        "goals": "extracted goals or null",
        "budget": "extracted budget or null",
        "timeline": "extracted timeline or null"
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
                    if self.current_stage == "target":
                        self.current_stage = "goals"
                    elif self.current_stage == "goals":
                        self.current_stage = "budget"
                    elif self.current_stage == "budget":
                        self.current_stage = "timeline"
                    elif self.current_stage == "timeline":
                        self.current_stage = "complete"

                return response_data["next_message"]
            except json.JSONDecodeError:
                return "I apologize, but I encountered an error. Could you please repeat your last message?"
        else:
            # Initial message
            return "Hello! To begin our M&A strategy discussion, do you have a specific company in mind for acquisition, or are you targeting a particular market or sector?"


def main():
    st.title("M&A Strategy Assessment System")
    st.write("Let's discuss your merger and acquisition strategy.")

    # Initialize session states
    if "bot" not in st.session_state:
        st.session_state.bot = MAStrategyBot()
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

                # Clear the "Running analysis..." message
                analysis_container.empty()

                # Store results in session state
                st.session_state.analysis_results = []
                for step in result:
                    if step.action_output:
                        st.write("Action Output:")
                        st.write(step.action_output)
                        st.session_state.analysis_results.append(
                            ("output", step.action_output)
                        )
                    if step.observations:
                        st.write("Analysis Observations:")
                        st.write(step.observations)
                        st.session_state.analysis_results.append(
                            ("observation", step.observations)
                        )

                st.session_state.analysis_complete = True
            else:
                # Display stored results
                for result_type, content in st.session_state.analysis_results:
                    st.write(f"{result_type.title()}:")
                    st.write(content)


if __name__ == "__main__":
    main()
