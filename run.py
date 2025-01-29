import os
from pathlib import Path
from typing import Annotated

import autogen
from autogen import ConversableAgent, UserProxyAgent, register_function
from dotenv import load_dotenv

from configs import (
    COMPANIES_JSON_PATH,
    CRITIC_COMPANIES_JSON_PATH,
    OAI_CONFIG,
    OUTPUT_DIR,
    STRATEGY_REPORT_PATH,
)
from prompts import (
    ANALYST_PROMPT,
    CRITIC_PROMPT,
    RESEARCHER_PROMPT,
    STRATEGY_PROMPT,
    VALUATION_PROMPT,
)
from tools import (
    collect_financial_metrics,
    get_companies,
    get_company_profile,
    get_names_and_summaries,
    get_options,
    perform_valuation_analysis,
    read_from_markdown,
    read_json_from_disk,
    save_response_json,
    save_to_markdown,
)

load_dotenv()
LLM_CONFIG = OAI_CONFIG


def ensure_output_directory():
    """Ensure the output directory exists"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_strategy_phase() -> bool:
    """Run the strategy development phase with agent1"""
    print("\n=== Starting Strategy Phase ===")

    pm = ConversableAgent(
        "pm",
        system_message=STRATEGY_PROMPT,
        llm_config=LLM_CONFIG,
        code_execution_config=False,
        human_input_mode="NEVER",
    )

    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="ALWAYS",
        llm_config=False,
        code_execution_config={"use_docker": False},
        is_termination_msg=lambda x: x.get("content", "")
        and "TERMINATE" in x["content"],
    )

    register_function(
        save_to_markdown,
        caller=pm,
        executor=user_proxy,
        name="save_to_markdown",
        description="Save the given content to a markdown file.",
    )

    user_proxy.initiate_chat(
        pm,
        message="Hello, I need your help developing an acquisition strategy.",
    )

    if not os.path.exists(STRATEGY_REPORT_PATH):
        print("Strategy phase failed: No strategy report generated")
        return False

    print("Strategy phase completed successfully")
    return True


def run_research_phase() -> bool:
    """Run the company research phase with agent2"""
    print("\n=== Starting Research Phase ===")

    human_proxy = ConversableAgent(
        "human_proxy",
        llm_config=LLM_CONFIG,
        max_consecutive_auto_reply=0,
        human_input_mode="NEVER",
    )

    researcher = ConversableAgent(
        "researcher",
        llm_config=LLM_CONFIG,
        system_message=RESEARCHER_PROMPT,
        human_input_mode="NEVER",
    )

    critic = ConversableAgent(
        "critic",
        llm_config=LLM_CONFIG,
        system_message=CRITIC_PROMPT,
        human_input_mode="NEVER",
    )

    executor = ConversableAgent(
        "executor",
        llm_config=False,
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "")
        and "TERMINATE" in x["content"],
        default_auto_reply="",
    )

    for tool, desc in [
        (read_from_markdown, "Read the content from a markdown file."),
        (get_options, "Retrieve options for a given parameter."),
        (get_companies, "Retrieve companies based on specified filters."),
        (
            get_names_and_summaries,
            "Get the names and summaries of companies from the JSON file.",
        ),
    ]:
        register_function(
            tool,
            caller=researcher,
            executor=executor,
            name=tool.__name__,
            description=desc,
        )

    for tool, desc in [
        (read_from_markdown, "Read the content from a markdown file."),
        (
            get_names_and_summaries,
            "Get the names and summaries of companies from the JSON file.",
        ),
        (save_response_json, "Save the given JSON string to a file."),
    ]:
        register_function(
            tool, caller=critic, executor=executor, name=tool.__name__, description=desc
        )

    researcher.register_nested_chats(
        trigger=human_proxy,
        chat_queue=[
            {
                "sender": executor,
                "recipient": researcher,
                "message": "Which tool you want to call?",
            },
            {
                "sender": executor,
                "recipient": critic,
                "message": "Which tool you want to call?",
            },
        ],
    )

    human_proxy.initiate_chat(
        researcher,
        message="Please start the research process based on the strategy report.",
    )

    if not os.path.exists(COMPANIES_JSON_PATH) or not os.path.exists(
        CRITIC_COMPANIES_JSON_PATH
    ):
        print("Research phase failed: Missing output files")
        return False

    print("Research phase completed successfully")
    return True


def run_data_collection_phase() -> bool:
    """Run the data collection phase with agent3&4"""
    print("\n=== Starting Data Collection Phase ===")

    analyst = ConversableAgent(
        "analyst",
        llm_config=LLM_CONFIG,
        system_message=ANALYST_PROMPT,
        human_input_mode="NEVER",
    )

    executor = ConversableAgent(
        "executor",
        llm_config=False,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: msg.get("content") is not None
        and "TERMINATE" in msg["content"],
        default_auto_reply="",
    )

    for tool, desc in [
        (collect_financial_metrics, "Collect financial metrics for a company"),
        (get_company_profile, "Get company profile information"),
        (perform_valuation_analysis, "Perform valuation analysis on collected metrics"),
        (read_json_from_disk, "Read JSON data from disk"),
        (read_from_markdown, "Read content from markdown file"),
    ]:
        register_function(
            tool,
            caller=analyst,
            executor=executor,
            name=tool.__name__,
            description=desc,
        )

    executor.initiate_chat(
        analyst,
        message="Begin the analysis process. First, read the strategy report and the screened companies from the outputs directory.",
    )

    data_dir = os.path.join(OUTPUT_DIR, "fmp_data")
    if not os.path.exists(data_dir) or len(os.listdir(data_dir)) == 0:
        print("Data collection phase failed: No data files generated")
        return False

    print("Data collection phase completed successfully")
    return True


def run_valuation_phase() -> bool:
    """Run the valuation analysis phase with agent5"""
    print("\n=== Starting Valuation Phase ===")

    analyzer = ConversableAgent(
        "analyzer",
        llm_config=LLM_CONFIG,
        system_message=VALUATION_PROMPT,
        human_input_mode="NEVER",
    )

    executor = ConversableAgent(
        "executor",
        llm_config=False,
        human_input_mode="NEVER",
        is_termination_msg=lambda x: x.get("content", "")
        and "TERMINATE" in x["content"],
        default_auto_reply="",
    )

    for tool, desc in [
        (read_from_markdown, "Read markdown file content"),
        (read_json_from_disk, "Read JSON data from disk"),
        (save_to_markdown, "Save content to markdown file"),
    ]:
        register_function(
            tool,
            caller=analyzer,
            executor=executor,
            name=tool.__name__,
            description=desc,
        )

    analyzer.initiate_chat(
        executor,
        message="Generate comprehensive valuation report analyzing all companies against the acquisition strategy.",
    )

    valuation_report = os.path.join(OUTPUT_DIR, "valuation.md")
    if not os.path.exists(valuation_report):
        print("Valuation phase failed: No valuation report generated")
        return False

    print("Valuation phase completed successfully")
    return True


def main():
    """Run the complete M&A analysis process sequentially"""
    print("Starting M&A Analysis Process")
    ensure_output_directory()

    if not run_strategy_phase():
        return

    if not run_research_phase():
        return

    if not run_data_collection_phase():
        return

    if not run_valuation_phase():
        return

    print("\n=== M&A Analysis Process Completed Successfully ===")
    print(f"All outputs have been saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
