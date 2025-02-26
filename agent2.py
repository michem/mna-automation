from os import name

from dotenv import load_dotenv
from smolagents import CodeAgent, LiteLLMModel, ToolCallingAgent

from config import MODEL_API_KEY, MODEL_ID
from prompts import CRITIC_PROMPT, RESEARCHER_PROMPT
from tools import (
    get_companies,
    get_names_and_summaries,
    get_options,
    read_from_json,
    read_from_markdown,
    save_to_json,
)

load_dotenv()


model_r = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)
model_c = LiteLLMModel(
    model_id=MODEL_ID,
    api_key=MODEL_API_KEY,
    temperature=0.0,
)
researcher = CodeAgent(
    name="researcher",
    tools=[
        get_companies,
        read_from_json,
        read_from_markdown,
        get_options,
        save_to_json,
    ],
    additional_authorized_imports=["json", "os"],
    model=model_r,
    max_steps=50,
    description="A flexible and persistent researcher agent that finds companies matching the target profile from the strategy report. It tries multiple search parameters when needed, adapts to available options, and always ensures viable companies are identified and saved, even with imperfect strategy data.",
)
critic = ToolCallingAgent(
    name="critic",
    tools=[get_names_and_summaries, read_from_json, save_to_json, read_from_markdown],
    model=model_c,
    max_steps=50,
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
