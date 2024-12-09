# mna_automation/config/settings.py

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_CONFIG = [
    {
        "model": "gemini-1.5-flash",
        "api_key": GEMINI_API_KEY,
        "api_type": "google",
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 2048,
    },
    {
        "model": "gemini-1.5-pro",
        "api_key": GEMINI_API_KEY,
        "api_type": "google",
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 2048,
    },
]

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "mna_automation.log"

STRATEGY_AGENT_CONFIG = {
    "temperature": 0.7,
    "max_tokens": 2000,
    "required_fields": [
        "primary_goal",
        "buyer_type",
        "acquisition_type",
        "target_criteria",
        "success_metrics",
    ],
}


def get_agent_config(agent_name: str) -> dict:
    """Get agent-specific configuration"""
    base_config = {
        "config_list": GEMINI_CONFIG,
        "temperature": 0.7,
        "request_timeout": 120,
        "seed": 42,
    }

    if agent_name == "strategy":
        base_config.update(STRATEGY_AGENT_CONFIG)

    return base_config
