# mna_automation/agents/valuation_agent.py

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from autogen import ConversableAgent

from config.settings import BASE_CONFIG, OUTPUT_DIR

ANALYZER_PROMPT = """You are a Valuation Analysis Expert specializing in M&A transactions. Your role is to analyze target companies based on their financial data and the acquisition strategy.

WORKFLOW:
1. Review the provided strategy and target companies content
2. Extract stock symbols for analysis
3. For each target company:
   - Analyze financial statements
   - Perform DCF valuation
   - Conduct comparable company analysis
   - Assess potential synergies
   - Evaluate risks and strategic fit
4. Request comprehensive report generation for each analysis
5. After all analyses are complete, respond with 'TERMINATE'

Each analysis should focus on:
- Enterprise value calculation
- Market multiple comparison
- Synergy potential
- Strategic alignment with acquirer
- Risk assessment
- Deal structure recommendations

Example workflow:
1. Read strategy content: "Company: Microsoft (MSFT) seeks..."
2. Extract target symbols: ["BFLY", "TDOC", ...]
3. For each symbol:
   - Request financial analysis
   - Compare results with strategy goals
   - Request report generation
4. After all targets analyzed, terminate

Request report generation for each target before moving to the next one."""

REPORTER_PROMPT = """You are a Valuation Report Generator specializing in M&A analysis. Your role is to create comprehensive valuation reports based on financial analysis results.

Your reports should:
1. Clearly present valuation results
2. Highlight key metrics and comparisons
3. Discuss strategic fit and synergies
4. Provide deal structure recommendations
5. Include risk assessment
6. Make clear recommendations

Focus on:
- Clear presentation of numerical results
- Strategic implications
- Actionable recommendations
- Risk-reward assessment

Ensure all reports are saved using the provided save_report tool before analyzing the next target.
After completing all reports, respond with 'TERMINATE'."""


def calculate_dcf(
    financials: Dict, wacc: float = 0.12, growth_rate: float = 0.03
) -> Dict[str, float]:
    """Calculate DCF valuation using financial data"""
    try:

        fcf_data = [
            float(year["Free Cash Flow"])
            for year in financials.get("cash_flow", {}).get("financials", [])
            if year.get("Free Cash Flow")
        ]
        fcf_data.reverse()

        if not fcf_data:
            return {"error": "Insufficient cash flow data"}

        projection_years = 5
        base_fcf = fcf_data[0]
        projected_fcfs = []

        for year in range(1, projection_years + 1):
            projected_fcf = base_fcf * (1 + growth_rate) ** year
            projected_fcfs.append(projected_fcf)

        terminal_value = (projected_fcfs[-1] * (1 + growth_rate)) / (wacc - growth_rate)

        pv_fcfs = []
        for i, fcf in enumerate(projected_fcfs):
            pv = fcf / (1 + wacc) ** (i + 1)
            pv_fcfs.append(pv)

        pv_terminal = terminal_value / (1 + wacc) ** projection_years

        enterprise_value = sum(pv_fcfs) + pv_terminal

        return {
            "enterprise_value": enterprise_value,
            "present_value_fcf": sum(pv_fcfs),
            "present_value_terminal": pv_terminal,
            "projected_fcfs": projected_fcfs,
        }
    except Exception as e:
        return {"error": f"DCF calculation error: {str(e)}"}


def analyze_comparables(
    company_data: Dict, target_metrics: List[str]
) -> Dict[str, Any]:
    """Analyze company using market multiples"""
    try:
        metrics = {}
        financials = company_data.get("financials", {}).get("financials", [])
        quote = company_data.get("quote", [{}])[0]

        if not financials or not quote:
            return {"error": "Insufficient data for comparable analysis"}

        latest_financials = financials[0]
        market_cap = float(quote.get("marketCap", 0))

        metrics["EV/EBITDA"] = market_cap / float(latest_financials.get("EBITDA", 1))
        metrics["P/E"] = float(quote.get("pe", 0))
        metrics["EV/Revenue"] = market_cap / float(latest_financials.get("Revenue", 1))

        return metrics
    except Exception as e:
        return {"error": f"Comparable analysis error: {str(e)}"}


def assess_synergies(
    acquirer_data: Dict, target_data: Dict, strategy: str
) -> Dict[str, Any]:
    """Assess potential synergies between acquirer and target"""
    try:
        synergies = {
            "revenue_synergies": [],
            "cost_synergies": [],
            "strategic_benefits": [],
        }

        acquirer_revenue = float(
            acquirer_data.get("financials", {})
            .get("financials", [{}])[0]
            .get("Revenue", 0)
        )
        target_revenue = float(
            target_data.get("financials", {})
            .get("financials", [{}])[0]
            .get("Revenue", 0)
        )

        potential_revenue_synergy = (acquirer_revenue + target_revenue) * 0.05
        potential_cost_synergy = target_revenue * 0.03

        synergies["revenue_synergies"].append(
            {"type": "Cross-selling opportunities", "value": potential_revenue_synergy}
        )

        synergies["cost_synergies"].append(
            {"type": "Operational efficiency", "value": potential_cost_synergy}
        )

        return synergies
    except Exception as e:
        return {"error": f"Synergy assessment error: {str(e)}"}


def load_financial_data(symbol: str) -> Dict:
    """Load financial data from the outputs/json directory"""
    try:
        json_dir = Path(OUTPUT_DIR) / "json"
        if not json_dir.exists():
            json_dir.mkdir(parents=True, exist_ok=True)
            return {"error": f"JSON directory not found for {symbol}"}

        filepath = json_dir / f"{symbol}_fmp.json"
        if not filepath.exists():
            return {"error": f"No financial data found for {symbol}"}

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                return {"error": f"Empty financial data for {symbol}"}
            return data

    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON data for {symbol}: {str(e)}"}
    except Exception as e:
        return {"error": f"Error loading financial data for {symbol}: {str(e)}"}


def save_report(report: str, symbol: str) -> str:
    """Save the valuation report to a markdown file"""
    try:
        report_path = Path(OUTPUT_DIR) / f"{symbol}_valuation.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        return f"Successfully saved valuation report for {symbol}"
    except Exception as e:
        return f"Error saving report: {str(e)}"


class AnalyzerAgent(ConversableAgent):
    """Agent for analyzing financial data and valuations"""

    def __init__(
        self,
        name: str = "Analyzer",
        system_message: str = ANALYZER_PROMPT,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="TERMINATE",
        )

        self.register_for_llm(
            name="calculate_dcf",
            description="Calculate DCF valuation using financial data",
        )(calculate_dcf)

        self.register_for_llm(
            name="analyze_comparables",
            description="Analyze company using market multiples",
        )(analyze_comparables)

        self.register_for_llm(
            name="assess_synergies",
            description="Assess potential synergies between acquirer and target",
        )(assess_synergies)

        self.register_for_llm(
            name="load_financial_data",
            description="Load financial data for a given stock symbol",
        )(load_financial_data)


class ReporterAgent(ConversableAgent):
    """Agent for generating valuation reports"""

    def __init__(
        self,
        name: str = "Reporter",
        system_message: str = REPORTER_PROMPT,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="TERMINATE",
        )

        self.register_for_execution(
            name="calculate_dcf",
        )(calculate_dcf)
        self.register_for_execution(
            name="analyze_comparables",
        )(analyze_comparables)
        self.register_for_execution(
            name="assess_synergies",
        )(assess_synergies)
        self.register_for_execution(
            name="load_financial_data",
        )(load_financial_data)
        self.register_for_execution(
            name="save_report",
        )(save_report)
