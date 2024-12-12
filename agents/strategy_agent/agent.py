# mna_automation/agents/strategy_agent/agent.py

from pathlib import Path
from typing import Dict, Optional

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
        You are an expert M&A Strategy Agent. Your role is to develop comprehensive acquisition strategies through natural conversation.
        
        Guidelines:
        - Keep the conversation flowing naturally
        - Infer information from context when possible
        - Ask follow-up questions only when crucial information is missing
        - Focus on understanding the core strategy rather than excessive details
        - Generate the strategy document when you have sufficient understanding
        
        Remember to maintain a friendly yet professional tone throughout the conversation.
        """
        super().__init__("Strategy_Agent", system_message)
        self.human_proxy = self._create_human_proxy()
        self.strategy = StrategyModel()
        self.logger.info("Strategy Agent initialized")

    def _create_human_proxy(self) -> autogen.UserProxyAgent:
        """Create a human proxy agent for interactive conversation"""
        return CustomUserProxy(
            name="human_proxy",
            system_message="Engage with the Strategy Agent to develop an M&A strategy.",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=0,
            code_execution_config=False,
        )

    def analyze_response(self, response: str) -> Dict:
        """Analyze user response for relevant information"""
        analysis_prompt = f"""
        Analyze this response for M&A strategy information:
        {response}
        
        Extract key strategic information about:
        - Goals and objectives
        - Target preferences
        - Success criteria
        - Risk factors
        - Timeline considerations
        
        Return only the relevant extracted information.
        """
        return self.agent.generate_reply(analysis_prompt)

    def _has_sufficient_information(self) -> bool:
        """Check if we have enough information to generate a strategy"""
        return bool(
            self.strategy.primary_goal
            and (
                self.strategy.target_criteria.industry
                or self.strategy.target_criteria.key_requirements
            )
        )

    def _format_question(self, question: str) -> str:
        """Format a question for display"""
        return f"\n{Fore.CYAN}💡 {question}{Style.RESET_ALL}\n"

    def run(self) -> Optional[StrategyModel]:
        """Execute the strategy development workflow"""
        self.logger.info("Starting strategy development conversation")

        initial_question = """
        Hello! I'm here to help develop your M&A acquisition strategy. 
        Could you tell me about your organization and what you're looking to achieve with this acquisition?
        """.strip()

        self.agent.initiate_chat(
            self.human_proxy, message=self._format_question(initial_question)
        )

        try:
            while not self._has_sufficient_information():
                response = self.human_proxy.get_human_input()
                if response.lower() in ["exit", "quit"]:
                    return None

                print(f"\n{Fore.BLUE}Processing your response...{Style.RESET_ALL}")
                new_info = self.analyze_response(response)
                self._update_strategy(new_info)

                if not self._has_sufficient_information():
                    next_question = self._generate_next_question()
                    if next_question:
                        self.agent.send_message(self._format_question(next_question))

            # Generate and save strategy
            self._finalize_strategy()
            self.strategy.save_to_file()

            print(
                f"\n{Fore.GREEN}✓ Strategy document has been generated and saved to output/strategy.md{Style.RESET_ALL}"
            )
            return self.strategy

        except KeyboardInterrupt:
            self.logger.info("Strategy development interrupted by user")
            raise
        except Exception as e:
            self.logger.error(
                f"Error during strategy development: {str(e)}", exc_info=True
            )
            raise

    def _update_strategy(self, new_info: Dict):
        """Update strategy model with new information"""
        for key, value in new_info.items():
            if hasattr(self.strategy, key):
                setattr(self.strategy, key, value)
            elif hasattr(self.strategy.target_criteria, key):
                setattr(self.strategy.target_criteria, key, value)
            elif hasattr(self.strategy.success_metrics, key):
                setattr(self.strategy.success_metrics, key, value)

    def _generate_next_question(self) -> str:
        """Generate the next relevant question based on current strategy state"""
        strategy_state = self.strategy.model_dump()

        question_prompt = f"""
        Based on the current strategy state:
        {strategy_state}
        
        Generate a natural follow-up question to gather missing crucial information.
        Focus on the most important missing element.
        Make the question conversational and context-aware.
        
        Return only the question text.
        """

        return self.agent.generate_reply(question_prompt)

    def _finalize_strategy(self):
        """Generate final strategy details"""
        finalization_prompt = f"""
        Based on the collected information:
        {self.strategy.model_dump()}
        
        Generate a complete M&A strategy by:
        1. Inferring any missing but logical details
        2. Adding relevant risk considerations
        3. Creating a basic implementation timeline
        4. Defining clear success metrics
        
        Return the complete strategy details in a structured format.
        """

        final_details = self.agent.generate_reply(finalization_prompt)
        self._update_strategy(final_details)
