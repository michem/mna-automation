import os
from pathlib import Path

MODEL_PROVIDER = "openai"

if MODEL_PROVIDER == "openai":
    MODEL_ID = "openai/gpt-4o-mini"
    MODEL_API_KEY = os.getenv("OPENAI_API_KEY")
elif MODEL_PROVIDER == "gemini":
    MODEL_ID = "gemini/gemini-2.0-flash-exp"
    MODEL_API_KEY = os.getenv("GEMINI_API_KEY")
else:
    raise ValueError("Unsupported MODEL_PROVIDER. Choose 'openai' or 'gemini'.")

OUTPUT_DIR = "outputs"
STRATEGY_REPORT_PATH = Path("outputs/output.md")
VALUATION_REPORT_PATH = Path("outputs/valuation.md")
COMPANIES_JSON_PATH = Path("outputs/companies.json")
CRITIC_COMPANIES_JSON_PATH = Path("outputs/critic_companies.json")
DATA_COLLECTION_PATH = Path("outputs/fmp_data/valuation")
