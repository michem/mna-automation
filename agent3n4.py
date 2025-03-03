from dotenv import load_dotenv
from smolagents import LiteLLMModel, ToolCallingAgent

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
    temperature=0.2,
)
analyst = ToolCallingAgent(
    name="analyst",
    tools=[
        collect_financial_metrics,
        get_company_profile,
        perform_valuation_analysis,
        read_from_json,
        read_from_markdown,
    ],
    model=model,
    max_steps=50,
    description="A resilient financial analyst agent that collects comprehensive company metrics and performs valuation analysis. It processes each company independently, continues even when individual API calls fail, and ensures financial data collection proceeds for all viable companies while handling errors gracefully.",
)

if __name__ == "__main__":
    response = analyst.run(
        ANALYST_PROMPT,
        reset=False,
    )
