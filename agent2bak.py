from autogen import ConversableAgent, register_function

from config import OAI_CONFIG
from prompts import CRITIC_PROMPT, RESEARCHER_PROMPT
from tools import (
    get_companies,
    get_names_and_summaries,
    get_options,
    read_from_markdown,
    save_to_json,
)

LLM_CONFIG = OAI_CONFIG


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
    is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x["content"],
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
    get_options,
    caller=researcher,
    executor=executor,
    name="get_options",
    description="Retrieve options for a given parameter.",
)
register_function(
    get_companies,
    caller=researcher,
    executor=executor,
    name="get_companies",
    description="Retrieve companies based on specified filters.",
)
register_function(
    get_names_and_summaries,
    caller=researcher,
    executor=executor,
    name="get_names_and_summaries",
    description="Get the names and summaries of companies from the JSON file.",
)

register_function(
    read_from_markdown,
    caller=critic,
    executor=executor,
    name="read_from_markdown",
    description="Read the content from a markdown file.",
)
register_function(
    get_names_and_summaries,
    caller=critic,
    executor=executor,
    name="get_names_and_summaries",
    description="Get the names and summaries of companies from the JSON file.",
)

register_function(
    save_to_json,
    caller=critic,
    executor=executor,
    name="save_to_json",
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
