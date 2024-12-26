# mna_automation/sequential.py

import os
from pathlib import Path

from autogen import ConversableAgent, UserProxyAgent

from agents.collection_agent import DataCollectorAgent, ExecutorAgent
from agents.strategy_agent import StrategyAgent, save_file
from agents.valuation_agent import AnalyzerAgent, ReporterAgent
from agents.web_search_agent import WebSearchAgent, extract_formatted_output
from config.settings import BASE_CONFIG, OUTPUT_DIR

STRATEGY_AGENT_NAME: str = "Strategy_Agent"
WEB_SEARCH_AGENT_NAME: str = "Web_Search_Agent"
DATA_COLLECTOR_AGENT_NAME: str = "Data_Collector_Agent"
EXECUTOR_AGENT_NAME: str = "Executor_Agent"
ANALYZER_AGENT_NAME: str = "Analyzer_Agent"
REPORTER_AGENT_NAME: str = "Reporter_Agent"


def init_agents():
    """Initialize agents and load financial data"""
    strategy_agent = StrategyAgent(name=STRATEGY_AGENT_NAME, llm_config=BASE_CONFIG)

    web_search_agent = WebSearchAgent(llm_config=BASE_CONFIG)

    data_collector_agent = DataCollectorAgent(
        name=DATA_COLLECTOR_AGENT_NAME, llm_config=BASE_CONFIG
    )
    executor_agent = ExecutorAgent(name=EXECUTOR_AGENT_NAME)

    analyzer_agent = AnalyzerAgent(name=ANALYZER_AGENT_NAME, llm_config=BASE_CONFIG)
    reporter_agent = ReporterAgent(name=REPORTER_AGENT_NAME, llm_config=BASE_CONFIG)

    return (
        strategy_agent,
        web_search_agent,
        data_collector_agent,
        executor_agent,
        analyzer_agent,
        reporter_agent,
    )


def main():
    """Run the sequential M&A analysis process"""
    (
        strategy_agent,
        web_search_agent,
        data_collector_agent,
        executor_agent,
        analyzer_agent,
        reporter_agent,
    ) = init_agents()

    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode="ALWAYS",
        llm_config=False,
        code_execution_config={"use_docker": False},
        is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
    )

    user_proxy.register_for_execution(
        name="save_file",
    )(save_file)

    chat_result = user_proxy.initiate_chat(
        strategy_agent,
        message="I need help developing an acquisition strategy for my company.",
        summary_method="reflection_with_llm",
    )
    strategy_path = Path(OUTPUT_DIR) / "strategy.md"
    with open(strategy_path, "r", encoding="utf-8") as f:
        strategy_output = f.read()
        print(f"Strategy read from {strategy_path}")

    web_search_result = web_search_agent.initiate_web_search(strategy_output)

    if not web_search_result.get("success", False):
        print(f"Error during web search: {web_search_result.get('error')}")
        return

    target_companies_output = extract_formatted_output(web_search_result["content"])

    targets_path = Path(OUTPUT_DIR) / "target_companies.md"
    with open(targets_path, "w", encoding="utf-8") as f:
        f.write(target_companies_output)

    print(f"Target companies saved to {targets_path}")

    chat_result = executor_agent.initiate_chat(
        data_collector_agent,
        message=(
            "Extract stock symbols and request financial data collection for companies in the content below. "
            "After processing all symbols, respond with exactly 'TERMINATE':\n\n"
            f"Strategy:\n\n{strategy_output}\n\n"
            f"Target Companies Table:\n\n{target_companies_output}"
        ),
    )

    chat_result = reporter_agent.initiate_chat(
        analyzer_agent,
        message=(
            "Analyze the following strategy and target companies. "
            "Perform valuations using the collected financial data, and generate a final report. "
            "After generating the report, respond with exactly 'TERMINATE':\n\n"
            f"Strategy:\n\n{strategy_output}\n\n"
            f"Target Companies Table:\n\n{target_companies_output}"
        ),
    )

    if chat_result:
        print(f"Final Report:\n{chat_result.summary}")
        report_path = Path(OUTPUT_DIR) / "summary.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(chat_result.summary)
        print(f"Final report saved to {report_path}")
    else:
        print("Error during report generation.")


if __name__ == "__main__":
    main()
