from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel

from config import MODEL_API_KEY, MODEL_ID
from prompts import STRATEGY_PROMPT
from tools import read_from_json, save_to_markdown

load_dotenv()


model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.6,
)
strategist = CodeAgent(
    name="strategist",
    tools=[save_to_markdown, read_from_json],
    additional_authorized_imports=["json", "os"],
    model=model,
    max_steps=10,
    description="A strategist agent that generates a comprehensive M&A strategy report based on the client's requirements and market analysis.,",
)

if __name__ == "__main__":
    response = strategist.run(
        STRATEGY_PROMPT,
        reset=False,
    )
