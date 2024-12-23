# mna_automation/data_collection.py

import os
from pathlib import Path

from agents.collection_agent import DataCollectorAgent, ExecutorAgent
from config.settings import OUTPUT_DIR


def read_input_files() -> str:
    """Read both strategy and target companies files"""
    strategy_path = Path(OUTPUT_DIR) / "strategy_hc.md"
    targets_path = Path(OUTPUT_DIR) / "target_companies.md"

    if not strategy_path.exists():
        raise FileNotFoundError(
            "Strategy file not found. Please run the strategy agent first."
        )
    if not targets_path.exists():
        raise FileNotFoundError(
            "Target companies file not found. Please run the web search agent first."
        )

    with open(strategy_path, "r", encoding="utf-8") as f:
        strategy_content = f.read()

    with open(targets_path, "r", encoding="utf-8") as f:
        targets_content = f.read()

    return (
        f"Strategy:\n\n{strategy_content}\n\n"
        f"Target Companies Table:\n\n{targets_content}"
    )


def main():
    content = read_input_files()

    collector = DataCollectorAgent()
    executor = ExecutorAgent()

    executor.initiate_chat(
        collector,
        message=(
            "Extract stock symbols and request financial data collection for companies in the content below. "
            "After processing all symbols, respond with exactly 'TERMINATE':\n\n"
            f"{content}"
        ),
    )


if __name__ == "__main__":
    main()
