# mna_automation/config/settings.py

import os
from typing import Any, Dict, List

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GEMINI_CONFIG = [
    {
        "model": "gemini-2.0-flash-exp",
        "api_key": GEMINI_API_KEY,
        "api_type": "google",
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 8192,
    },
]

OPENAI_CONFIG = [
    {
        "model": "gpt-4o",
        "api_key": OPENAI_API_KEY,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 4096,
        "api_rate_limit": 60.0,
    },
]

BASE_CONFIG = {
    "config_list": OPENAI_CONFIG,
    "temperature": 0.7,
    "timeout": 60,
    "seed": 42,
}

BASE_GEMINI = {
    "config_list": GEMINI_CONFIG,
    "temperature": 0.7,
    "timeout": 60,
    "seed": 42,
}

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
