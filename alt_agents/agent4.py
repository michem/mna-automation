# mna_automation/agents/valuation_agent.py

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from autogen import ConversableAgent
from configs import OAI_CONFIG, OUTPUT_DIR

# from prompts import analyzer_prompt


ANALYZER_PROMPT = """You are a Valuation Analysis Expert specializing in M&A transactions. Your role is to thoroughly evaluate target companies based on their financial data and the overall acquisition strategy. And generate a detailed report.

Perform the following tasks

1. Collect and store Data for each company using get_financial_metrics("SYMBOL") Function.
2. Get and store Balance Sheets for each company using get_balance_sheet_metrics("SYMBOL") Function.
3. Get and store Market Data for each company using get_market_data("SYMBOL") Function.
4. Calculate DCF Valuation for each company using calculate_dcf Function and store.
5. Perform Individual company analysis for all companies which contains:
- Companies Inromation
- Financial Metrics Summary (Summarize the Financial Metrics in the form of a table)
- Balance Sheet Overview (Provide an Overview of Balance Sheet in the form of a table)
- Market Data (Provide Market Data in the form of a table)
- DCF Valuation Results (Include DCF Valuation Results in the form of a table)
- Comparative analysis (MANDATORY):

6. Perform Comparative analysis in which you compare key financial metrics across companies.

7. Generate a Detailed recommendation.
Disucss pros and cons of going with all of the companies. 
And then finally recommending a company for acquisition. 
Explain why are you recommending it and how does it fit with the requirements outlined in strategy report.

8. Save your report using save_final_report Function.

9. After saving the report, reply with 'TERMINATE'.
"""


def register_tools(agent: ConversableAgent, for_llm: bool = True) -> None:
    """Register all available tools with the agent

    Args:
        agent: The agent to register tools with
        for_llm: If True, register for LLM use. If False, register for execution
    """
    tools = {
        "get_financial_metrics": (
            get_financial_metrics,
            "Get key financial metrics for analysis",
        ),
        "get_balance_sheet_metrics": (
            get_balance_sheet_metrics,
            "Get key balance sheet metrics",
        ),
        "get_market_data": (get_market_data, "Get current market data"),
        "calculate_dcf": (
            calculate_dcf,
            "Calculate DCF valuation using financial data",
        ),
        "load_financial_data": (
            load_financial_data,
            "Load financial data for a given stock symbol",
        ),
        "save_final_report": (
            save_final_report,
            "Save the complete report containing financial data, analysis and recommendations",
        ),
    }

    register_func = agent.register_for_llm if for_llm else agent.register_for_execution

    for name, (func, description) in tools.items():
        if for_llm:
            register_func(name=name, description=description)(func)
        else:
            register_func(name=name)(func)


def save_complete_report(report: str) -> str:
    """Save the complete report containing financial data, analysis and recommendations"""
    try:
        report_path = Path(OUTPUT_DIR) / "valuation.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        recommendation_section = extract_final_recommendation(report)
        if recommendation_section:
            recommendation_path = Path(OUTPUT_DIR) / "recommendation.md"
            with open(recommendation_path, "w", encoding="utf-8") as f:
                f.write(recommendation_section)

        return "Successfully saved complete valuation report"
    except Exception as e:
        return f"Error saving complete report: {str(e)}"


def extract_final_recommendation(report: str) -> str:
    """Extract the final recommendation section from the complete report"""
    try:
        start_idx = report.find("## Final Recommendation")
        if start_idx == -1:
            return ""

        return report[start_idx:].strip()
    except Exception as e:
        return f"Error extracting recommendation: {str(e)}"


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
        json_dir = Path(OUTPUT_DIR) / "fmp_data"
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


def get_financial_metrics(symbol: str, years: int = 5) -> Dict:
    """Get key financial metrics for the last N years"""
    try:
        with open(Path(OUTPUT_DIR) / "fmp_data" / f"{symbol}_fmp.json", "r") as f:
            data = json.load(f)

        financials = data.get("financials", {}).get("financials", [])[:years]
        metrics = {"yearly_metrics": [], "latest": {}}

        for year in financials:

            metrics["yearly_metrics"].append(
                {
                    "date": year.get("date", ""),
                    "revenue": float(year.get("Revenue", 0) or 0),
                    "ebitda": float(year.get("EBITDA", 0) or 0),
                    "net_income": float(year.get("Net Income", 0) or 0),
                    "fcf": float(year.get("Free Cash Flow", 0) or 0),
                }
            )

        if financials:
            latest = financials[0]

            metrics["latest"] = {
                "revenue_growth": float(latest.get("Revenue Growth", 0) or 0),
                "gross_margin": float(latest.get("Gross Margin", 0) or 0),
                "ebitda_margin": float(latest.get("EBITDA Margin", 0) or 0),
                "net_margin": float(latest.get("Net Profit Margin", 0) or 0),
            }

        return metrics
    except Exception as e:
        return {"error": str(e)}


def get_balance_sheet_metrics(symbol: str) -> Dict:
    """Get key balance sheet metrics"""
    try:
        with open(Path(OUTPUT_DIR) / "fmp_data" / f"{symbol}_fmp.json", "r") as f:
            data = json.load(f)

        latest = data.get("balance_sheet", {}).get("financials", [])[0]

        return {
            "cash": float(latest.get("Cash and cash equivalents", 0)),
            "total_debt": float(latest.get("Total debt", 0)),
            "total_assets": float(latest.get("Total assets", 0)),
            "total_liabilities": float(latest.get("Total liabilities", 0)),
            "equity": float(latest.get("Total shareholders equity", 0)),
        }
    except Exception as e:
        return {"error": str(e)}


def get_market_data(symbol: str) -> Dict:
    """Get current market data"""
    try:
        with open(Path(OUTPUT_DIR) / "fmp_data" / f"{symbol}_fmp.json", "r") as f:
            data = json.load(f)

        quote = data.get("quote", [{}])[0]

        return {
            "price": float(quote.get("price", 0)),
            "market_cap": float(quote.get("marketCap", 0)),
            "pe_ratio": float(quote.get("pe", 0)),
            "volume": int(quote.get("volume", 0)),
        }
    except Exception as e:
        return {"error": str(e)}


def save_final_report(report: Annotated[str, "The detailed report generated"]) -> str:
    """Save the final report"""
    try:
        report_path = Path(OUTPUT_DIR) / "valuation.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        return "Successfully saved final recommendation"
    except Exception as e:
        return f"Error saving final recommendation: {str(e)}"


def generate_final_recommendation(analyzed_companies: List[str]) -> str:
    """Generate final recommendation report comparing all analyzed targets"""
    try:
        recommendation = "# M&A Target Comparison and Final Recommendation\n\n"
        companies_data = {}

        for symbol in analyzed_companies:
            companies_data[symbol] = {
                "metrics": get_financial_metrics(symbol),
                "market": get_market_data(symbol),
                "balance": get_balance_sheet_metrics(symbol),
                "dcf": calculate_dcf(get_financial_metrics(symbol)),
            }

        recommendation += "## Financial Comparison\n\n"
        comparison_table = "| Company | Revenue | EBITDA | Market Cap | P/E Ratio | EBITDA Margin | Revenue Growth | EV/EBITDA |\n"
        comparison_table += "|---------|----------|---------|------------|-----------|---------------|----------------|------------|\n"

        for symbol, data in companies_data.items():
            metrics = (
                data["metrics"]["yearly_metrics"][0]
                if data["metrics"]["yearly_metrics"]
                else {}
            )
            latest = data["metrics"]["latest"]
            market = data["market"]

            comparison_table += (
                f"| {symbol} "
                f"| ${metrics.get('revenue', 0)/1e6:.1f}M "
                f"| ${metrics.get('ebitda', 0)/1e6:.1f}M "
                f"| ${market.get('market_cap', 0)/1e6:.1f}M "
                f"| {market.get('pe_ratio', 'N/A')} "
                f"| {latest.get('ebitda_margin', 0)*100:.1f}% "
                f"| {latest.get('revenue_growth', 0)*100:.1f}% "
                f"| {market.get('market_cap', 0)/(metrics.get('ebitda', 1)):.1f}x |\n"
            )

        recommendation += comparison_table + "\n\n"

        recommendation += "## Valuation Analysis\n\n"
        for symbol, data in companies_data.items():
            dcf = data["dcf"]
            recommendation += f"### {symbol} Valuation\n"
            recommendation += f"- Enterprise Value (DCF): ${dcf.get('enterprise_value', 0)/1e6:.1f}M\n"
            recommendation += (
                f"- Present Value of FCF: ${dcf.get('present_value_fcf', 0)/1e6:.1f}M\n"
            )
            recommendation += f"- Terminal Value: ${dcf.get('present_value_terminal', 0)/1e6:.1f}M\n\n"

        recommendation += "## Strategic Assessment\n\n"
        for symbol, data in companies_data.items():
            metrics = data["metrics"]
            recommendation += f"### {symbol} Strategic Fit\n"
            recommendation += (
                f"- Financial Health: {assess_financial_health(metrics)}\n"
            )
            recommendation += (
                f"- Growth Potential: {assess_growth_potential(metrics)}\n"
            )
            recommendation += f"- Risk Assessment: {assess_risk_profile(data)}\n\n"

        recommendation += "## Final Recommendation\n\n"
        best_target = select_best_target(companies_data)
        recommendation += f"Based on comprehensive analysis, {best_target} emerges as the recommended acquisition target:\n\n"
        recommendation += generate_target_summary(companies_data[best_target])

        return recommendation

    except Exception as e:
        return f"Error generating final recommendation: {str(e)}"


def assess_financial_health(metrics: Dict) -> str:
    """Helper function to assess financial health"""
    latest = metrics.get("latest", {})
    return (
        "Strong"
        if latest.get("ebitda_margin", 0) > 0.15
        else "Moderate" if latest.get("ebitda_margin", 0) > 0.08 else "Weak"
    )


def assess_growth_potential(metrics: Dict) -> str:
    """Helper function to assess growth potential"""
    latest = metrics.get("latest", {})
    return (
        "High"
        if latest.get("revenue_growth", 0) > 0.15
        else "Moderate" if latest.get("revenue_growth", 0) > 0.05 else "Low"
    )


def assess_risk_profile(data: Dict) -> str:
    """Helper function to assess risk profile"""
    metrics = data.get("metrics", {}).get("latest", {})
    balance = data.get("balance", {})

    debt_ratio = balance.get("total_debt", 0) / balance.get("total_assets", 1)
    return (
        "High Risk"
        if debt_ratio > 0.6 or metrics.get("ebitda_margin", 0) < 0
        else "Moderate Risk" if debt_ratio > 0.4 else "Low Risk"
    )


def select_best_target(companies_data: Dict) -> str:
    """Helper function to select best target based on metrics"""
    best_score = -float("inf")
    best_target = None

    for symbol, data in companies_data.items():
        metrics = data["metrics"]["latest"]
        score = (
            metrics.get("ebitda_margin", 0) * 0.4
            + metrics.get("revenue_growth", 0) * 0.4
            + (
                1
                - data.get("balance", {}).get("total_debt", 0)
                / data.get("balance", {}).get("total_assets", 1)
            )
            * 0.2
        )

        if score > best_score:
            best_score = score
            best_target = symbol

    return best_target


def generate_target_summary(target_data: Dict) -> str:
    """Helper function to generate target summary"""
    metrics = target_data["metrics"]
    market = target_data["market"]
    dcf = target_data["dcf"]

    return f"""
Key Highlights:
- Current Market Cap: ${market.get('market_cap', 0)/1e6:.1f}M
- DCF Valuation: ${dcf.get('enterprise_value', 0)/1e6:.1f}M
- Revenue Growth: {metrics['latest'].get('revenue_growth', 0)*100:.1f}%
- EBITDA Margin: {metrics['latest'].get('ebitda_margin', 0)*100:.1f}%

Recommended Actions:
1. Initiate preliminary discussions with target management
2. Conduct detailed due diligence
3. Develop integration plan
4. Structure deal terms
"""


def calculate_dcf(
    symbol: str,
) -> Dict[str, float]:
    """
    Calculate the Discounted Cash Flow (DCF) for a given stock symbol.
    Args:
        symbol (str): The stock symbol for which to calculate the DCF.
    Returns:
        Dict[str, float]: A dictionary containing the following keys:
            - "enterprise_value": The calculated enterprise value based on DCF.
            - "present_value_fcf": The present value of projected free cash flows.
            - "present_value_terminal": The present value of the terminal value.
            - "projected_fcfs": A list of projected free cash flows for the next 5 years.
            - "historical_average_fcf": The historical average free cash flow.
            - "error": An error message if the calculation fails or data is insufficient.
    Raises:
        Exception: If there is an error during the DCF calculation.
    """

    fmetrics = get_financial_metrics(symbol)

    wacc: float = 0.12
    growth_rate: float = 0.03
    try:
        if not fmetrics or "yearly_metrics" not in fmetrics:
            return {"error": "Invalid financial data format"}

        metrics = fmetrics.get("yearly_metrics", [])
        if not metrics:
            return {"error": "No historical metrics available"}

        fcf_data = []
        for year in metrics:
            fcf = year.get("fcf")
            if fcf and fcf != 0:
                fcf_data.append(float(fcf))

        if not fcf_data:
            for year in metrics:
                ebitda = year.get("ebitda")
                if ebitda and ebitda != 0:
                    estimated_fcf = float(ebitda) * 0.7
                    fcf_data.append(estimated_fcf)

        if not fcf_data:
            return {"error": "Insufficient data for DCF calculation"}

        base_fcf = sum(fcf_data) / len(fcf_data)

        projection_years = 5
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
            "historical_average_fcf": base_fcf,
        }

    except Exception as e:
        return {"error": f"DCF calculation error: {str(e)}"}


class AnalyzerAgent(ConversableAgent):
    """Agent for analyzing financial data and valuations"""

    def __init__(
        self,
        name: str = "Analyzer",
        system_message: str = ANALYZER_PROMPT,
        llm_config: Optional[Union[Dict, bool]] = OAI_CONFIG,
    ):
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config=llm_config,
            human_input_mode="NEVER",
        )
        register_tools(self, for_llm=True)


class ReporterAgent(ConversableAgent):
    """Agent for generating valuation reports"""

    def __init__(
        self,
        name: str = "Reporter",
        llm_config: Optional[Union[Dict, bool]] = OAI_CONFIG,
    ):
        super().__init__(
            name=name,
            # system_message=system_message,
            llm_config=False,
            human_input_mode="NEVER",
            is_termination_msg=lambda msg: msg.get("content") is not None
            and "TERMINATE" in msg["content"],
        )
        register_tools(self, for_llm=False)


# mna_automation/valuation.py


def read_input_files() -> str:
    """Read both strategy and target companies files"""
    strategy_path = Path("outputs/output.md")
    targets_path = Path("outputs/critic_companies.json")

    if not strategy_path.exists():
        raise FileNotFoundError(
            "Strategy file not found. Please run the strategy agent first."
        )
    if not targets_path.exists():
        raise FileNotFoundError(
            "Target companies file not found. Please run the web search agent first."
        )

    with open(strategy_path, "r", encoding="utf-8") as f:
        strategy_content = f.read()

    with open(targets_path, "r", encoding="utf-8") as f:
        targets_content = f.read()

    return (
        f"Strategy:\n\n{strategy_content}\n\n"
        f"Target Companies Table:\n\n{targets_content}"
    )


def main():
    content = read_input_files()

    analyzer = AnalyzerAgent()
    reporter = ReporterAgent()

    reporter.initiate_chat(
        analyzer,
        message=("Begin" f"{content}"),
    )


if __name__ == "__main__":
    main()
