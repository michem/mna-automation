# mna_automation/web_targets.py

import os
from pathlib import Path

from agents.web_search_agent import WebSearchAgent
from config.settings import OUTPUT_DIR


def read_strategy_file() -> str:
    strategy_path = Path(OUTPUT_DIR) / "strategy.md"
    if not strategy_path.exists():
        raise FileNotFoundError(
            "Strategy file not found. Please run the strategy agent first."
        )

    with open(strategy_path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    strategy_content = read_strategy_file()
    web_agent = WebSearchAgent()

    print("Searching for target companies...")
    web_agent.initiate_web_search(strategy_content)


if __name__ == "__main__":
    main()
