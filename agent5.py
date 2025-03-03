from dotenv import load_dotenv
from smolagents import LiteLLMModel, ManagedAgent, ToolCallingAgent

from config import MODEL_API_KEY, MODEL_ID
from prompts import VALUATION_PROMPT
from tools import read_from_json, read_from_markdown, save_to_markdown

load_dotenv()


model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.2,
)
valuator = ToolCallingAgent(
    tools=[read_from_markdown, read_from_json, save_to_markdown],
    model=model,
    max_steps=50,
)
managed_valuator = ManagedAgent(
    agent=valuator,
    name="valuator",
    description="A comprehensive valuator agent that analyzes financial data, generates insightful valuation reports, and provides actionable acquisition recommendations. It works effectively with partial data, provides reasoned analysis even with limitations, and always produces a complete valuation report regardless of upstream data quality.",
)

if __name__ == "__main__":
    response = valuator.run(
        VALUATION_PROMPT,
        reset=False,
    )
