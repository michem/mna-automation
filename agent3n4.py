from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel, ManagedAgent, ToolCallingAgent

from config import MODEL_API_KEY, MODEL_ID
from prompts import ANALYST_PROMPT
from tools import (
    collect_financial_metrics,
    get_company_profile,
    perform_valuation_analysis,
    read_from_json,
    read_from_markdown,
)

load_dotenv()


model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)
analyst = ToolCallingAgent(
    tools=[
        collect_financial_metrics,
        get_company_profile,
        perform_valuation_analysis,
        read_from_json,
        read_from_markdown,
    ],
    model=model,
    max_steps=20,
)
managed_analyst = ManagedAgent(
    agent=analyst,
    name="analyst",
    description=ANALYST_PROMPT,
)
