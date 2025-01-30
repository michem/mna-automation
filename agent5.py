# agent5.py

from pathlib import Path
from typing import Annotated

import autogen
import pandas as pd
from autogen import ConversableAgent, register_function
from typing_extensions import Annotated

from config import OAI_CONFIG
from prompts import VALUATION_PROMPT
from tools import read_from_json, read_from_markdown, save_to_markdown

LLM_CONFIG = OAI_CONFIG


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
    is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x["content"],
    default_auto_reply="",
)

register_function(
    read_from_markdown,
    caller=analyzer,
    executor=executor,
    name="read_from_markdown",
    description="Read markdown file content",
)

register_function(
    read_from_json,
    caller=analyzer,
    executor=executor,
    name="read_from_json",
    description="Read JSON data from disk",
)

register_function(
    save_to_markdown,
    caller=analyzer,
    executor=executor,
    name="save_to_markdown",
    description="Save content to markdown file",
)

if __name__ == "__main__":
    analyzer.initiate_chat(
        executor,
        message="Generate comprehensive valuation report analyzing all companies against the acquisition strategy.",
    )
