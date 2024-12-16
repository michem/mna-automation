# mna_automation/config/settings.py

import os
from typing import Any, Dict, List

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")

GEMINI_CONFIG = [
    {
        "model": "gemini-1.5-pro",
        "api_key": GEMINI_API_KEY,
        "api_type": "google",
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 8192,
    },
]

BASE_CONFIG = {
    "config_list": GEMINI_CONFIG,
    "temperature": 0.7,
    "request_timeout": 120,
    "seed": 42,
}

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
