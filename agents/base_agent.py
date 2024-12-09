# mna_automation/agents/base_agent.py

from abc import ABC, abstractmethod
from typing import Any, Dict

import autogen

from config import get_agent_config
from utils import get_logger


class BaseAgent(ABC):
    """Base class for all M&A agents"""

    def __init__(self, name: str, system_message: str):
        self.name = name
        self.system_message = system_message
        self.logger = get_logger(f"agent.{name}")
        self.agent = self._create_agent()

    def _create_agent(self) -> autogen.AssistantAgent:
        """Create an AutoGen assistant agent"""
        self.logger.debug(f"Creating agent: {self.name}")

        config = get_agent_config(self.name.lower())

        agent = autogen.AssistantAgent(
            name=self.name, system_message=self.system_message, llm_config=config
        )

        self.logger.info(f"Agent {self.name} created successfully")
        return agent

    @abstractmethod
    def run(self, *args, **kwargs):
        """Run the agent's main workflow"""
        pass

    def log_error(self, error: Exception, context: str = None):
        """Log an error with context"""
        message = f"Error in {self.name}"
        if context:
            message += f" during {context}"
        self.logger.error(f"{message}: {str(error)}", exc_info=True)
