import json
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional

import google.generativeai as genai
import streamlit as st
import watchdog.events
import watchdog.observers
from streamlit_autorefresh import st_autorefresh
from watchdog.events import FileSystemEvent, FileSystemEventHandler

BASE_DIR = "outputs"
FMP_DATA_DIR = os.path.join(BASE_DIR, "fmp_data")


STRATEGY_INFO_PATH = os.path.join(BASE_DIR, "strategy_info.json")
STRATEGY_REPORT_PATH = os.path.join(BASE_DIR, "output.md")
COMPANIES_PATH = os.path.join(BASE_DIR, "companies.json")
VALUATION_REPORT_PATH = os.path.join(BASE_DIR, "valuation.md")


if "PROCESSING_STATUS" not in st.session_state:
    st.session_state["PROCESSING_STATUS"] = {
        "current_agent": None,
        "current_task": None,
        "start_time": None,
        "progress": 0.0,
        "message": "Ready to start analysis",
        "error": None,
        "completed_tasks": set(),
        "total_tasks": 4,
        "is_running": False,
    }

if "FILE_UPDATES" not in st.session_state:
    st.session_state["FILE_UPDATES"] = {
        "strategy_info": None,
        "strategy_report": None,
        "companies": None,
        "valuation_report": None,
        "fmp_data": {},
    }

if "STARTUP" not in st.session_state:
    st.session_state["STARTUP"] = True

if "OBSERVER" not in st.session_state:
    st.session_state["OBSERVER"] = None

if "ANALYSIS_THREAD_STARTED" not in st.session_state:
    st.session_state["ANALYSIS_THREAD_STARTED"] = False

if "conversation_ended" not in st.session_state:
    st.session_state["conversation_ended"] = False

if "analysis_started" not in st.session_state:
    st.session_state["analysis_started"] = False

if "LAST_UPDATE_CHECK" not in st.session_state:
    st.session_state["LAST_UPDATE_CHECK"] = datetime.now()


class ImprovedFileChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        self._process_change(event)

    def on_modified(self, event):
        self._process_change(event)

    def _process_change(self, event: FileSystemEvent):
        if event.is_directory:
            return

        file_path = str(Path(event.src_path))

        if "FILE_UPDATES" not in st.session_state:
            st.session_state["FILE_UPDATES"] = {
                "strategy_info": None,
                "strategy_report": None,
                "companies": None,
                "valuation_report": None,
                "fmp_data": {},
            }

        if "PROCESSING_STATUS" not in st.session_state:
            st.session_state["PROCESSING_STATUS"] = {
                "current_agent": None,
                "current_task": None,
                "start_time": None,
                "progress": 0.0,
                "message": "Ready to start analysis",
                "error": None,
                "completed_tasks": set(),
                "total_tasks": 4,
                "is_running": False,
            }

        if file_path.endswith("strategy_info.json"):
            st.session_state["FILE_UPDATES"]["strategy_info"] = datetime.now()
            st.session_state["PROCESSING_STATUS"]["progress"] = 0.25
            st.session_state["PROCESSING_STATUS"]["message"] = "Starting analysis"
            st.session_state["PROCESSING_STATUS"][
                "current_task"
            ] = "Generating strategy report"
            st.session_state["PROCESSING_STATUS"]["completed_tasks"].add("input")

        elif file_path.endswith("output.md"):
            st.session_state["FILE_UPDATES"]["strategy_report"] = datetime.now()
            st.session_state["PROCESSING_STATUS"]["progress"] = 0.5
            st.session_state["PROCESSING_STATUS"][
                "message"
            ] = "Strategy report generated"
            st.session_state["PROCESSING_STATUS"][
                "current_task"
            ] = "Researching companies"
            st.session_state["PROCESSING_STATUS"]["completed_tasks"].add("strategy")

        elif file_path.endswith("companies.json"):
            st.session_state["FILE_UPDATES"]["companies"] = datetime.now()
            st.session_state["PROCESSING_STATUS"]["progress"] = 0.75
            st.session_state["PROCESSING_STATUS"]["message"] = "Companies identified"
            st.session_state["PROCESSING_STATUS"][
                "current_task"
            ] = "Analyzing financials"
            st.session_state["PROCESSING_STATUS"]["completed_tasks"].add("companies")

        elif file_path.endswith("valuation.md"):
            st.session_state["FILE_UPDATES"]["valuation_report"] = datetime.now()
            st.session_state["PROCESSING_STATUS"]["progress"] = 1.0
            st.session_state["PROCESSING_STATUS"]["message"] = "Financials analyzed"
            st.session_state["PROCESSING_STATUS"][
                "current_task"
            ] = "Completing valuation"
            st.session_state["PROCESSING_STATUS"]["completed_tasks"].add("financials")

            if len(st.session_state["PROCESSING_STATUS"]["completed_tasks"]) == 4:
                st.session_state["PROCESSING_STATUS"]["progress"] = 1.0
                st.session_state["PROCESSING_STATUS"]["message"] = "Analysis complete"
                st.session_state["PROCESSING_STATUS"]["current_task"] = "Complete"
                st.session_state["PROCESSING_STATUS"]["is_running"] = False

        elif file_path.startswith(FMP_DATA_DIR) and (
            file_path.endswith("_metrics.md") or file_path.endswith("_valuation.md")
        ):
            filename = os.path.basename(file_path)
            st.session_state["FILE_UPDATES"]["fmp_data"][filename] = datetime.now()
            company_symbol = filename.split("_")[0]
            st.session_state["PROCESSING_STATUS"][
                "message"
            ] = f"Processing financial data for {company_symbol}"

        st.rerun()


def setup_file_watcher():
    """Setup a watchdog observer to monitor file changes"""
    if "OBSERVER" not in st.session_state:
        st.session_state["OBSERVER"] = None

    if (
        st.session_state["OBSERVER"] is None
        or not st.session_state["OBSERVER"].is_alive()
    ):
        event_handler = ImprovedFileChangeHandler()
        observer = watchdog.observers.Observer()
        observer.schedule(event_handler, path=BASE_DIR, recursive=True)
        observer.start()
        st.session_state["OBSERVER"] = observer
        print(f"File watcher started for {BASE_DIR}")


def cleanup_outputs_directory():
    """Clean up the outputs directory and reset session state, but preserve existing reports if analysis was completed"""
    preserve_files = (
        st.session_state.get("PROCESSING_STATUS", {}).get("progress", 0) >= 1.0
    )

    if os.path.exists(BASE_DIR):
        important_files = [STRATEGY_REPORT_PATH, COMPANIES_PATH, VALUATION_REPORT_PATH]
        backup_contents = {}

        if preserve_files:
            for file_path in important_files:
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    try:
                        with open(file_path, "r") as f:
                            backup_contents[file_path] = f.read()
                    except Exception as e:
                        st.error(f"Failed to backup {file_path}. Reason: {e}")

        for filename in os.listdir(BASE_DIR):
            file_path = os.path.join(BASE_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    if preserve_files and file_path in important_files:
                        continue
                    os.unlink(file_path)
                elif os.path.isdir(file_path) and file_path != FMP_DATA_DIR:
                    shutil.rmtree(file_path)
            except Exception as e:
                st.error(f"Failed to delete {file_path}. Reason: {e}")

    for directory in [BASE_DIR, FMP_DATA_DIR]:
        os.makedirs(directory, exist_ok=True)

    if not preserve_files:
        st.session_state["PROCESSING_STATUS"] = {
            "current_agent": None,
            "current_task": None,
            "start_time": None,
            "progress": 0.0,
            "message": "Ready to start analysis",
            "error": None,
            "completed_tasks": set(),
            "total_tasks": 4,
            "is_running": False,
        }

        st.session_state["FILE_UPDATES"] = {
            "strategy_info": None,
            "strategy_report": None,
            "companies": None,
            "valuation_report": None,
            "fmp_data": {},
        }

    if preserve_files:
        for file_path, content in backup_contents.items():
            try:
                with open(file_path, "w") as f:
                    f.write(content)
            except Exception as e:
                st.error(f"Failed to restore {file_path}. Reason: {e}")

    st.session_state["ANALYSIS_THREAD_STARTED"] = False
    st.session_state["LAST_UPDATE_CHECK"] = datetime.now()


def check_file_updates():
    """Check for file updates and update session state accordingly"""

    if "PROCESSING_STATUS" not in st.session_state:
        st.session_state["PROCESSING_STATUS"] = {
            "current_agent": None,
            "current_task": None,
            "start_time": None,
            "progress": 0.0,
            "message": "Ready to start analysis",
            "error": None,
            "completed_tasks": set(),
            "total_tasks": 4,
            "is_running": False,
        }

    if "FILE_UPDATES" not in st.session_state:
        st.session_state["FILE_UPDATES"] = {
            "strategy_info": None,
            "strategy_report": None,
            "companies": None,
            "valuation_report": None,
            "fmp_data": {},
        }

    if "LAST_UPDATE_CHECK" not in st.session_state:
        st.session_state["LAST_UPDATE_CHECK"] = datetime.now()

    if "ANALYSIS_THREAD_STARTED" not in st.session_state:
        st.session_state["ANALYSIS_THREAD_STARTED"] = False

    st.session_state["LAST_UPDATE_CHECK"] = datetime.now()

    files_to_check = {
        "strategy_info": (
            STRATEGY_INFO_PATH,
            0.0,
            "Starting analysis",
            "Generating strategy report",
            "input",
        ),
        "strategy_report": (
            STRATEGY_REPORT_PATH,
            0.25,
            "Strategy report generated",
            "Researching companies",
            "strategy",
        ),
        "companies": (
            COMPANIES_PATH,
            0.5,
            "Companies identified",
            "Analyzing financials",
            "companies",
        ),
        "valuation_report": (
            VALUATION_REPORT_PATH,
            0.75,
            "Financials analyzed",
            "Completing valuation",
            "financials",
        ),
    }

    files_found = 0

    highest_completed_stage = -1
    stage_order = ["input", "strategy", "companies", "financials", "valuation"]

    fmp_files_found = False
    if os.path.exists(FMP_DATA_DIR):
        fmp_files = [
            f
            for f in os.listdir(FMP_DATA_DIR)
            if f.endswith("_valuation.md") or f.endswith("_metrics.md")
        ]
        for fmp_file in fmp_files:
            file_path = os.path.join(FMP_DATA_DIR, fmp_file)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                st.session_state["FILE_UPDATES"]["fmp_data"][fmp_file] = datetime.now()
                fmp_files_found = True

    for file_key, (
        file_path,
        progress,
        message,
        task,
        task_id,
    ) in files_to_check.items():
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            files_found += 1
            st.session_state["FILE_UPDATES"][file_key] = datetime.now()

            if task_id in stage_order:
                stage_index = stage_order.index(task_id)
                highest_completed_stage = max(highest_completed_stage, stage_index)

    current_stage_index = highest_completed_stage
    if current_stage_index >= 0 and current_stage_index < len(stage_order):
        current_stage = stage_order[current_stage_index]

        for file_key, (
            file_path,
            progress,
            message,
            task,
            task_id,
        ) in files_to_check.items():
            if task_id == current_stage:
                st.session_state["PROCESSING_STATUS"]["progress"] = progress
                st.session_state["PROCESSING_STATUS"]["message"] = message
                st.session_state["PROCESSING_STATUS"]["current_task"] = task
                st.session_state["PROCESSING_STATUS"]["completed_tasks"].add(task_id)
                break

    if files_found == 4:
        valuation_updated = st.session_state["FILE_UPDATES"].get("valuation_report")
        if (
            valuation_updated
            and (datetime.now() - valuation_updated).total_seconds() > 5
        ):
            st.session_state["PROCESSING_STATUS"].update(
                {
                    "is_running": False,
                    "message": "Analysis complete",
                    "progress": 1.0,
                    "current_task": "Complete",
                }
            )
            st.session_state["ANALYSIS_THREAD_STARTED"] = True
            st.rerun()

    return files_found


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
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MAStrategyBot:
    model: genai.GenerativeModel
    conversation_history: List[Message] = field(default_factory=list)
    current_stage: Stage = Stage.INDUSTRY
    collected_info: MAStrategyInfo = field(default_factory=MAStrategyInfo)
    chat: Optional[genai.ChatSession] = None
    max_retries: int = 3

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

IMPORTANT: If you're missing crucial information, ask follow-up questions to obtain it.
Always provide a meaningful response even with incomplete data.

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
        """Save the collected strategy information to a JSON file"""
        os.makedirs(BASE_DIR, exist_ok=True)
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

        for retry in range(self.max_retries):
            try:
                prompt = f"""Current stage: {self.current_stage.name}
Current state: {json.dumps(vars(self.collected_info), indent=2)}
User message: {user_message}

Remember to respond only with a JSON object in the specified format, including the is_strategy_complete flag.
If you have trouble parsing the user's message, try to extract relevant information anyway and request clarification in your next_message.
"""

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

                            for key, value in collected_info.items():
                                if value is not None:
                                    setattr(self.collected_info, key, value)

                            self.collected_info.is_complete = is_strategy_complete

                        if response_data.get("answer_complete"):
                            self._advance_stage()

                        return (
                            response_data.get(
                                "next_message", "Could you provide more details?"
                            ),
                            is_strategy_complete,
                        )

                except json.JSONDecodeError:
                    if retry < self.max_retries - 1:
                        continue

                    if "Thank you for providing this information" in response.text:
                        self.collected_info.is_complete = True
                        return response.text, True

                    user_message_lower = user_message.lower()
                    if (
                        self.current_stage == Stage.INDUSTRY
                        and not self.collected_info.industry
                    ):
                        for industry in [
                            "technology",
                            "healthcare",
                            "finance",
                            "education",
                            "retail",
                            "manufacturing",
                        ]:
                            if industry in user_message_lower:
                                self.collected_info.industry = industry.capitalize()
                                self._advance_stage()
                                return (
                                    f"I understand you're interested in the {industry} sector. What are your primary goals for this M&A strategy?",
                                    False,
                                )

                    return (
                        "I'm having trouble processing that. Could you please provide key information clearly? For example, what industry are you targeting and what are your main goals?",
                        False,
                    )

            except Exception as e:
                if retry < self.max_retries - 1:
                    time.sleep(1)
                    continue

                print(f"Error in processing: {str(e)}")

                if (
                    self.current_stage == Stage.INDUSTRY
                    and "education" in user_message.lower()
                ):
                    self.collected_info.industry = "Education"
                    self._advance_stage()
                    return (
                        "I understand you're interested in the education sector. What are your primary goals for this M&A strategy?",
                        False,
                    )

                return (
                    "I encountered an issue processing your request. Could you please clarify your requirements in simple terms?",
                    False,
                )


def run_analysis_thread(strategy_info):
    """Run the analysis process in a separate thread"""
    try:
        if "PROCESSING_STATUS" not in st.session_state:
            st.session_state["PROCESSING_STATUS"] = {
                "current_agent": None,
                "current_task": None,
                "start_time": None,
                "progress": 0.0,
                "message": "Ready to start analysis",
                "error": None,
                "completed_tasks": set(),
                "total_tasks": 4,
                "is_running": False,
            }

        cleanup_outputs_directory()

        output_path = os.path.join(BASE_DIR, "strategy_info.json")
        with open(output_path, "w") as f:
            json.dump(strategy_info, f, indent=4)

        from run import MANAGER_PROMPT, manager

        st.session_state["PROCESSING_STATUS"]["start_time"] = datetime.now()
        st.session_state["PROCESSING_STATUS"]["is_running"] = True
        st.session_state["PROCESSING_STATUS"]["current_agent"] = "strategist"
        st.session_state["PROCESSING_STATUS"][
            "current_task"
        ] = "Generating strategy report"
        st.session_state["PROCESSING_STATUS"]["message"] = "Starting analysis..."
        st.session_state["PROCESSING_STATUS"]["progress"] = 0.0

        try:
            result = manager.run(MANAGER_PROMPT, stream=True)

            for step in result:
                if hasattr(step, "action_output") and step.action_output:
                    print(f"{step.action_output}\n")

                    if "MNA_PROCESS_COMPLETE" in str(step.action_output):
                        print("MNA process completion signal detected!")
                        time.sleep(2)
                        st.session_state["PROCESSING_STATUS"].update(
                            {
                                "is_running": False,
                                "message": "Analysis complete",
                                "progress": 1.0,
                                "current_task": "Complete",
                            }
                        )
                        check_file_updates()
                        st.rerun()

                if hasattr(step, "agent_name") and step.agent_name:
                    st.session_state["PROCESSING_STATUS"][
                        "current_agent"
                    ] = step.agent_name

                    agent_tasks = {
                        "strategist": ("Generating strategy report", 0.0),
                        "researcher": ("Researching companies", 0.25),
                        "analyst": ("Analyzing financials", 0.5),
                        "valuator": ("Performing valuation", 0.75),
                    }

                    if step.agent_name in agent_tasks:
                        task, progress = agent_tasks[step.agent_name]

                        completed_files = sum(
                            1
                            for f in [
                                STRATEGY_INFO_PATH,
                                STRATEGY_REPORT_PATH,
                                COMPANIES_PATH,
                                VALUATION_REPORT_PATH,
                            ]
                            if os.path.exists(f) and os.path.getsize(f) > 0
                        )

                        if completed_files <= len(agent_tasks):
                            st.session_state["PROCESSING_STATUS"].update(
                                {
                                    "progress": progress,
                                    "current_task": task,
                                    "message": f"Working on {task.lower()}",
                                }
                            )
                            st.rerun()

            check_file_updates()

        except Exception as e:
            error_msg = f"Analysis error: {str(e)}"
            st.session_state["PROCESSING_STATUS"]["error"] = error_msg
            st.session_state["PROCESSING_STATUS"]["message"] = "Error during analysis"
            print(f"Error: {error_msg}")

    except Exception as e:
        print(f"Failed to run analysis: {str(e)}")
    finally:
        if "PROCESSING_STATUS" in st.session_state:
            st.session_state["PROCESSING_STATUS"]["is_running"] = False


def read_file_content(file_path):
    """Read and return the content of a file"""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return None

    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None


def get_fmp_data_files():
    """Get all markdown files from the FMP data directory"""
    result = []
    if os.path.exists(FMP_DATA_DIR):
        for file in os.listdir(FMP_DATA_DIR):
            if file.endswith("_valuation.md") or file.endswith("_metrics.md"):
                result.append(os.path.join(FMP_DATA_DIR, file))
    return sorted(result)


def initialize_gemini():
    """Initialize the Gemini model"""
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 40,
            "max_output_tokens": 2048,
        },
    )

    return model


def display_strategy_tab():
    """Display the Strategy tab content"""
    strategy_content = read_file_content(STRATEGY_REPORT_PATH)
    if strategy_content:
        st.info(strategy_content)
    else:
        st.info(
            "Strategy report not available yet. Please wait for the analysis to complete."
        )


def display_company_card(company):
    """Display a company information card"""
    markdown_content = f"""
## {company['symbol']} - {company['name']}

**Country:** {company['country']}

**Website:** {company['website']}

**Summary:**
{company['summary']}

    """
    st.info(markdown_content)


def display_companies_tab():
    """Display the Companies tab content"""
    companies_content = read_file_content(COMPANIES_PATH)
    if companies_content:
        try:
            companies_data = json.loads(companies_content)
            for company in companies_data:
                display_company_card(company)

        except json.JSONDecodeError:
            st.info(companies_content)
    else:
        st.info(
            "Companies data not available yet. Please wait for the analysis to complete."
        )


def display_financials_tab():
    """Display the Financials tab content"""
    fmp_files = get_fmp_data_files()
    if fmp_files:
        for file_path in fmp_files:
            filename = os.path.basename(file_path)
            company_symbol = filename.split("_")[0]
            content = read_file_content(file_path)

            if content:
                with st.expander(f"{company_symbol} - {filename}", expanded=True):
                    st.info(content)
    else:
        st.info(
            "Financial data not available yet. Please wait for the analysis to complete."
        )


def display_valuation_tab():
    """Display the Valuation tab content"""
    valuation_content = read_file_content(VALUATION_REPORT_PATH)
    if valuation_content:
        st.info(valuation_content)
    else:
        st.info(
            "Valuation report not available yet. Please wait for the analysis to complete."
        )


def main():
    st.set_page_config(
        page_title="M&A Strategy Automation",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    if "INITIAL_CLEANUP_DONE" not in st.session_state:
        st.session_state["INITIAL_CLEANUP_DONE"] = False

    if st.session_state.get("analysis_started", False):
        st_autorefresh(interval=15000, limit=100, key="auto-refresh")

    if "PROCESSING_STATUS" not in st.session_state:
        st.session_state["PROCESSING_STATUS"] = {
            "current_agent": None,
            "current_task": None,
            "start_time": None,
            "progress": 0.0,
            "message": "Ready to start analysis",
            "error": None,
            "completed_tasks": set(),
            "total_tasks": 4,
            "is_running": False,
        }

    if "FILE_UPDATES" not in st.session_state:
        st.session_state["FILE_UPDATES"] = {
            "strategy_info": None,
            "strategy_report": None,
            "companies": None,
            "valuation_report": None,
            "fmp_data": {},
        }

    if "STARTUP" not in st.session_state:
        st.session_state["STARTUP"] = True

    if "OBSERVER" not in st.session_state:
        st.session_state["OBSERVER"] = None

    if "ANALYSIS_THREAD_STARTED" not in st.session_state:
        st.session_state["ANALYSIS_THREAD_STARTED"] = False

    if "conversation_ended" not in st.session_state:
        st.session_state["conversation_ended"] = False

    if "analysis_started" not in st.session_state:
        st.session_state["analysis_started"] = False

    if "LAST_UPDATE_CHECK" not in st.session_state:
        st.session_state["LAST_UPDATE_CHECK"] = datetime.now()

    st.markdown(
        """
        <style>
        .css-18e3th9 .block-container {padding-top: 0rem;}
        .stProgress .st-bo {background-color: #808080;}
        .main-header {text-align: center; margin-bottom: 20px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state["STARTUP"] and not st.session_state["INITIAL_CLEANUP_DONE"]:
        setup_file_watcher()
        st.session_state["STARTUP"] = False
        st.session_state["INITIAL_CLEANUP_DONE"] = True

    col1, col2, col3 = st.columns([0.25, 0.2, 0.25])
    with col2:
        st.image("resources/mna.png", use_container_width=True)

    if "bot" not in st.session_state:
        model = initialize_gemini()
        st.session_state["bot"] = MAStrategyBot(model=model)

    bot = st.session_state["bot"]

    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    progress = st.session_state["PROCESSING_STATUS"]["progress"]
    task = st.session_state["PROCESSING_STATUS"]["current_task"] or "Waiting to start"
    message = st.session_state["PROCESSING_STATUS"]["message"]

    progress_bar = progress_placeholder.progress(progress)
    status_placeholder.warning(f"Status: {message} | Current Task: {task}")

    if progress > 0:
        progress_bar.progress(progress, text=f"Progress: {int(progress*100)}%")

    if st.session_state["PROCESSING_STATUS"]["error"]:
        error_msg = st.session_state["PROCESSING_STATUS"]["error"]
        st.error(f"Error: {error_msg}")

    if not st.session_state["conversation_ended"]:
        chat_container = st.container()
        with chat_container:
            for message in bot.conversation_history:
                if message.role == "bot":
                    st.chat_message("assistant").write(message.text)
                else:
                    st.chat_message("user").write(message.text)

            if not bot.conversation_history:
                initial_message, _ = bot.get_response()
                bot.conversation_history.append(
                    Message(role="bot", text=initial_message)
                )
                st.rerun()

            user_input = st.chat_input("Type your message here...")
            if user_input:
                bot.conversation_history.append(Message(role="user", text=user_input))
                with st.spinner("Thinking..."):
                    bot_response, is_complete = bot.get_response(user_input)
                bot.conversation_history.append(Message(role="bot", text=bot_response))

                if is_complete or bot.current_stage in [
                    Stage.COMPLETION,
                    Stage.COMPLETE,
                ]:
                    st.session_state["conversation_ended"] = True
                st.rerun()

    elif not st.session_state["analysis_started"]:
        if st.button("▶️ Generate strategy", key="generate_button", type="primary"):
            st.session_state["analysis_started"] = True
            strategy_info = vars(bot.collected_info)
            analysis_thread = threading.Thread(
                target=run_analysis_thread, args=(strategy_info,)
            )
            analysis_thread.daemon = True
            analysis_thread.start()
            st.rerun()
    else:
        if not st.session_state["ANALYSIS_THREAD_STARTED"]:
            strategy_info = vars(bot.collected_info)
            analysis_thread = threading.Thread(
                target=run_analysis_thread, args=(strategy_info,)
            )
            analysis_thread.daemon = True
            analysis_thread.start()
            st.session_state["ANALYSIS_THREAD_STARTED"] = True

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Strategy", "Companies", "Financials", "Recommendations"]
        )

        with tab1:
            display_strategy_tab()

        with tab2:
            display_companies_tab()

        with tab3:
            display_financials_tab()

        with tab4:
            display_valuation_tab()

        check_file_updates()


if __name__ == "__main__":
    main()
