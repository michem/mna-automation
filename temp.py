import os

from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

opneai_model_client = OpenAIChatCompletionClient(
    model="gemini-1.5-flash",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=GEMINI_API_KEY,
    model_capabilities={
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
)


async def test():
    result = await opneai_model_client.create(
        [UserMessage(content="What is the capital of France?", source="user")]
    )

    print(result)


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
