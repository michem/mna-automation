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
    temperature=0.2,
)
researcher = CodeAgent(
    name="researcher",
    tools=[get_companies, read_from_markdown, get_options, save_to_json],
    additional_authorized_imports=["json", "os"],
    model=model_r,
    max_steps=15,
    description="A researcher agent that finds companies that match the target profile of the strategy report by calling the 'get_options' tool for valid arguments to pass to 'get_companies' tool, folowed by 'save_to_json' tool to save the results to a JSON file.",
)
critic = ToolCallingAgent(
    name="critic",
    tools=[get_names_and_summaries, read_from_json, save_to_json, read_from_markdown],
    model=model_c,
    max_steps=10,
    description="A critic agent that analyzes the JSON file containing companies and filters them based on the strategy report requirements, saving the results to a new JSON file in a similar format as the input file.",
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
