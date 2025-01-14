import os

import autogen
from autogen import ConversableAgent, register_function
from configs import GEMINI_CONFIG, OAI_CONFIG

from prompts import collector_prompt, critic_prompt, researcher_prompt_fd
from tools import (
    collect_and_save_fmp_data,
    get_companies,
    get_names_and_summaries,
    get_number_of_companies,
    get_options,
    read_from_markdown,
    read_json_from_disk,
    save_response_json,
    save_to_markdown,
)

LLM_CONFIG = OAI_CONFIG
human_proxy = ConversableAgent(
    "human_proxy",
    llm_config=LLM_CONFIG,
    human_input_mode="ALWAYS",  # always ask for human input
)

collector = ConversableAgent(
    "collector",
    llm_config=LLM_CONFIG,
    system_message=collector_prompt,
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
    collect_and_save_fmp_data,
    caller=collector,
    executor=executor,
    name="collect_and_save_fmp_data",
    description="Collect FMP data and save it, returning only a status message",
)
register_function(
    read_json_from_disk,
    caller=collector,  # Add multiple callers here
    executor=executor,
    name="read_json_from_disk",
    description="Get the companies' symbols, names and summaries from disk.",
)

collector.register_nested_chats(
    trigger=human_proxy,
    chat_queue=[
        {
            "sender": executor,
            "recipient": collector,
            "message": "Which tool you want to call?",
            # "max_turns": 5,
        },
    ],
)

human_proxy.initiate_chat(
    collector,
    message="Begin",
)
