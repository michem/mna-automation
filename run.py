import os
from pathlib import Path

from agent1 import pm, user_proxy
from agent2 import executor as research_executor
from agent2 import researcher
from agent3n4 import critic, data_collector
from agent3n4 import executor as dc_executor
from agent5 import analyzer
from agent5 import executor as analyzer_executor
from configs import (
    COMPANIES_JSON_PATH,
    CRITIC_COMPANIES_JSON_PATH,
    OUTPUT_DIR,
    STRATEGY_REPORT_PATH,
)
from dotenv import load_dotenv

load_dotenv()


def ensure_output_directory():
    """Ensure the output directory exists"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_strategy_phase():
    """Run the strategy development phase with agent1"""
    print("\n=== Starting Strategy Phase ===")
    try:
        user_proxy.initiate_chat(
            pm,
            message="I need help developing an acquisition strategy for my company.",
        )
        if not os.path.exists(STRATEGY_REPORT_PATH):
            print("Error: Strategy report was not generated")
            return False
        print("Strategy phase completed successfully")
        return True
    except Exception as e:
        print(f"Error in strategy phase: {str(e)}")
        return False


def run_research_phase():
    """Run the company research phase with agent2"""
    print("\n=== Starting Research Phase ===")
    try:
        researcher.initiate_chat(
            research_executor,
            message="Begin company research based on the strategy report",
        )
        if not os.path.exists(COMPANIES_JSON_PATH):
            print("Error: Companies list was not generated")
            return False
        print("Research phase completed successfully")
        return True
    except Exception as e:
        print(f"Error in research phase: {str(e)}")
        return False


def run_data_collection_phase():
    """Run the data collection and critic phase with agent3&4"""
    print("\n=== Starting Data Collection & Critic Phase ===")
    try:
        data_collector.initiate_chat(
            dc_executor,
            message="Begin collecting financial data for the target companies",
        )

        critic.initiate_chat(
            dc_executor,
            message="Analyze collected data and filter companies",
        )

        if not os.path.exists(CRITIC_COMPANIES_JSON_PATH):
            print("Error: Critic analysis was not generated")
            return False
        print("Data collection and critic phase completed successfully")
        return True
    except Exception as e:
        print(f"Error in data collection phase: {str(e)}")
        return False


def run_valuation_phase():
    """Run the valuation analysis phase with agent5"""
    print("\n=== Starting Valuation Phase ===")
    try:
        analyzer.initiate_chat(
            analyzer_executor,
            message="Generate comprehensive valuation report analyzing all companies against the acquisition strategy.",
        )
        valuation_report_path = Path(OUTPUT_DIR) / "valuation.md"
        if not os.path.exists(valuation_report_path):
            print("Error: Valuation report was not generated")
            return False
        print("Valuation phase completed successfully")
        return True
    except Exception as e:
        print(f"Error in valuation phase: {str(e)}")
        return False


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
