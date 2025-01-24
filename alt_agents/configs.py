import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


OAI_CONFIG = {
    "config_list": [
        {
            "model": os.environ["oai_model"],
            "api_key": os.environ["openai_api_key"],
        }
    ],
    "timeout": 120,
    "temperature": 0.0,
    "cache_seed": None,
}

SUMMARISER_CONFIG = {
    "config_list": [
        {
            "model": os.environ["oai_model"],
            "api_key": os.environ["openai_api_key"],
        }
    ],
    "timeout": 600,
    "temperature": 0,
    "cache_seed": None,
}

GEMINI_CONFIG = {
    "config_list": [
        {
            "model": os.environ["gemini_model"],
            "api_key": os.environ["gemini_api_key"],
            "api_type": "google",
        }
    ],
    "timeout": 120,
    "temperature": 0.1,
    "cache_seed": None,
}

OUTPUT_DIR = "outputs"
STRATEGY_REPORT_PATH = Path("outputs/output.md")
COMPANIES_JSON_PATH = Path("outputs/companies.json")
CRITIC_COMPANIES_JSON_PATH = Path("outputs/critic_companies.json")
DATA_COLLECTION_PATH = Path("outputs/fmp_data")
