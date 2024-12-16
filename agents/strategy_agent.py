# mna_automation/agents/strategy_agent.py

import os
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Union

from autogen import Agent, ConversableAgent

from config.settings import BASE_CONFIG, OUTPUT_DIR

STRATEGY_PROMPT = """You are a project manager for a Merger and Aquisitions consultancy firm. You are polite and well manered.

Your goal is to prepare aquistion strategy for the client. Get all the information from client. Don't assume anything.

Don't ask all the information at once. Ask one by one and keep the conversational flow smooth.

1. Define Strategic Objectives:
o Identify whether the goal is market expansion, technology acquisition, talent
acquisition, cost synergies, or another objective.
o Determine if the buyer is a financial or strategic buyer.
o For strategic buyers, determine whether the acquisition is horizontal or
vertical:
▪ Horizontal Acquisition: Acquiring a company that operates in the
same industry and at the same stage of the supply chain.
▪ Vertical Acquisition: Acquiring a company that operates at a different
stage of the supply chain (either upstream or downstream).

2. Prioritize Objectives:
o Rank the objectives based on the user's business priorities.
3. Establish Measurable Criteria for Success:
o Set clear metrics to gauge the success of the acquisition strategy.

Once you have all the information from client, you are to provide the strategy to the client.

When the strategy is complete:
1. Output the strategy in well-formatted markdown
2. Present it for user review
3. When the strategy is approved:
   - Use the save_file tool to save ONLY the strategy content to outputs/strategy.md
   - Ensure no conversational text or TERMINATE message is included in the saved content
4. After successfully saving, return 'TERMINATE'

Return 'TERMINATE' only when the strategy is approved and has been successfully saved using the save_file tool."""


def save_file(
    content: Annotated[
        str,
        "The acquisition strategy content in markdown format, without any conversational elements",
    ],
    filepath: Annotated[
        str,
        "Path where to save the strategy markdown file, should be outputs/strategy.md",
    ],
) -> str:
    """Save the acquisition strategy to a markdown file. Only the strategy content should be saved,
    without any conversational elements or termination messages."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully saved strategy to {filepath}"
    except Exception as e:
        return f"Error saving file: {str(e)}"


class StrategyAgent(ConversableAgent):
    def __init__(
        self,
        name: str = "Strategy_Advisor",
        system_message: Optional[str] = STRATEGY_PROMPT,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="TERMINATE",
        )
        self.strategy = {}
        self.strategy_approved = False

        self.register_for_execution(
            name="save_file",
        )(save_file)

        self.register_for_llm(
            name="save_file",
            description=(
                "Save the final acquisition strategy to outputs/strategy.md. "
                "This should be called only when the strategy is approved. "
                "Save only the strategy content in markdown format, without any conversation or TERMINATE messages."
            ),
        )(save_file)

    def update_strategy(self, key: str, value: str):
        self.strategy[key] = value

    def get_human_input(self, prompt: str) -> str:
        if "approve" in prompt.lower() and "strategy" in prompt.lower():
            response = super().get_human_input(prompt)
            return response
        return super().get_human_input(prompt)
