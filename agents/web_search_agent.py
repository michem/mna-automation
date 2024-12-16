# mna_automation/agents/web_search_agent.py

import os
from typing import Dict, Optional, Union

from autogen import ConversableAgent
from autogen.agentchat.contrib.web_surfer import (
    BingMarkdownSearch,
    RequestsMarkdownBrowser,
    WebSurferAgent,
)

from config.settings import BASE_CONFIG

researcher_prompt = """You are a researcher at a well-reputed Merger and Acquisitions consultancy firm.

You will chat with the WebSurferAgent and generate a nicely formatted table of 5 publically listed companies with their stock symbols.

You will have to give instructions to the WebSurfer Agent step by step.
After each instruction, WebSurfer Agent will provide you with the information.
Analyse that information and give the next instruction to the WebSurfer Agent.

A sample interaction with the WebSurferAgent looks like this:

You: Search latest articles in AI
WebSurfer Agent: <returns result of a bing search "latest articles in ai">
You: Open the first link and summarize the article
WebSurfer Agent: <returns the summary of the article>
...
"""


class WebSearchAgent:
    def __init__(
        self,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
        bing_api_key: Optional[str] = os.getenv("BING_API_KEY"),
    ):
        self.researcher = ConversableAgent(
            name="researcher",
            system_message=researcher_prompt,
            llm_config=llm_config,
            code_execution_config=False,
            human_input_mode="NEVER",
        )

        search_engine = BingMarkdownSearch(bing_api_key=bing_api_key)
        self.web_surfer = WebSurferAgent(
            name="web_surfer",
            llm_config=llm_config,
            summarizer_llm_config=llm_config,
            browser=RequestsMarkdownBrowser(
                viewport_size=4096, search_engine=search_engine
            ),
        )

    def initiate_web_search(self, strategy_report: str):
        result = self.researcher.initiate_chat(
            self.web_surfer,
            message=f"Based on the following acquisition strategy, find 5 publicly listed companies with their stock symbols:\n\n{strategy_report}",
            silent=True,
        )
        return result
