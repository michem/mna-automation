from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel

from agent1 import managed_strategist
from agent2 import managed_critic, managed_researcher
from agent3n4 import managed_analyst
from agent5 import managed_valuator
from config import MODEL_API_KEY, MODEL_ID, VALUATION_REPORT_PATH
from tools import *

load_dotenv()

MANAGER_PROMPT = f"""You are the managing director of a Merger and Acquisitions consultancy firm, responsible for overseeing the entire M&A process and coordinating a team of specialized professionals. You do not perform any tasks directly but instead delegate responsibilities to your team members based on their expertise. You must end the chat once the final valuation report ({VALUATION_REPORT_PATH}) has been saved as in the execution log.
"""

model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)
manager = CodeAgent(
    tools=[read_from_json, save_to_json],
    additional_authorized_imports=["json", "os"],
    model=model,
    managed_agents=[
        managed_strategist,
        managed_researcher,
        managed_critic,
        managed_analyst,
        managed_valuator,
    ],
)

# response = manager.run(MANAGER_PROMPT, single_step=True)
