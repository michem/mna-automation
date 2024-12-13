# mna_automation/agents/strategy_agent.py

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from autogen import ConversableAgent

from config.settings import BASE_CONFIG, OUTPUT_DIR

STRATEGY_PROMPT = """You are an expert M&A Strategy Advisor with extensive experience in helping companies develop acquisition strategies. Your role is to:

1. Guide users through a strategic discussion about their M&A objectives
2. Ask relevant questions to understand their needs
3. Analyze responses holistically to avoid redundant questions
4. Develop a comprehensive acquisition strategy

Follow these guidelines:
- Maintain a natural, conversational flow
- Ask one question at a time
- Analyze user responses for implicit information
- Adapt questions based on previous responses
- Focus on strategic objectives, market positioning, and value creation
- Be thorough but efficient in information gathering

Key areas to explore:
- Strategic objectives (market expansion, technology acquisition, talent acquisition)
- Buyer type (financial vs. strategic)
- Acquisition type (horizontal vs. vertical)
- Success criteria and metrics
- Industry-specific considerations
- Risk factors and mitigation strategies

Remember to:
- Acknowledge user responses
- Show understanding of industry context
- Provide strategic insights
- Maintain professional tone
- Guide towards actionable strategy development

When the strategy is complete:
1. Output it in markdown format enclosed in triple backticks as ```markdown ... ```
2. Present it for user review
3. Accept feedback and refine if needed

Return 'TERMINATE' only when the strategy is approved.
"""


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

    def _save_strategy(self, strategy_text: str) -> str:
        strategy_path = Path(OUTPUT_DIR) / "strategy.md"
        with open(strategy_path, "w") as f:
            f.write(strategy_text)
        return str(strategy_path)

    def _format_strategy(self) -> str:
        return f"""# M&A Acquisition Strategy

                ## Strategic Objectives
                {self.strategy.get('objectives', 'Not specified')}

                ## Buyer Profile
                - Type: {self.strategy.get('buyer_type', 'Not specified')}
                - Acquisition Approach: {self.strategy.get('acquisition_type', 'Not specified')}

                ## Target Criteria
                {self.strategy.get('target_criteria', 'Not specified')}

                ## Success Metrics
                {self.strategy.get('success_metrics', 'Not specified')}

                ## Risk Analysis & Mitigation
                {self.strategy.get('risk_analysis', 'Not specified')}

                ## Timeline & Next Steps
                {self.strategy.get('next_steps', 'Not specified')}"""

    def update_strategy(self, key: str, value: str):
        self.strategy[key] = value

    def get_human_input(self, prompt: str) -> str:
        if "approve" in prompt.lower() and "strategy" in prompt.lower():
            response = super().get_human_input(prompt)
            self.strategy_approved = response.lower() in [
                "yes",
                "y",
                "approved",
                "approve",
            ]
            if self.strategy_approved:
                strategy_text = self._format_strategy()
                self._save_strategy(strategy_text)
                return f"Strategy approved and saved.\n\n```markdown\n{strategy_text}\n```\nTERMINATE"
            return response
        return super().get_human_input(prompt)
