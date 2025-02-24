import json
import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

import google.generativeai as genai
import streamlit as st

BASE_DIR = "outputs"
FMP_DATA_DIR = os.path.join(BASE_DIR, "fmp_data")
VALUATION_DIR = os.path.join(FMP_DATA_DIR, "valuation")
METRICS_DIR = os.path.join(FMP_DATA_DIR, "metrics")

for directory in [BASE_DIR, FMP_DATA_DIR, VALUATION_DIR, METRICS_DIR]:
    os.makedirs(directory, exist_ok=True)


class Stage(Enum):
    INDUSTRY = auto()
    GOALS = auto()
    BUDGET = auto()
    TIMELINE = auto()
    FINANCIAL_HEALTH = auto()
    MARKET_POSITION = auto()
    RISKS = auto()
    COMPLETION = auto()
    COMPLETE = auto()


@dataclass
class MAStrategyInfo:
    industry: Optional[str] = None
    specific_company: Optional[str] = None
    goals: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    financial_health: Optional[str] = None
    market_position: Optional[str] = None
    risks_concern: Optional[str] = None
    risks_details: Optional[str] = None
    is_complete: bool = False


@dataclass
class Message:
    role: str
    text: str


@dataclass
class MAStrategyBot:
    model: genai.GenerativeModel
    conversation_history: List[Message] = field(default_factory=list)
    current_stage: Stage = Stage.INDUSTRY
    collected_info: MAStrategyInfo = field(default_factory=MAStrategyInfo)
    chat: Optional[genai.ChatSession] = None

    def __post_init__(self):
        self.chat = self.model.start_chat(history=[])
        self.system_prompt = """You are an M&A strategy consultant bot. Your role is to guide the conversation to collect key M&A strategy information. 

Format all responses as the following JSON structure:
{
    "answer_complete": true/false (if you have enough info for this stage),
    "current_stage": "STAGE_NAME",
    "is_strategy_complete": true/false (set to true ONLY when all necessary information has been collected),
    "collected_info": {
        "industry": "user's industry or null",
        "specific_company": "target company or null",
        "goals": "M&A goals or null",
        "budget": "budget info or null",
        "timeline": "timeline info or null",
        "financial_health": "financial health info of target or null",
        "market_position": "market position info of target or null",
        "risks_concern": "risk concerns or null",
        "risks_details": "risk details or null",
        "is_complete": false
    },
    "next_message": "your next message to user"
}

Set is_strategy_complete to true when:
1. You have collected sufficient information about the target industry/company
2. You have clear goals for the M&A
3. You have budget information
4. You understand the timeline
5. You have assessed risks and concerns

When is_strategy_complete is true:
1. Set collected_info.is_complete to true
2. Make next_message indicate completion and readiness for analysis
3. Set current_stage to COMPLETION"""

        first_message = {
            "answer_complete": False,
            "current_stage": "INDUSTRY",
            "is_strategy_complete": False,
            "collected_info": {
                "industry": None,
                "specific_company": None,
                "goals": None,
                "budget": None,
                "timeline": None,
                "financial_health": None,
                "market_position": None,
                "risks_concern": None,
                "risks_details": None,
                "is_complete": False,
            },
            "next_message": "Welcome! To begin our M&A strategy discussion, do you have a specific company in mind for acquisition, or are you targeting a particular market or sector?",
        }

        self.chat.send_message(
            f"{self.system_prompt}\n\nRespond with this exact JSON:\n{json.dumps(first_message, indent=2)}"
        )

    def save_strategy_info(self) -> str:
        output_path = os.path.join(BASE_DIR, "strategy_info.json")
        with open(output_path, "w") as f:
            json.dump(vars(self.collected_info), f, indent=4)
        return output_path

    def _advance_stage(self):
        stage_progression = {
            Stage.INDUSTRY: Stage.GOALS,
            Stage.GOALS: Stage.BUDGET,
            Stage.BUDGET: Stage.TIMELINE,
            Stage.TIMELINE: Stage.FINANCIAL_HEALTH,
            Stage.FINANCIAL_HEALTH: Stage.MARKET_POSITION,
            Stage.MARKET_POSITION: Stage.RISKS,
            Stage.RISKS: Stage.COMPLETION,
            Stage.COMPLETION: Stage.COMPLETE,
        }
        self.current_stage = stage_progression.get(self.current_stage, Stage.COMPLETE)

    def get_response(self, user_message: Optional[str] = None) -> tuple[str, bool]:
        if not user_message:
            return (
                "Welcome! To begin our M&A strategy discussion, do you have a specific company in mind for acquisition, or are you targeting a particular market or sector?",
                False,
            )

        try:
            prompt = f"""Current stage: {self.current_stage.name}
Current state: {json.dumps(vars(self.collected_info), indent=2)}
User message: {user_message}

Remember to respond only with a JSON object in the specified format, including the is_strategy_complete flag."""

            response = self.chat.send_message(prompt)

            try:
                start = response.text.find("{")
                end = response.text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = response.text[start:end]
                    response_data = json.loads(json_str)

                    is_strategy_complete = response_data.get(
                        "is_strategy_complete", False
                    )

                    if "collected_info" in response_data:
                        collected_info = response_data["collected_info"]
                        collected_info["is_complete"] = is_strategy_complete
                        self.collected_info = MAStrategyInfo(**collected_info)

                    if response_data.get("answer_complete"):
                        self._advance_stage()

                    return (
                        response_data.get(
                            "next_message", "Could you provide more details?"
                        ),
                        is_strategy_complete,
                    )

            except json.JSONDecodeError:
                if "Thank you for providing this information" in response.text:
                    self.collected_info.is_complete = True
                    return response.text, True
                return response.text, False

        except Exception as e:
            st.error(f"Error in processing: {str(e)}")
            return "Could you please elaborate on your response?", False

        except Exception as e:
            st.error(f"Error in processing: {str(e)}")
            if (
                self.current_stage == Stage.INDUSTRY
                and "education" in user_message.lower()
            ):
                self.collected_info.industry = "Education"
                self._advance_stage()
                return "I understand you're interested in the education sector. What are your primary goals for this M&A strategy?"
            return "Could you please elaborate on your response?"


def run_analysis(analysis_container) -> None:
    try:
        from agent1 import managed_strategist
        from agent2 import managed_critic, managed_researcher
        from agent3n4 import managed_analyst
        from agent5 import managed_valuator
        from run import MANAGER_PROMPT, manager

        result = manager.run(MANAGER_PROMPT, stream=True)

        for step in result:
            if hasattr(step, "action_output") and step.action_output:
                st.write(step.action_output)

            if os.path.exists("outputs/critic_companies.json"):
                with open("outputs/critic_companies.json", "r") as f:
                    companies = json.load(f)

                valuation_files = [
                    f"{VALUATION_DIR}/{company['symbol']}_valuation.md"
                    for company in companies
                ]

                if all(os.path.exists(file) for file in valuation_files):
                    for file in valuation_files:
                        with open(file, "r") as f:
                            analysis_container.write(f.read())
                    break

    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")


def initialize_gemini():
    genai.configure(os.getenv('GOOGLE_API_KEY'))

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={
            "temperature": 0.1,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
        },
    )

    return model


def main():
    st.set_page_config(
        page_title="M&A Strategy Assessment", page_icon="💼", layout="wide"
    )

    st.title("M&A Strategy Assessment System")
    st.write("Let's discuss your merger and acquisition strategy.")

    if "bot" not in st.session_state:
        model = initialize_gemini()
        st.session_state.bot = MAStrategyBot(model=model)

    if "conversation_ended" not in st.session_state:
        st.session_state.conversation_ended = False

    if "analysis_started" not in st.session_state:
        st.session_state.analysis_started = False

    bot = st.session_state.bot

    for message in bot.conversation_history:
        st.write(f"{'🤖 Bot:' if message.role == 'bot' else '👤 You:'} {message.text}")

    if not st.session_state.conversation_ended:
        if not bot.conversation_history:
            initial_message, _ = bot.get_response()
            bot.conversation_history.append(Message(role="bot", text=initial_message))
            st.rerun()

        user_input = st.text_input("Your response:", key="user_input")

        if st.button("Submit", key="submit_button"):
            if user_input.strip():
                bot.conversation_history.append(Message(role="user", text=user_input))
                bot_response, is_complete = bot.get_response(user_input)
                bot.conversation_history.append(Message(role="bot", text=bot_response))

                if is_complete or bot.current_stage in [
                    Stage.COMPLETION,
                    Stage.COMPLETE,
                ]:
                    st.session_state.conversation_ended = True
                    filename = bot.save_strategy_info()
                    st.success(f"Strategy information has been saved to: {filename}")
                    st.json(vars(bot.collected_info))
                    if st.button("Generate strategy analysis"):
                        st.session_state.analysis_started = True
                        st.rerun()

                st.rerun()

    elif not st.session_state.analysis_started:
        if st.button("Generate strategy analysis"):
            st.session_state.analysis_started = True
            st.rerun()

    else:
        analysis_container = st.container()
        with analysis_container:
            run_analysis(analysis_container)


if __name__ == "__main__":
    main()
