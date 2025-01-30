from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel, ManagedAgent

from config import MODEL_API_KEY, MODEL_ID
from prompts import RESEARCHER_PROMPT
from tools import 

load_dotenv()


model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)
researcher = CodeAgent(
    tools=[],
    model=model,
    additional_authorized_imports=["json", "os"],
    max_steps=15,
)
managed_researcher = ManagedAgent(
    agent=researcher,
    name="researcher",
    description=RESEARCHER_PROMPT,
)

response = researcher.run(
    RESEARCHER_PROMPT,
    reset=False,
)
