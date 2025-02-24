from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel

from agent1 import strategist
from agent2 import critic, researcher
from agent3n4 import analyst
from agent5 import valuator
from config import (
    COMPANIES_JSON_PATH,
    CRITIC_COMPANIES_JSON_PATH,
    DATA_COLLECTION_PATH,
    MODEL_API_KEY,
    MODEL_ID,
    STRATEGY_REPORT_PATH,
    VALUATION_REPORT_PATH,
)
from prompts import (
    ANALYST_PROMPT,
    CRITIC_PROMPT,
    RESEARCHER_PROMPT,
    STRATEGY_PROMPT,
    VALUATION_PROMPT,
)

load_dotenv()

MANAGER_PROMPT = f"""You are the managing director of a Merger and Acquisitions consultancy firm, responsible for overseeing the entire M&A process and coordinating a team of specialized professionals.

Pass on verbatim the following prompts to the respective agents:
1. STRATEGIST: ```{STRATEGY_PROMPT}```
2. RESEARCHER: ```{RESEARCHER_PROMPT}```
3. CRITIC: ```{CRITIC_PROMPT}```
4. ANALYST: ```{ANALYST_PROMPT}```
5. VALUATOR: ```{VALUATION_PROMPT}```

Your task is to ensure that the agents work together effectively, leveraging their expertise to achieve the best possible outcome for the M&A process. You will need to manage the workflow, facilitate communication between agents, and ensure that all aspects of the M&A process are covered.
"""

model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.2,
)
manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[
        strategist,
        researcher,
        critic,
        analyst,
        valuator,
    ],
)

if __name__ == "__main__":
    response = manager.run(MANAGER_PROMPT)
