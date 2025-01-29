from autogen import ConversableAgent, UserProxyAgent, register_function
from autogen.tools import Tool
from configs import OAI_CONFIG

from prompts import STRATEGY_PROMPT
from tools import save_to_markdown

LLM_CONFIG = OAI_CONFIG


def is_termination_msg(msg):
    return (
        isinstance(msg.get("content"), str)
        and "TERMINATE" in msg.get("content", "").upper()
    )


pm = ConversableAgent(
    "pm",
    system_message=STRATEGY_PROMPT,
    llm_config=LLM_CONFIG,
    code_execution_config=False,
    human_input_mode="NEVER",
)

user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="ALWAYS",
    llm_config=False,
    code_execution_config={"use_docker": False},
    is_termination_msg=lambda x: x.get("content", "") and "TERMINATE" in x["content"],
)

register_function(
    save_to_markdown,
    caller=pm,
    executor=user_proxy,
    name="save_to_markdown",
    description="Save the given content to a markdown file.",
)


result = user_proxy.initiate_chat(
    pm,
    message="Hello",
)
