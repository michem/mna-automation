import json
import os
import shutil
import sys
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
from watchdog.events import FileSystemEvent, FileSystemEventHandler


class StreamlitOutputRedirector:
    def __init__(self, placeholder):
        self.buffer = ""
        self.placeholder = placeholder
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

    def write(self, text):
        self.buffer += text
        self.placeholder.code(self.buffer)
        self._original_stdout.write(text)

    def flush(self):
        pass

    def reset(self):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr


BASE_DIR = "outputs"
FMP_DATA_DIR = os.path.join(BASE_DIR, "fmp_data")


if "PROCESSING_STATUS" not in st.session_state:
    st.session_state.PROCESSING_STATUS = {
        "current_agent": None,
        "current_task": None,
        "start_time": None,
        "progress": 0.0,
        "message": "Ready to start analysis",
        "error": None,
        "completed_tasks": set(),
        "total_tasks": 5,
        "is_running": False,
        "cancelling": False,
    }

if "FILE_UPDATES" not in st.session_state:
    st.session_state.FILE_UPDATES = {
        "strategy_info": None,
        "strategy_report": None,
        "companies": None,
        "valuation_report": None,
    }

if "EXPANDER_STATES" not in st.session_state:
    st.session_state.EXPANDER_STATES = {
        "strategy_info": False,
        "strategy_report": False,
        "companies": False,
        "valuation_report": False,
    }

if "STARTUP" not in st.session_state:
    st.session_state.STARTUP = True

if "OBSERVER" not in st.session_state:
    st.session_state.OBSERVER = None

if "ANALYSIS_THREAD_STARTED" not in st.session_state:
    st.session_state.ANALYSIS_THREAD_STARTED = False


def check_file_updates():
    if "PROCESSING_STATUS" not in st.session_state:
        st.session_state.PROCESSING_STATUS = {
            "current_agent": None,
            "current_task": None,
            "start_time": None,
            "progress": 0.0,
            "message": "Ready to start analysis",
            "error": None,
            "completed_tasks": set(),
            "total_tasks": 5,
            "is_running": False,
            "cancelling": False,
        }

    if "FILE_UPDATES" not in st.session_state:
        st.session_state.FILE_UPDATES = {
            "strategy_info": None,
            "strategy_report": None,
            "companies": None,
            "valuation_report": None,
        }

    if "EXPANDER_STATES" not in st.session_state:
        st.session_state.EXPANDER_STATES = {
            "strategy_info": False,
            "strategy_report": False,
            "companies": False,
            "valuation_report": False,
        }

    files_to_check = {
        "strategy_info": (
            "outputs/strategy_info.json",
            0.25,
            "Strategy information collected",
            "Researching companies",
            "strategy",
        ),
        "strategy_report": (
            "outputs/output.md",
            0.5,
            "Strategy report generated",
            "Analyzing financials",
            "report",
        ),
        "companies": (
            "outputs/companies.json",
            0.75,
            "Companies identified",
            "Performing valuation",
            "companies",
        ),
        "valuation_report": (
            "outputs/valuation.md",
            1.0,
            "Valuation complete",
            "Analysis complete",
            "valuation",
        ),
    }

    files_found = 0
    latest_progress = 0.0

    fmp_files_found = False
    if os.path.exists("outputs/fmp_data"):
        fmp_files = os.listdir("outputs/fmp_data")
        if any(
            f.endswith("_valuation.md") or f.endswith("_metrics.md") for f in fmp_files
        ):
            fmp_files_found = True
            print(f"Found company files in outputs/fmp_data: {fmp_files}")

    for file_key, (
        file_path,
        progress,
        message,
        task,
        task_id,
    ) in files_to_check.items():
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            files_found += 1
            latest_progress = max(latest_progress, progress)
            st.session_state.FILE_UPDATES[file_key] = datetime.now()
            st.session_state.EXPANDER_STATES[file_key] = True

            if progress > st.session_state.PROCESSING_STATUS["progress"]:
                st.session_state.PROCESSING_STATUS["progress"] = progress
                st.session_state.PROCESSING_STATUS["message"] = message
                st.session_state.PROCESSING_STATUS["current_task"] = task
                st.session_state.PROCESSING_STATUS["completed_tasks"].add(task_id)

    if (
        files_found == 3
        and fmp_files_found
        and "valuation_report" not in st.session_state.FILE_UPDATES
    ):
        print("Found 3/4 files plus FMP data - assuming process nearly complete")

    if files_found == 4 and st.session_state.PROCESSING_STATUS["is_running"]:
        st.session_state.PROCESSING_STATUS["is_running"] = False
        st.session_state.PROCESSING_STATUS["message"] = "Analysis complete"
        st.session_state.PROCESSING_STATUS["progress"] = 1.0
        st.session_state.ANALYSIS_THREAD_STARTED = True

    if (
        not st.session_state.PROCESSING_STATUS["is_running"]
        and files_found < 4
        and fmp_files_found
    ):
        print("Process completed but missing some main files - checking FMP data")

    return files_found


class FileChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        self._process_change(event)

    def on_modified(self, event):
        self._process_change(event)

    def _process_change(self, event: FileSystemEvent):
        if event.is_directory:
            return

        if "FILE_UPDATES" not in st.session_state:
            st.session_state.FILE_UPDATES = {
                "strategy_info": None,
                "strategy_report": None,
                "companies": None,
                "valuation_report": None,
            }

        if "PROCESSING_STATUS" not in st.session_state:
            st.session_state.PROCESSING_STATUS = {
                "current_agent": None,
                "current_task": None,
                "start_time": None,
                "progress": 0.0,
                "message": "Ready to start analysis",
                "error": None,
                "completed_tasks": set(),
                "total_tasks": 5,
                "is_running": False,
                "cancelling": False,
            }

        if "EXPANDER_STATES" not in st.session_state:
            st.session_state.EXPANDER_STATES = {
                "strategy_info": False,
                "strategy_report": False,
                "companies": False,
                "valuation_report": False,
            }

        path = Path(event.src_path)
        file_path = str(path)

        if file_path.endswith("strategy_info.json"):
            st.session_state.FILE_UPDATES["strategy_info"] = datetime.now()
            st.session_state.EXPANDER_STATES["strategy_info"] = True
            st.session_state.PROCESSING_STATUS["progress"] = 0.25
            st.session_state.PROCESSING_STATUS["message"] = (
                "Strategy information collected"
            )
            st.session_state.PROCESSING_STATUS["current_task"] = "Researching companies"
            st.session_state.PROCESSING_STATUS["completed_tasks"].add("strategy")
        elif file_path.endswith("output.md"):
            st.session_state.FILE_UPDATES["strategy_report"] = datetime.now()
            st.session_state.EXPANDER_STATES["strategy_report"] = True
            st.session_state.PROCESSING_STATUS["progress"] = 0.5
            st.session_state.PROCESSING_STATUS["message"] = "Strategy report generated"
            st.session_state.PROCESSING_STATUS["current_task"] = "Analyzing financials"
            st.session_state.PROCESSING_STATUS["completed_tasks"].add("report")
        elif file_path.endswith("companies.json"):
            st.session_state.FILE_UPDATES["companies"] = datetime.now()
            st.session_state.EXPANDER_STATES["companies"] = True
            st.session_state.PROCESSING_STATUS["progress"] = 0.75
            st.session_state.PROCESSING_STATUS["message"] = "Companies identified"
            st.session_state.PROCESSING_STATUS["current_task"] = "Performing valuation"
            st.session_state.PROCESSING_STATUS["completed_tasks"].add("companies")
        elif file_path.endswith("valuation.md"):
            st.session_state.FILE_UPDATES["valuation_report"] = datetime.now()
            st.session_state.EXPANDER_STATES["valuation_report"] = True
            st.session_state.PROCESSING_STATUS["progress"] = 1.0
            st.session_state.PROCESSING_STATUS["message"] = "Valuation complete"
            st.session_state.PROCESSING_STATUS["current_task"] = "Analysis complete"
            st.session_state.PROCESSING_STATUS["completed_tasks"].add("valuation")
            st.session_state.PROCESSING_STATUS["is_running"] = False

        if "_metrics.md" in file_path or "_valuation.md" in file_path:
            company_symbol = os.path.basename(file_path).split("_")[0]
            st.session_state.PROCESSING_STATUS["message"] = (
                f"Processing financial data for {company_symbol}"
            )

        st.rerun()


def setup_file_watcher():
    if st.session_state.OBSERVER is None or not st.session_state.OBSERVER.is_alive():
        event_handler = FileChangeHandler()
        observer = watchdog.observers.Observer()
        observer.schedule(event_handler, path=BASE_DIR, recursive=True)
        observer.start()
        st.session_state.OBSERVER = observer
        print(f"File watcher started for {BASE_DIR}")


def cleanup_outputs_directory():
    """Clean up the outputs directory and reset session state"""
    if os.path.exists(BASE_DIR):
        for filename in os.listdir(BASE_DIR):
            file_path = os.path.join(BASE_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                st.error(f"Failed to delete {file_path}. Reason: {e}")

    for directory in [BASE_DIR, FMP_DATA_DIR]:
        os.makedirs(directory, exist_ok=True)

    st.session_state.PROCESSING_STATUS = {
        "current_agent": None,
        "current_task": None,
        "start_time": None,
        "progress": 0.0,
        "message": "Outputs directory has been cleaned up",
        "error": None,
        "completed_tasks": set(),
        "total_tasks": 5,
        "is_running": False,
        "cancelling": False,
    }

    st.session_state.FILE_UPDATES = {
        "strategy_info": None,
        "strategy_report": None,
        "companies": None,
        "valuation_report": None,
    }

    st.session_state.EXPANDER_STATES = {
        "strategy_info": False,
        "strategy_report": False,
        "companies": False,
        "valuation_report": False,
    }

    st.session_state.ANALYSIS_THREAD_STARTED = False

    st.success("Outputs directory has been cleaned up.")


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

                st.error(f"Error in processing: {str(e)}")

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


def run_analysis_thread(analysis_container):
    try:
        if "PROCESSING_STATUS" not in st.session_state:
            st.session_state.PROCESSING_STATUS = {
                "current_agent": None,
                "current_task": None,
                "start_time": None,
                "progress": 0.0,
                "message": "Ready to start analysis",
                "error": None,
                "completed_tasks": set(),
                "total_tasks": 5,
                "is_running": False,
                "cancelling": False,
            }

        if "ANALYSIS_THREAD_STARTED" not in st.session_state:
            st.session_state.ANALYSIS_THREAD_STARTED = False

        if "FILE_UPDATES" not in st.session_state:
            st.session_state.FILE_UPDATES = {
                "strategy_info": None,
                "strategy_report": None,
                "companies": None,
                "valuation_report": None,
            }

        if "EXPANDER_STATES" not in st.session_state:
            st.session_state.EXPANDER_STATES = {
                "strategy_info": False,
                "strategy_report": False,
                "companies": False,
                "valuation_report": False,
            }

        st.session_state.ANALYSIS_THREAD_STARTED = True

        from run import MANAGER_PROMPT, manager

        st.session_state.PROCESSING_STATUS["start_time"] = datetime.now()
        st.session_state.PROCESSING_STATUS["is_running"] = True
        st.session_state.PROCESSING_STATUS["current_agent"] = "strategist"
        st.session_state.PROCESSING_STATUS["current_task"] = (
            "Generating strategy report"
        )
        st.session_state.PROCESSING_STATUS["message"] = "Starting analysis..."

        try:
            result = manager.run(MANAGER_PROMPT, stream=True)

            for step in result:
                if st.session_state.PROCESSING_STATUS["cancelling"]:
                    print("Analysis cancelled by user")
                    st.session_state.PROCESSING_STATUS["message"] = (
                        "Analysis cancelled by user"
                    )
                    st.session_state.PROCESSING_STATUS["is_running"] = False
                    break

                if hasattr(step, "action_output") and step.action_output:
                    print(f"{step.action_output}\n")

                    if "MNA_PROCESS_COMPLETE" in str(step.action_output):
                        print("MNA process completion signal detected!")
                        st.session_state.PROCESSING_STATUS["is_running"] = False
                        st.session_state.PROCESSING_STATUS["message"] = (
                            "Analysis complete"
                        )
                        st.session_state.PROCESSING_STATUS["progress"] = 1.0
                        files_found = check_file_updates()
                        print(f"Found {files_found}/4 output files")
                        st.session_state.ANALYSIS_THREAD_STARTED = True

                        if files_found == 4:
                            st.stop()

                if hasattr(step, "agent_name") and step.agent_name:
                    st.session_state.PROCESSING_STATUS["current_agent"] = (
                        step.agent_name
                    )

                    if step.agent_name == "strategist":
                        st.session_state.PROCESSING_STATUS["current_task"] = (
                            "Generating strategy report"
                        )
                    elif step.agent_name == "researcher":
                        st.session_state.PROCESSING_STATUS["current_task"] = (
                            "Researching companies"
                        )
                    elif step.agent_name == "analyst":
                        st.session_state.PROCESSING_STATUS["current_task"] = (
                            "Analyzing financials"
                        )
                    elif step.agent_name == "valuator":
                        st.session_state.PROCESSING_STATUS["current_task"] = (
                            "Generating valuation report"
                        )

            check_file_updates()

        except Exception as e:
            error_msg = f"Analysis error: {str(e)}"
            st.session_state.PROCESSING_STATUS["error"] = error_msg
            st.session_state.PROCESSING_STATUS["message"] = "Error during analysis"
            print(f"Error: {error_msg}")

    finally:
        st.session_state.PROCESSING_STATUS["is_running"] = False


def run_analysis(analysis_container) -> None:
    try:
        if "PROCESSING_STATUS" not in st.session_state:
            st.session_state.PROCESSING_STATUS = {
                "current_agent": None,
                "current_task": None,
                "start_time": None,
                "progress": 0.0,
                "message": "Ready to start analysis",
                "error": None,
                "completed_tasks": set(),
                "total_tasks": 5,
                "is_running": False,
                "cancelling": False,
            }

        setup_file_watcher()
        check_file_updates()

        button_cols = analysis_container.columns([1, 2, 1])
        with button_cols[0]:
            if st.button(
                "🔄 Fetch Updates",
                key="fetch_updates_button",
                help="Manually check for file updates",
            ):
                files_found = check_file_updates()
                st.success(f"Found {files_found}/4 output files")
                if files_found < 4:
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.session_state.PROCESSING_STATUS["is_running"] = False
                    st.session_state.PROCESSING_STATUS["progress"] = 1.0
                    st.session_state.PROCESSING_STATUS["message"] = "Analysis complete"

        progress_placeholder = analysis_container.empty()
        status_placeholder = analysis_container.empty()
        files_container = analysis_container.container()

        if (
            not st.session_state.ANALYSIS_THREAD_STARTED
            and not st.session_state.PROCESSING_STATUS["is_running"]
        ):
            analysis_thread = threading.Thread(
                target=run_analysis_thread, args=(analysis_container,)
            )
            analysis_thread.daemon = True
            analysis_thread.start()

        files_to_check = {
            "strategy_info": "outputs/strategy_info.json",
            "strategy_report": "outputs/output.md",
            "companies": "outputs/companies.json",
            "valuation_report": "outputs/valuation.md",
        }

        progress = st.session_state.PROCESSING_STATUS["progress"]
        progress_placeholder.progress(progress, text=f"Progress: {int(progress*100)}%")

        status_message = st.session_state.PROCESSING_STATUS["message"]
        current_agent = st.session_state.PROCESSING_STATUS["current_agent"] or "None"
        current_task = (
            st.session_state.PROCESSING_STATUS["current_task"] or "Waiting to start"
        )

        status_placeholder.info(
            f"Status: {status_message} | Agent: {current_agent} | Task: {current_task}"
        )

        if st.session_state.PROCESSING_STATUS["error"]:
            error_msg = st.session_state.PROCESSING_STATUS["error"]
            status_placeholder.error(f"Error: {error_msg}")

            if status_placeholder.button("Retry Analysis"):
                st.session_state.PROCESSING_STATUS["error"] = None
                st.session_state.PROCESSING_STATUS["is_running"] = False
                st.session_state.ANALYSIS_THREAD_STARTED = False
                st.rerun()

        if st.session_state.PROCESSING_STATUS["is_running"]:
            if status_placeholder.button("Cancel Analysis"):
                st.session_state.PROCESSING_STATUS["cancelling"] = True
                status_placeholder.warning("Cancelling analysis... Please wait.")

        files_displayed = set()

        for file_key, file_path in files_to_check.items():
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                is_new = False
                if st.session_state.FILE_UPDATES[file_key] is not None:
                    last_update = st.session_state.FILE_UPDATES[file_key]
                    is_new = (datetime.now() - last_update).total_seconds() < 5

                expanded = st.session_state.EXPANDER_STATES[file_key] or is_new
                display_file(files_container, file_key, file_path, expanded)
                files_displayed.add(file_key)

        if (
            len(files_displayed) == 4
            and not st.session_state.PROCESSING_STATUS["is_running"]
        ):
            status_placeholder.success("✅ Analysis process completed successfully!")
            st.balloons()
        elif (
            not st.session_state.PROCESSING_STATUS["is_running"]
            and len(files_displayed) > 0
        ):
            missing_files = set(files_to_check.keys()) - files_displayed
            status_placeholder.warning(
                f"⚠️ Analysis complete but some files were not generated. Found {len(files_displayed)}/4 files. Missing: {', '.join(missing_files)}"
            )

        if st.session_state.PROCESSING_STATUS["is_running"]:
            time.sleep(1)
            st.rerun()

    except Exception as e:
        analysis_container.error(f"Error during analysis: {str(e)}")
        print(f"Error: {str(e)}")


def display_file(container, file_key, file_path, expanded=False):
    if file_key == "strategy_info":
        with container.expander("Strategy Information", expanded=expanded):
            try:
                with open(file_path, "r") as f:
                    strategy_data = json.load(f)
                    container.json(strategy_data)
            except Exception as e:
                container.error(f"Error reading strategy info: {str(e)}")

    elif file_key == "strategy_report":
        with container.expander("Strategy Report", expanded=expanded):
            try:
                with open(file_path, "r") as f:
                    container.markdown(f.read())
            except Exception as e:
                container.error(f"Error reading strategy report: {str(e)}")

    elif file_key == "companies":
        with container.expander("Researched Companies", expanded=expanded):
            try:
                with open(file_path, "r") as f:
                    companies_data = json.load(f)
                    container.json(companies_data)
            except Exception as e:
                container.error(f"Error reading companies data: {str(e)}")

    elif file_key == "valuation_report":
        with container.expander("Valuation Report", expanded=expanded):
            try:
                with open(file_path, "r") as f:
                    container.markdown(f.read())
            except Exception as e:
                container.error(f"Error reading valuation report: {str(e)}")

    if expanded and st.session_state.EXPANDER_STATES[file_key]:
        st.session_state.EXPANDER_STATES[file_key] = False


def initialize_gemini():
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


def main():
    st.set_page_config(
        page_title="M&A Automation",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    if "PROCESSING_STATUS" not in st.session_state:
        st.session_state.PROCESSING_STATUS = {
            "current_agent": None,
            "current_task": None,
            "start_time": None,
            "progress": 0.0,
            "message": "Ready to start analysis",
            "error": None,
            "completed_tasks": set(),
            "total_tasks": 5,
            "is_running": False,
            "cancelling": False,
        }

    if "FILE_UPDATES" not in st.session_state:
        st.session_state.FILE_UPDATES = {
            "strategy_info": None,
            "strategy_report": None,
            "companies": None,
            "valuation_report": None,
        }

    if "EXPANDER_STATES" not in st.session_state:
        st.session_state.EXPANDER_STATES = {
            "strategy_info": False,
            "strategy_report": False,
            "companies": False,
            "valuation_report": False,
        }

    if "STARTUP" not in st.session_state:
        st.session_state.STARTUP = True

    if "OBSERVER" not in st.session_state:
        st.session_state.OBSERVER = None

    if "ANALYSIS_THREAD_STARTED" not in st.session_state:
        st.session_state.ANALYSIS_THREAD_STARTED = False

    if "conversation_ended" not in st.session_state:
        st.session_state.conversation_ended = False

    if "analysis_started" not in st.session_state:
        st.session_state.analysis_started = False

    st.markdown(
        """
        <style>
        .css-18e3th9 .block-container {
            padding-top: 0rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.STARTUP:
        cleanup_outputs_directory()
        setup_file_watcher()
        st.session_state.STARTUP = False

    col1, col2, col3 = st.columns([0.25, 0.2, 0.25])
    with col2:
        st.image("resources/mna.png", use_container_width=True)

    if "bot" not in st.session_state:
        model = initialize_gemini()
        st.session_state.bot = MAStrategyBot(model=model)

    bot = st.session_state.bot

    chat_container = st.container()
    with chat_container:
        for message in bot.conversation_history:
            if message.role == "bot":
                st.chat_message("assistant").write(message.text)
            else:
                st.chat_message("user").write(message.text)

    if not st.session_state.conversation_ended:
        if not bot.conversation_history:
            initial_message, _ = bot.get_response()
            bot.conversation_history.append(Message(role="bot", text=initial_message))
            st.rerun()

        user_input = st.chat_input("Type your message here...")
        if user_input:
            bot.conversation_history.append(Message(role="user", text=user_input))
            with st.spinner("Thinking..."):
                bot_response, is_complete = bot.get_response(user_input)
            bot.conversation_history.append(Message(role="bot", text=bot_response))

            if is_complete or bot.current_stage in [Stage.COMPLETION, Stage.COMPLETE]:
                st.session_state.conversation_ended = True
                filename = bot.save_strategy_info()
                st.success(f"Strategy information has been saved to: {filename}")

                if st.button(
                    "▶️ Generate Strategy",
                    key="generate_button",
                    type="primary",
                ):
                    st.session_state.analysis_started = True
                    st.rerun()
            else:
                st.rerun()
    elif not st.session_state.analysis_started:
        st.subheader("Collected Strategy Information")
        st.json(vars(bot.collected_info))

        if st.button("▶️ Generate Strategy", key="generate_button", type="primary"):
            st.session_state.analysis_started = True
            st.rerun()
    else:
        tab1, tab2 = st.tabs(["Analysis Progress", "Summary"])

        with tab1:
            analysis_container = st.container()
            with analysis_container:
                run_analysis(analysis_container)

        with tab2:
            refresh_col1, refresh_col2, refresh_col3 = st.columns([0.25, 0.5, 0.25])
            with refresh_col1:
                if st.button("🔄 Refresh Data", key="refresh_summary_button"):
                    check_file_updates()
                    st.rerun()

            st.subheader("User Input")
            st.json(vars(bot.collected_info))

            st.subheader("Output Status")
            files_to_check = {
                "Strategy Info": "outputs/strategy_info.json",
                "Strategy Report": "outputs/output.md",
                "Companies List": "outputs/companies.json",
                "Valuation Report": "outputs/valuation.md",
            }

            file_status = {}
            for name, path in files_to_check.items():
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    file_status[name] = "✅ Available"
                else:
                    file_status[name] = "❌ Not available"

            st.table(file_status)

    with st.sidebar:
        col1, col2, col3 = st.columns([0.25, 1, 0.25])
        with col2:
            st.markdown("# 🛠️ Cleanup")

        col1, col2, col3 = st.columns([0.25, 0.4, 0.25])
        with col2:
            if st.button("Execute", type="primary"):
                cleanup_outputs_directory()
                st.session_state.conversation_ended = False
                st.session_state.analysis_started = False
                st.session_state.STARTUP = True
                st.rerun()


if __name__ == "__main__":
    main()
