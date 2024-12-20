# mna_automation/agents/collection_agent.py

import json
import os
from pathlib import Path
from typing import Annotated, Dict, Optional, Union

import requests
from autogen import ConversableAgent
from dotenv import load_dotenv

from config.settings import BASE_CONFIG

load_dotenv()

FMP_API_KEY = os.getenv("FMP_API_KEY")

COLLECTION_PROMPT = """You are a financial data collection agent.
Your only task is to fetch financial data for companies and save it as JSON files.

Process:
1. For each company mentioned in the input:
   - Extract the stock symbol
   - Use fetch_company_data to get and save financial data as JSON
   - Wait for confirmation that the data was saved
   
2. After ALL companies have been processed, respond with exactly 'TERMINATE'

Do not perform any analysis. Focus only on data collection.
Do not continue conversation after receiving save confirmations."""


def fetch_company_data(symbol: Annotated[str, "Stock symbol of the company"]) -> str:
    """Fetch and save financial data for a company"""
    base_url = "https://financialmodelingprep.com/api/v3"
    endpoints = {"financials": f"financials/income-statement/{symbol}"}

    data = {}
    for key, endpoint in endpoints.items():
        try:
            url = f"{base_url}/{endpoint}?apikey={FMP_API_KEY}"
            response = requests.get(url)
            response.raise_for_status()
            data[key] = response.json()
        except Exception as e:
            return f"Error fetching {key} for {symbol}: {str(e)}"

    output_dir = Path("outputs/json")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_dir / f"{symbol}_fmp.json", "w") as f:
            json.dump(data, f, indent=2)
        return f"Successfully fetched and saved data for {symbol}"
    except Exception as e:
        return f"Error saving data for {symbol}: {str(e)}"


class CollectionAgent(ConversableAgent):
    def __init__(
        self,
        name: str = "data_collector",
        system_message: Optional[str] = COLLECTION_PROMPT,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=2,
        )

        self.register_for_execution(name="fetch_company_data")(fetch_company_data)
        self.register_for_llm(
            name="fetch_company_data", description=fetch_company_data.__doc__
        )(fetch_company_data)
