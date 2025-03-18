from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel, ManagedAgent, ToolCallingAgent

from config import MODEL_API_KEY, MODEL_ID
from prompts import CRITIC_PROMPT, RESEARCHER_PROMPT
from tools import (
    get_companies,
    get_names_and_summaries,
    get_options,
    read_from_json,
    read_from_markdown,
    save_to_json,
    shortlist_companies,
)

load_dotenv()


model = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)
researcher = CodeAgent(
    tools=[shortlist_companies, read_from_markdown, save_to_json],
    additional_authorized_imports=["json", "os"],
    model=model,
    max_steps=15,
)
managed_researcher = ManagedAgent(
    agent=researcher,
    name="researcher",
    description="A flexible and persistent researcher agent that finds companies matching the target profile from the strategy report. It tries multiple search parameters when needed, adapts to available options, and always ensures viable companies are identified and saved, even with imperfect strategy data.",
)

critic = ToolCallingAgent(
    tools=[get_names_and_summaries, read_from_json, save_to_json, read_from_markdown],
    model=model,
    max_steps=10,
)
managed_critic = ManagedAgent(
    agent=critic,
    name="critic",
    description="A diligent critic agent that analyzes company profiles against strategy requirements, ranks matches systematically, and ensures at least some viable options are identified and saved. It handles incomplete data gracefully and provides clear reasoning for company selection.",
)

if __name__ == "__main__":
    res_response = researcher.run(
        RESEARCHER_PROMPT,
        reset=False,
    )
    crt_response = critic.run(
        CRITIC_PROMPT,
        reset=False,
    )
