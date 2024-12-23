# mna_automation/agents/collection_agent.py

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import requests
from autogen import ConversableAgent, UserProxyAgent

from config.settings import BASE_CONFIG, OUTPUT_DIR

COLLECTOR_PROMPT = """You are a Data Collection Agent for M&A analysis. Your role is to extract stock symbols from strategy documents and company lists, then request collection of comprehensive financial data for analysis.

WORKFLOW:
1. Read and parse the provided content
2. Extract stock symbols for both acquirer and target companies
3. For each symbol, request data collection using collect_and_save_fmp_data tool
4. Track completion status for each symbol
5. After all symbols are processed, reply 'TERMINATE'

RULES:
- Extract symbols carefully from markdown content, especially from tables
- Process both acquirer and target companies
- Request collection for each symbol individually
- Monitor collection status
- Ensure all companies are processed before terminating

Example workflow:
1. From content: "Company: Apple Inc (AAPL)"
2. Extract symbol: "AAPL"
3. Request collection for "AAPL"
4. Wait for confirmation
5. Continue with next symbol
6. After all symbols complete, terminate"""


def collect_and_save_fmp_data(symbol: str) -> str:
    """Collect FMP data and save it, returning only a status message"""
    api_key = os.getenv("FMP_API_KEY", "vcS4GLjpRr6YPgpYrwzM6BwZJHAcl3M0")
    base_url = "https://financialmodelingprep.com/api/v3"

    endpoints = {
        "financials": f"/financials/income-statement/{symbol}",
        "balance_sheet": f"/financials/balance-sheet-statement/{symbol}",
        "cash_flow": f"/financials/cash-flow-statement/{symbol}",
        "ratios": f"/key-ratios/{symbol}",
        "quote": f"/quote/{symbol}",
        "sector_performance": "/sector-performance",
        "macro_data": "/economic-indicator",
    }

    data = {}
    try:
        for key, endpoint in endpoints.items():
            url = f"{base_url}{endpoint}?apikey={api_key}"
            response = requests.get(url)
            response.raise_for_status()
            data[key] = response.json()

        base_path = str(Path(OUTPUT_DIR) / "json")
        os.makedirs(base_path, exist_ok=True)
        filepath = Path(base_path) / f"{symbol}_fmp.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return f"Successfully collected and saved FMP data for {symbol}"
    except Exception as e:
        return f"Error processing {symbol}: {str(e)}"


class DataCollectorAgent(ConversableAgent):
    """Agent for analyzing content and requesting data collection"""

    def __init__(
        self,
        name: str = "Data_Collector",
        system_message: str = COLLECTOR_PROMPT,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="TERMINATE",
        )

        self.register_for_llm(
            name="collect_and_save_fmp_data",
            description="Request collection of financial data for a stock symbol",
        )(collect_and_save_fmp_data)


class ExecutorAgent(UserProxyAgent):
    """Agent for executing data collection requests"""

    def __init__(self, name: str = "Executor"):
        super().__init__(
            name=name,
            human_input_mode="NEVER",
            code_execution_config=False,
        )

        self.register_for_execution(name="collect_and_save_fmp_data")(
            collect_and_save_fmp_data
        )
