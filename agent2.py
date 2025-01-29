import os

from dotenv import load_dotenv
from smolagents import LiteLLMModel, ToolCallingAgent

from config import COMPANIES_JSON_PATH, MODEL_API_KEY, MODEL_ID, STRATEGY_REPORT_PATH
from prompts import RESEARCHER_PROMPT
from tools import (
    get_companies,
    get_names_and_summaries,
    get_options,
    read_from_markdown,
    save_response_json,
)

load_dotenv()


model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.2,
)
research_agent = ToolCallingAgent(
    tools=[
        read_from_markdown,
        get_options,
        get_companies,
        get_names_and_summaries,
        save_response_json,
    ],
    model=model,
    system_prompt=RESEARCHER_PROMPT,
    max_steps=20,
)

conversation_active = True
output_file = COMPANIES_JSON_PATH
first_message = True

research_response = research_agent.run(
    "Please start the research process based on the strategy report.", reset=False
)
