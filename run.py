from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel

from agent1 import managed_strategist
from agent2 import managed_critic, managed_researcher
from agent3n4 import managed_analyst
from agent5 import managed_valuator
from config import MODEL_API_KEY, MODEL_ID, VALUATION_REPORT_PATH
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

Stop the chat/process once {VALUATION_REPORT_PATH } is generated.
"""

model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)
manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[
        managed_strategist,
        managed_researcher,
        managed_critic,
        managed_analyst,
        managed_valuator,
    ],
)

if __name__ == "__main__":
    response = manager.run(MANAGER_PROMPT)
