# mna_automation/strategy_writer.py

import os
from pathlib import Path
from typing import Optional

from autogen import UserProxyAgent

from agents.strategy_agent import StrategyAgent, save_file
from config.settings import BASE_CONFIG, OUTPUT_DIR


def init_agents():
    """Initialize the strategy agent and user proxy"""
    strategy_agent = StrategyAgent()

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

    return strategy_agent, user_proxy


def main():
    """Run the strategy generation workflow"""
    strategy_agent, user_proxy = init_agents()

    user_proxy.initiate_chat(
        strategy_agent,
        message="I need help developing an acquisition strategy for my company.",
    )


if __name__ == "__main__":
    main()
