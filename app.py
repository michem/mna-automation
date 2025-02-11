import streamlit as st
from smolagents import CodeAgent, LiteLLMModel, ToolCallingAgent

from agent1 import managed_strategist
from agent2 import managed_critic, managed_researcher
from agent3n4 import managed_analyst
from agent5 import managed_valuator
from config import MODEL_API_KEY, MODEL_ID
from prompts import RESEARCHER_PROMPTlke
from run import MANAGER_PROMPT, manager
from tools import (
    get_companies,
    get_options,
    read_from_json,
    read_from_markdown,
    save_to_json,
)

model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)

agent = ToolCallingAgent(
    tools=[],
    model=model,
    managed_agents=[managed_strategist],
)

st.title("CodeAgent Demo with Streamlit")

if st.button("Run Agent"):
    st.write("Running the agent...")
    result = agent.run(MANAGER_PROMPT, stream=True)
    for step in result:
        st.write(step.action_output if step.action_output else "No output")
        if step.observations:
            st.write("Observations:")
            st.write(step.observations)
