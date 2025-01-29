import os

from dotenv import load_dotenv
from smolagents import LiteLLMModel, ToolCallingAgent

from config import MODEL_API_KEY, MODEL_ID, STRATEGY_REPORT_PATH
from prompts import STRATEGY_PROMPT
from tools import human_intervention, save_to_markdown

load_dotenv()


model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.2,
)
agent = ToolCallingAgent(
    tools=[save_to_markdown, human_intervention],
    model=model,
    system_prompt=STRATEGY_PROMPT,
    max_steps=20,
)

response = agent.run(
    "Hello, I need your help developing and subsequently, saving an acquisition strategy.",
    reset=False,
)
