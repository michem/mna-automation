import os

import autogen
from autogen import ConversableAgent, register_function
from configs import GEMINI_CONFIG, OAI_CONFIG

from prompts import critic_prompt, google_researcher
from tools import (
    google_search,
    read_from_markdown,
    save_response_json,
    save_to_markdown,
)

LLM_CONFIG = OAI_CONFIG


human_proxy = ConversableAgent(
    "human_proxy",
    llm_config=LLM_CONFIG,
    human_input_mode="ALWAYS",  # always ask for human input
)

researcher = ConversableAgent(
    "researcher",
    llm_config=LLM_CONFIG,
    system_message=google_researcher,
    human_input_mode="NEVER",
)

critic = ConversableAgent(
    "critic",
    llm_config=LLM_CONFIG,
    system_message=critic_prompt,
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
    read_from_markdown,
    caller=researcher,
    executor=executor,
    name="read_from_markdown",
    description="Read the content from a markdown file.",
)
register_function(
    google_search,
    caller=researcher,
    executor=executor,
    name="google_search",
    description="Search the web for a given string and return the results.",
)
register_function(
    save_response_json,
    caller=researcher,
    executor=executor,
    name="save_response_json",
    description="Save the given JSON string to a file.",
)

register_function(
    read_from_markdown,
    caller=critic,
    executor=executor,
    name="read_from_markdown",
    description="Read the content from a markdown file.",
)

register_function(
    save_response_json,
    caller=critic,
    executor=executor,
    name="save_response_json",
    description="Save the given JSON string to a file.",
)


researcher.register_nested_chats(
    trigger=human_proxy,
    chat_queue=[
        {
            "sender": executor,
            "recipient": researcher,
            "message": "Which tool you want to call?",
            # "max_turns": 5,
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
    message="Hello",
)
