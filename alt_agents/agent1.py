import autogen
from autogen import ConversableAgent, register_function
import os
from configs import OAI_CONFIG, GEMINI_CONFIG
from prompts import (
    project_manager_prompt,
    motivational_coach_prompt,
    strategy_prompt,
    dummy_client_prompt,
    strategy_prompt_1,
    strategy_prompt_3,
    strategy_prompt_2,
)
from tools import save_to_markdown

LLM_CONFIG = OAI_CONFIG


pm = ConversableAgent(
    "pm",
    system_message=strategy_prompt_2,
    llm_config=LLM_CONFIG,
    code_execution_config=False,
    human_input_mode="NEVER",  # Never ask for human input.
)


dummy_client = ConversableAgent(
    "dummy_client",
    system_message=dummy_client_prompt,
    llm_config=LLM_CONFIG,
    code_execution_config=False,
    function_map=None,
    human_input_mode="ALWAYS",
)


human_proxy = ConversableAgent(
    "human_proxy",
    llm_config=LLM_CONFIG,
    human_input_mode="ALWAYS",  # always ask for human input
)

register_function(
    save_to_markdown,
    caller=human_proxy,  # The agent can suggest calls to the tool.
    executor=pm,  # The  agent can execute the tool calls.
    name="save_to_markdown",  # By default, the function name is used as the tool name.
    description="Save the given content to a markdown file.",  # A description of the tool.
)


result = human_proxy.initiate_chat(
    pm,
    message="Hello",
)
