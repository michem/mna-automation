# mna_automation/targets_app.py

import asyncio
import re
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from autogen import ConversableAgent

from agents.web_search_agent import WebSearchAgent
from config.settings import BASE_CONFIG

INITIAL_PROMPT = """Please provide your acquisition strategy report. This will be used to search for potential target companies that match your criteria.

The strategy should include:
- Target company profile
- Industry focus
- Size requirements
- Key technologies or capabilities sought
- Geographic preferences"""


def parse_markdown_table(table_str: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """Parse markdown table into headers and rows."""
    lines = [line.strip() for line in table_str.split("\n")]
    lines = [line for line in lines if line and line.strip("| ")]

    if len(lines) < 3:
        raise ValueError("Invalid table format")
    headers = [h.strip() for h in lines[0].split("|")[1:-1]]
    rows = []

    for line in lines[2:]:
        if not line.startswith("|"):
            continue
        values = [cell.strip() for cell in line.split("|")[1:-1]]
        if len(values) == len(headers):
            row_dict = dict(zip(headers, values))
            rows.append(row_dict)

    if not rows:
        raise ValueError("No valid data rows found in table")

    return headers, rows


class StreamingWebSearchAgent(WebSearchAgent):
    def __init__(self, llm_config):
        super().__init__(llm_config=llm_config)
        self.researcher.human_input_mode = "NEVER"
        self.web_surfer.human_input_mode = "NEVER"

    async def a_get_response(
        self,
        strategy_report: str,
    ) -> AsyncGenerator[str, None]:
        """Stream the conversation between researcher and web surfer"""
        try:
            # self.researcher.reset()
            # self.web_surfer.reset()

            initial_message = f"Here is the acquisition strategy report. Generate search queries based on the target profile, then execute them sequentially:\n\n{strategy_report}"

            chat_result = self.web_surfer.initiate_chat(
                self.researcher,
                message=initial_message,
                silent=False,
            )

            final_message = self.researcher.last_message()["content"]
            if "`TERMINATE`" in final_message:
                # Extract everything between the first and last line containing "|"
                lines = final_message.split("\n")
                table_lines = []
                start_idx = None
                end_idx = None

                for i, line in enumerate(lines):
                    if "|" in line:
                        if start_idx is None:
                            start_idx = i
                        end_idx = i

                if start_idx is not None and end_idx is not None:
                    table_str = "\n".join(lines[start_idx : end_idx + 1])
                    try:
                        headers, rows = parse_markdown_table(table_str)
                        df = pd.DataFrame(rows)
                        yield {"type": "table", "data": df}
                    except Exception as e:
                        st.error(f"Error parsing table: {str(e)}")
                        yield {
                            "type": "error",
                            "data": f"Error parsing table: {str(e)}",
                        }
                else:
                    yield {
                        "type": "error",
                        "data": "No results table found in the response.",
                    }
            else:
                yield {"type": "error", "data": "Search did not complete successfully."}

        except Exception as e:
            st.error(f"Error during web search: {str(e)}")
            yield {
                "type": "error",
                "data": "An error occurred during the search process.",
            }


def init_agent() -> StreamingWebSearchAgent:
    """Initialize the web search agent with error handling"""
    try:
        return StreamingWebSearchAgent(
            llm_config=BASE_CONFIG,
        )
    except Exception as e:
        st.error(f"Failed to initialize agent: {str(e)}")
        st.stop()


def initialize_session_state() -> None:
    """Initialize the session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.web_search_agent = init_agent()
        st.session_state.search_completed = False
        st.session_state.messages.append(
            {"role": "assistant", "content": INITIAL_PROMPT}
        )


def display_chat_history() -> None:
    """Display chat history with markdown rendering"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


async def process_strategy_input(strategy: str) -> None:
    """Process the strategy input and perform web search"""
    try:
        response_placeholder = st.empty()

        async for result in st.session_state.web_search_agent.a_get_response(strategy):
            if isinstance(result, dict):
                if result["type"] == "table":
                    st.table(result["data"])
                    st.session_state.messages.append(
                        {"role": "assistant", "content": result["data"].to_markdown()}
                    )
                else:
                    response_placeholder.error(result["data"])
                    st.session_state.messages.append(
                        {"role": "assistant", "content": result["data"]}
                    )

        st.session_state.search_completed = True

    except Exception as e:
        st.error(f"Error processing strategy: {str(e)}")


def main() -> None:
    """Main application with improved error handling and UX"""
    st.title("M&A Target Company Search")

    initialize_session_state()
    display_chat_history()

    if not st.session_state.search_completed:
        if strategy := st.chat_input("Enter your acquisition strategy"):
            st.session_state.messages.append({"role": "user", "content": strategy})
            with st.chat_message("user"):
                st.markdown(strategy)

            with st.chat_message("assistant"):
                with st.spinner("Searching for target companies..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(process_strategy_input(strategy))
                    finally:
                        loop.close()
    else:
        st.success("Target company search completed!")


if __name__ == "__main__":
    main()
