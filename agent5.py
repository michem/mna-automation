from dotenv import load_dotenv
from smolagents import LiteLLMModel, ToolCallingAgent

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
    name="valuator",
    tools=[read_from_markdown, read_from_json, save_to_markdown],
    model=model,
    max_steps=20,
    description="A financial analyst agent that generates a comprehensive M&A strategy report based on the provided prompt.",
)

if __name__ == "__main__":
    response = valuator.run(
        VALUATION_PROMPT,
        reset=False,
    )
