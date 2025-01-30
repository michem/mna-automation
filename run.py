from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel, ToolCallingAgent

from agent1 import managed_strategist
from agent2 import managed_critic, managed_researcher
from agent3n4 import managed_analyst
from agent5 import managed_valuator
from config import (
    COMPANIES_JSON_PATH,
    CRITIC_COMPANIES_JSON_PATH,
    DATA_COLLECTION_PATH,
    MODEL_API_KEY,
    MODEL_ID,
    STRATEGY_REPORT_PATH,
    VALUATION_REPORT_PATH,
)

load_dotenv()


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
    max_steps=0,
)

MANAGER_PROMPT = f"""You are the managing director of a Merger and Acquisitions consultancy firm, responsible for overseeing the entire M&A process and coordinating a team of specialized professionals.

Your team consists of:
1. 'strategist' - Chief strategist | Develops acquisition strategies
2. 'researcher' - Market researcher | Identifies potential target companies
3. 'critic' - Due diligence critic | Filters and evaluates potential targets
4. 'analyst' - Financial analyst | Performs financial analysis and valuation
5. 'valuator' - Valuation expert | Synthesizes analyses and provides final recommendations

Your role is to:
1. Begin by delegating the initial client consultation to the 'strategist' to:
   - Gather client requirements
   - Develop acquisition strategy
   - Create strategy report

2. Once the strategy is established, assign the 'researcher' to:
   - Analyze the strategy report
   - Identify matching companies
   - Generate initial target list

3. Forward the company list to the 'critic' to:
   - Review potential targets
   - Filter based on strategy alignment
   - Create refined target list

4. Direct the 'analyst' to:
   - Collect financial data for filtered targets
   - Perform detailed financial analysis
   - Generate company-specific valuations

5. Finally, task 'valuator' to:
   - Review all analyses
   - Create comprehensive comparison
   - Provide final recommendations

The process follows this sequential flow:
1. 'strategist' -> strategy report -> {STRATEGY_REPORT_PATH}
2. 'researcher' -> companies list -> {COMPANIES_JSON_PATH}
3. 'critic' -> filtered companies list -> {CRITIC_COMPANIES_JSON_PATH}
4. 'analyst' -> financial analysis -> {DATA_COLLECTION_PATH}
5. 'valuator' -> final valuation -> {VALUATION_REPORT_PATH}
6. End the chat

Ensure each step is completed successfully before proceeding to the next stage. If any step fails or produces incomplete results, assess the situation and either request clarification or proceed with available data while noting the limitations.

Once {VALUATION_REPORT_PATH} has been saved, end the chat
"""

response = manager.provide_final_answer(MANAGER_PROMPT)
