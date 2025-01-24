import os
from pathlib import Path

import autogen
from autogen import ConversableAgent, register_function
from configs import OAI_CONFIG

from prompts import analyst_prompt
from tools import (
    collect_financial_metrics,
    get_company_profile,
    perform_valuation_analysis,
    read_from_markdown,
    read_json_from_disk,
)

LLM_CONFIG = OAI_CONFIG

analyst = ConversableAgent(
    "analyst",
    llm_config=LLM_CONFIG,
    system_message=analyst_prompt,
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

register_function(
    collect_financial_metrics,
    caller=analyst,
    executor=executor,
    name="collect_financial_metrics",
    description="Collect financial metrics for a company",
)

register_function(
    get_company_profile,
    caller=analyst,
    executor=executor,
    name="get_company_profile",
    description="Get company profile information",
)

register_function(
    perform_valuation_analysis,
    caller=analyst,
    executor=executor,
    name="perform_valuation_analysis",
    description="Perform valuation analysis on collected metrics",
)

register_function(
    read_json_from_disk,
    caller=analyst,
    executor=executor,
    name="read_json_from_disk",
    description="Read JSON data from disk",
)

register_function(
    read_from_markdown,
    caller=analyst,
    executor=executor,
    name="read_from_markdown",
    description="Read content from markdown file",
)

if __name__ == "__main__":
    executor.initiate_chat(
        analyst,
        message="Begin the analysis process. First, read the strategy report and the screened companies from the outputs directory.",
    )
