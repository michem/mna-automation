# mna_automation/agents/strategy_agent/agent.py

from typing import Any, Dict, List, Optional

import autogen
from colorama import Fore, Style

from agents.base_agent import BaseAgent
from config.settings import GEMINI_CONFIG
from models.strategy import StrategyModel


class CustomUserProxy(autogen.UserProxyAgent):
    def get_human_input(self, prompt: Optional[str] = None) -> str:
        """Override to customize the input prompt"""
        print(Fore.GREEN + "You:" + Style.RESET_ALL, end=" ")
        return input()


class StrategyAgent(BaseAgent):
    """Agent for developing M&A acquisition strategy"""

    def __init__(self):
        system_message = """
        You are an expert M&A Strategy Agent. Your role is to:
        1. Understand acquisition objectives through conversation
        2. Identify whether goals are market expansion, technology acquisition, talent acquisition, etc.
        3. Determine if the buyer is financial or strategic
        4. For strategic buyers, determine if the acquisition is horizontal or vertical
        5. Prioritize objectives based on business priorities
        6. Establish measurable criteria for success
        
        Important guidelines:
        - Be conversational and natural in your questioning
        - Avoid asking redundant questions
        - Analyze user responses comprehensively
        - Only ask for information that hasn't been provided
        - Structure your questions logically and progressively
        """
        super().__init__("Strategy_Agent", system_message)
        self.human_proxy = self._create_human_proxy()
        self.strategy = StrategyModel()
        self.logger.info("Strategy Agent initialized with empty strategy model")

    def _get_config_list(self) -> list:
        return GEMINI_CONFIG

    def _create_human_proxy(self) -> autogen.UserProxyAgent:
        """Create a human proxy agent for interactive conversation"""
        return CustomUserProxy(
            name="human_proxy",
            system_message="Interact with the Strategy Agent to develop an M&A strategy.",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=0,
            code_execution_config=False,
        )

    def analyze_response(self, response: str) -> Dict:
        """Analyze user response for relevant information"""
        analysis_prompt = f"""
        Analyze the following response for M&A strategy information:
        {response}
        
        Extract information about:
        1. Primary and secondary goals
        2. Target industry/market
        3. Desired technologies/talents
        4. Cost synergy preferences
        5. Acquisition type (horizontal/vertical)
        6. Any other relevant strategic information
        
        Return only the extracted information in a clear format.
        """

        return self.agent.generate_response(analysis_prompt)

    def formulate_strategy(self, collected_info: Dict) -> StrategyModel:
        """Formulate acquisition strategy based on collected information"""
        strategy_prompt = f"""
        Based on the collected information:
        {collected_info}
        
        Create a comprehensive M&A strategy that includes:
        1. Strategic objectives (prioritized)
        2. Target criteria
        3. Success metrics
        4. Risk considerations
        5. Implementation timeline
        6. Next steps for other agents
        
        Provide the strategy in a structured format.
        """

        strategy_response = self.agent.generate_response(strategy_prompt)
        return StrategyModel.model_validate(strategy_response)

    def _format_question(self, question: str) -> str:
        """Format a question for display"""
        return f"\n{Fore.CYAN}💡 {question}{Style.RESET_ALL}\n"

    def run(self) -> StrategyModel:
        """Execute the strategy development workflow"""
        self.logger.info("Starting strategy development conversation")

        initial_question = """
        Hello! I'm here to help develop your M&A acquisition strategy. 
        Let's start with understanding your primary goal for this acquisition. 
        What are you looking to achieve?
        """.strip()

        self.agent.initiate_chat(
            self.human_proxy, message=self._format_question(initial_question)
        )

        collected_info = {}

        try:
            while not self._is_information_complete(collected_info):
                response = self.human_proxy.get_human_input()

                print(f"\n{Fore.BLUE}Processing your response...{Style.RESET_ALL}")
                new_info = self.analyze_response(response)
                collected_info.update(new_info)

                if not self._is_information_complete(collected_info):
                    next_question = self._generate_next_question(collected_info)
                    if next_question:
                        self.agent.send_message(self._format_question(next_question))

            if self._is_information_complete(collected_info):
                strategy = self.formulate_strategy(collected_info)
                self._present_strategy_for_approval(strategy)
                return strategy
            else:
                self.logger.warning("Strategy development incomplete due to early exit")
                return None

        except KeyboardInterrupt:
            self.logger.info("Strategy development interrupted by user")
            raise
        except Exception as e:
            self.logger.error(
                f"Error during strategy development: {str(e)}", exc_info=True
            )
            raise

    def _is_information_complete(self, info: Dict) -> bool:
        """Enhanced check for information completeness"""
        required_fields = [
            "primary_goal",
            "buyer_type",
            "acquisition_type",
            "target_criteria",
            "success_metrics",
        ]

        if not all(field in info for field in required_fields):
            return False

        if "target_criteria" in info:
            criteria = info["target_criteria"]
            if not (criteria.get("industry") and criteria.get("revenue_range")):
                return False

        if "success_metrics" in info:
            metrics = info["success_metrics"]
            if not (metrics.get("financial") or metrics.get("operational")):
                return False

        return True

    def _update_strategy_based_on_feedback(
        self, strategy: StrategyModel, feedback: str
    ):
        """Update strategy based on user feedback"""
        feedback_prompt = f"""
        Update the strategy based on this feedback:
        {feedback}
        
        Current strategy:
        {strategy.formatted_output()}
        
        Provide specific updates to make while maintaining the strategy's structure.
        """

        updates = self.agent.generate_response(feedback_prompt)
        for key, value in updates.items():
            setattr(strategy, key, value)

    def _generate_next_question(self, collected_info: Dict) -> str:
        """Generate the next relevant question based on missing information"""
        question_prompt = f"""
        Based on the collected information:
        {collected_info}
        
        Generate the next most relevant question to gather missing M&A strategy information.
        Focus on what's missing from:
        1. Strategic objectives
        2. Buyer type (financial/strategic)
        3. Acquisition type (horizontal/vertical)
        4. Target criteria
        5. Success metrics
        
        Return only the question in a conversational tone.
        """

        return self.agent.generate_response(question_prompt)

    def _prepare_agent_handoff(self, strategy: StrategyModel) -> Dict[str, Any]:
        """Prepare data for subsequent agents"""
        return {
            "web_search": {
                "criteria": strategy.web_search_criteria.model_dump(),
                "priorities": strategy.target_criteria.model_dump(),
            },
            "data_collection": {
                "requirements": strategy.data_requirements.model_dump(),
                "metrics": strategy.success_metrics.model_dump(),
            },
            "valuation": {
                "parameters": strategy.valuation_parameters.model_dump(),
                "risk_factors": strategy.risk_considerations,
            },
        }

    def _present_strategy_for_approval(self, strategy: StrategyModel):
        """Enhanced strategy presentation with termination handling"""
        approval_message = f"""
        {Fore.CYAN}=== Proposed Acquisition Strategy ==={Style.RESET_ALL}
        
        {strategy.formatted_output()}
        
        {Fore.YELLOW}Please review and let me know if you'd like any adjustments.
        Type 'approve' to accept or provide specific feedback for modifications.{Style.RESET_ALL}
        """

        self.agent.send_message(approval_message)
        while True:
            response = self.human_proxy.get_response()
            if response.lower() == "approve":
                print(
                    f"\n{Fore.GREEN}✓ Strategy approved! Preparing for next steps...{Style.RESET_ALL}"
                )
                handoff_data = self._prepare_agent_handoff(strategy)
                self.logger.info("Strategy approved, preparing for agent handoff")

                self.agent.send_message(
                    """
                Strategy has been approved. Initiating handoff to subsequent agents.
                
                `TERMINATE`
                """
                )
                break

            self._update_strategy_based_on_feedback(strategy, response)
