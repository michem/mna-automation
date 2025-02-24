from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel

from config import MODEL_API_KEY, MODEL_ID
from prompts import VALUATION_PROMPT
from tools import read_from_json, read_from_markdown, save_to_markdown

load_dotenv()


model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.2,
)
valuator = CodeAgent(
    tools=[read_from_markdown, read_from_json, save_to_markdown],
    model=model,
    additional_authorized_imports=["os"],
    max_steps=20,
    name="valuator",
    description=VALUATION_PROMPT,
)
