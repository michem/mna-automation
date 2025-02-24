from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel, ManagedAgent, ToolCallingAgent

from config import MODEL_API_KEY, MODEL_ID
from prompts import CRITIC_PROMPT, RESEARCHER_PROMPT
from tools import (
    get_companies,
    get_names_and_summaries,
    get_options,
    read_from_json,
    read_from_markdown,
    save_to_json,
)

load_dotenv()


model_r = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)
model_c = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.2,
)

researcher = CodeAgent(
    tools=[get_companies, read_from_markdown, get_options, save_to_json],
    additional_authorized_imports=["json", "os"],
    model=model_r,
    max_steps=15,
)
managed_researcher = ManagedAgent(
    agent=researcher,
    name="researcher",
    description=RESEARCHER_PROMPT,
)

critic = ToolCallingAgent(
    tools=[get_names_and_summaries, read_from_json, save_to_json, read_from_markdown],
    model=model_c,
    max_steps=10,
)
managed_critic = ManagedAgent(
    agent=critic,
    name="critic",
    description=CRITIC_PROMPT,
)
