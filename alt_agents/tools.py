import json
import os
from pathlib import Path

import financedatabase as fd
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from financetoolkit import Toolkit
from typing_extensions import Annotated

load_dotenv()


def collect_financial_metrics(
    symbol: Annotated[str, "Company symbol to analyze"],
    output_dir: Annotated[str, "Directory to save the output"] = "outputs",
) -> dict:
    """Collect key financial metrics using FinanceToolkit.

    Args:
        symbol: The company symbol to analyze.
        output_dir: Directory to save the output files.

    Returns:
        dict: Dictionary containing financial metrics and status message.
    """
    try:
        company = Toolkit(symbol, api_key=os.getenv("FMP_API_KEY"))

        income_statement = company.get_income_statement()
        balance_sheet = company.get_balance_sheet_statement()
        cash_flow = company.get_cash_flow_statement()
        metrics = company.ratios.collect_profitability_ratios()
        historical = company.get_historical_data()

        income_dict = income_statement.reset_index().to_dict("records")
        balance_dict = balance_sheet.reset_index().to_dict("records")
        cash_flow_dict = cash_flow.reset_index().to_dict("records")
        metrics_dict = metrics.reset_index().to_dict("records")
        historical_dict = historical.reset_index().to_dict("records")

        report = f"""# Financial Metrics Report for {symbol}

                ## Income Statement
                {income_statement.to_markdown()}

                ## Balance Sheet
                {balance_sheet.to_markdown()}

                ## Cash Flow Statement
                {cash_flow.to_markdown()}

                ## Profitability Metrics
                {metrics.to_markdown()}

                ## Historical Data
                {historical.to_markdown()}
                """

        output_path = Path(output_dir) / f"{symbol}_metrics.md"
        with open(output_path, "w") as f:
            f.write(report)

        return {
            "status": "success",
            "message": f"Financial metrics collected and saved to {output_path}",
            "data": {
                "income_statement": income_dict,
                "balance_sheet": balance_dict,
                "cash_flow": cash_flow_dict,
                "metrics": metrics_dict,
                "historical": historical_dict,
            },
        }
    except Exception as e:
        return {"status": "error", "message": f"Error collecting metrics: {str(e)}"}


def perform_valuation_analysis(
    symbol: Annotated[str, "Company symbol to analyze"]
) -> dict:
    """Perform comprehensive valuation analysis using FinanceToolkit."""
    try:
        company = Toolkit(symbol, api_key=os.getenv("FMP_API_KEY"))

        try:
            ev = company.models.get_enterprise_value_breakdown()
            ev_dict = ev.to_dict("records")
        except Exception:
            ev_dict = [{"Error": "EV calculation failed"}]

        try:
            profile = company.get_profile()
            first_col = profile.columns[0]
            dcf_value = profile.loc["DCF", first_col]
            dcf_difference = profile.loc["DCF Difference", first_col]

            dcf_dict = [
                {
                    "symbol": symbol,
                    "dcf_value": dcf_value,
                    "dcf_difference": dcf_difference,
                    "current_price": profile.loc["Price", first_col],
                    "valuation_status": (
                        "undervalued"
                        if dcf_value > profile.loc["Price", first_col]
                        else "overvalued"
                    ),
                }
            ]
        except Exception:
            dcf_dict = [{"Error": "DCF calculation failed"}]

        try:
            wacc = company.models.get_weighted_average_cost_of_capital()
            wacc_dict = wacc.to_dict("records")
        except Exception:
            wacc_dict = [{"Error": "WACC calculation failed"}]

        output_path = Path("outputs") / f"{symbol}_valuation.md"
        report = f"""# Valuation Analysis for {symbol}

                    ## Enterprise Value Breakdown
                    {ev.to_markdown() if not isinstance(ev_dict[0].get("Error"), str) else "Error calculating Enterprise Value"}

                    ## DCF Valuation
                    Current Price: {profile.loc['Price', first_col]}
                    DCF Value: {dcf_value}
                    DCF Difference: {dcf_difference}
                    Valuation Status: {'Undervalued' if dcf_value > profile.loc['Price', first_col] else 'Overvalued'}

                    ## Weighted Average Cost of Capital
                    {wacc.to_markdown() if not isinstance(wacc_dict[0].get("Error"), str) else "Error calculating WACC"}
                    """

        with open(output_path, "w") as f:
            f.write(report)

        return {
            "status": "success",
            "data": {"enterprise_value": ev_dict, "dcf": dcf_dict, "wacc": wacc_dict},
            "message": f"Valuation analysis saved to {output_path}",
        }
    except Exception as e:
        return {"status": "error", "message": f"Error performing valuation: {str(e)}"}


def generate_valuation_report(
    strategy_path: Annotated[str, "Path to strategy file"] = "outputs/strategy.md",
    output_path: Annotated[
        str, "Path to save valuation report"
    ] = "outputs/valuation.md",
) -> str:
    """Generate comprehensive valuation report analyzing all companies."""
    try:
        with open(strategy_path, "r") as f:
            strategy = f.read()

        metrics_files = list(Path("outputs").glob("*_metrics.md"))
        symbols = [f.stem.split("_")[0] for f in metrics_files]

        report = ["# M&A Target Valuation Report\n"]
        report.append("## Strategy Overview\n")
        report.append(strategy)
        report.append("\n## Company Analysis\n")

        for symbol in symbols:
            valuation_path = Path("outputs") / f"{symbol}_valuation.md"

            report.append(f"\n### {symbol} Analysis\n")

            if valuation_path.exists():
                with open(valuation_path, "r") as f:
                    valuation = f.read()
                report.append("\n#### Valuation Analysis\n")
                report.append(valuation)

        report.append("\n## Comparative Analysis\n")
        report.append("Analysis of key metrics across companies:")

        report.append("\n## Strategic Fit Assessment\n")
        report.append("Evaluation of each company against strategy requirements:")

        report.append("\n## Final Recommendations\n")
        report.append("Based on the analysis above, ranked recommendations:")

        with open(output_path, "w") as f:
            f.write("\n".join(report))

        return f"Valuation report generated at {output_path}"

    except Exception as e:
        return f"Error generating report: {str(e)}"


def generate_analysis_report(
    companies: Annotated[list, "List of company symbols"],
    all_metrics: Annotated[dict, "Dictionary of financial metrics per company"],
    all_valuations: Annotated[dict, "Dictionary of valuations per company"],
    strategy_path: Annotated[str, "Path to the strategy report"] = "outputs/output.md",
    output_path: Annotated[str, "Path to save the report"] = "outputs/report.md",
) -> str:
    """Generate a comprehensive M&A analysis report in Markdown format."""
    try:
        with open(strategy_path, "r") as f:
            strategy = f.read()

        report = f"""# M&A Target Analysis Report

                    ## Executive Summary
                    This report presents a comprehensive analysis of potential acquisition targets based on the defined strategy and thorough financial analysis.

                    ## Strategy Overview
                    {strategy}

                    ## Financial Analysis of Targets\n"""

        for symbol in companies:
            metrics = all_metrics.get(symbol, {}).get("data", {})
            valuation = all_valuations.get(symbol, {}).get("data", {})

            latest_metrics = (
                metrics.get("metrics", [{}])[-1] if metrics.get("metrics") else {}
            )
            latest_valuation = {
                "ev": (
                    valuation.get("enterprise_value", [{}])[-1]
                    if valuation.get("enterprise_value")
                    else {}
                ),
                "dcf": valuation.get("dcf", [{}])[-1] if valuation.get("dcf") else {},
                "wacc": (
                    valuation.get("wacc", [{}])[-1] if valuation.get("wacc") else {}
                ),
            }

            report += f"""
                    ### {symbol} Analysis
                    #### Financial Performance
                    - Revenue Growth: {latest_metrics.get('Revenue Growth', 'N/A')}
                    - Operating Margin: {latest_metrics.get('Operating Margin', 'N/A')}
                    - ROE: {latest_metrics.get('Return on Equity', 'N/A')}
                    - Net Profit Margin: {latest_metrics.get('Net Profit Margin', 'N/A')}

                    #### Valuation Metrics
                    - Enterprise Value: {latest_valuation['ev'].get('Enterprise Value', 'N/A')}
                    - Intrinsic Value: {latest_valuation['dcf'].get('Intrinsic Value', 'N/A')}
                    - WACC: {latest_valuation['wacc'].get('WACC', 'N/A')}

                    #### Strengths & Risks
                    [Based on the financial analysis above]

                    """

        report += """
                ## Comparative Analysis
                [Detailed comparison of key metrics]

                ## Strategic Fit Assessment
                [Evaluation of strategic alignment]

                ## Final Recommendation
                [Based on comprehensive analysis]
                """

        with open(output_path, "w") as f:
            f.write(report)

        return f"Analysis report saved to {output_path}"
    except Exception as e:
        return f"Error generating report: {str(e)}"


def get_company_profile(symbol: Annotated[str, "Company symbol"]) -> dict:
    """Get company profile information using FinanceToolkit.

    Args:
        symbol: The company symbol to analyze.

    Returns:
        dict: Company profile information.
    """
    try:
        company = Toolkit(symbol, api_key=os.getenv("FMP_API_KEY"))
        profile = company.get_profile()

        return {"status": "success", "data": profile.to_dict()}
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error getting company profile: {str(e)}",
        }


def read_companies_list(path: Annotated[str, "Path to companies JSON"]) -> list:
    """Read list of companies from JSON file.

    Args:
        path (str): Path to JSON file

    Returns:
        list: List of company data
    """
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"status": "error", "message": str(e)}


def generate_comparison_table(valuations: list) -> str:
    """Generate markdown comparison table from valuations.

    Args:
        valuations (list): List of valuation summaries

    Returns:
        str: Markdown formatted table
    """
    try:
        df = pd.DataFrame(valuations)
        df = df[df.columns[~df.columns.isin(["status"])]]  # Remove status column
        return df.to_markdown(index=False, floatfmt=".2f")
    except Exception as e:
        return f"Error generating table: {str(e)}"


def read_companies_list(path: Annotated[str, "Path to companies JSON"]) -> list:
    """Read list of companies from a JSON file.

    Args:
        path (str): Path to the companies JSON file.

    Returns:
        list: List of companies or an error message.
    """
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"status": "error", "message": str(e)}


def generate_comparison_table(valuations: list) -> str:
    """Generate a markdown comparison table from valuations.

    Args:
        valuations (list): List of valuation dictionaries.

    Returns:
        str: Markdown table as a string or an error message.
    """
    try:
        df = pd.DataFrame(valuations)
        markdown_table = df.to_markdown(index=False)
        return markdown_table
    except Exception as e:
        return f"Error generating table: {str(e)}"


def save_response_json(
    response_json: Annotated[str, "JSON String to save"],
    path: Annotated[str, "Path to save"],
) -> None:
    """Save the given JSON string to a file.

    Args:
        response_json (str): The JSON string to be saved.
        path (str): The path to the file where the JSON string will be saved.
    """
    data = json.loads(response_json)
    with open(path, "w") as file:
        json.dump(data, file, indent=4)
    print(f"JSON response saved to {path}")


def save_to_markdown(
    content: str,
    file_path: Annotated[str, "Path to save markdown file"] = "outputs/output.md",
) -> None:
    """Save the given content to a markdown file, overwriting if it exists.

    Args:
        content (str): The content to be saved.
        file_path (str, optional): Path to the markdown file. Defaults to "outputs/output.md".
    """
    with open(file_path, "w") as file:
        file.write(content)
    print(f"Content written to {file_path}")


def read_from_markdown(
    filepath: Annotated[str, "Path of Strategy Report"]
) -> Annotated[str, "Content of Strategy Report"]:
    """Read the content from a markdown file.

    Args:
        filepath (str): Path to the markdown file.

    Returns:
        str: Content of the markdown file.
    """
    with open(filepath, "r") as file:
        content = file.read()
    return content


def save_json_to_disk(
    data: dict, file_path: Annotated[str, "Path to save JSON file"] = "data.json"
) -> None:
    """Save the given dictionary as a JSON file.

    Args:
        data (dict): The dictionary to be saved.
        file_path (str, optional): Path to the JSON file. Defaults to "data.json".
    """
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)
    print(f"JSON data written to {file_path}")


def read_json_from_disk(file_path: Annotated[str, "Path to JSON file"]) -> dict:
    """Read the content from a JSON file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict: Content of the JSON file.
    """
    with open(file_path, "r") as file:
        data = json.load(file)
        if isinstance(data, list):
            return {"data": data}
        return data


def get_options(parameter: Annotated[str, "Parameter you want options for"]) -> dict:
    """Retrieve options for a given parameter.

    Args:
        parameter (str): The parameter to retrieve options for.

    Returns:
        dict: Options for the specified parameter.
    """
    options = fd.obtain_options("equities")
    return convert_ndarray_to_list(options[parameter])


def convert_ndarray_to_list(data):
    """Recursively convert numpy ndarrays to lists in a dictionary.

    Args:
        data: The data to convert.

    Returns:
        The converted data with ndarrays as lists.
    """
    if isinstance(data, np.ndarray):
        return data.tolist()
    elif isinstance(data, dict):
        return {key: convert_ndarray_to_list(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_ndarray_to_list(element) for element in data]
    else:
        return data


def get_companies(
    currency: Annotated[str, "Currency"] = "USD",
    sector: Annotated[str, "Sector"] = "Information Technology",
    industry_group: Annotated[str, "Industry Group"] = "Software & Services",
    industry: Annotated[str, "Industry"] = "Software",
    exchange: Annotated[str, "Exchange"] = "NASDAQ",
    market: Annotated[str, "Market"] = "us_market",
    country: Annotated[str, "Country"] = "United States",
    market_cap: Annotated[str, "Market Cap"] = "Small Cap",
    path: Annotated[str, "Path to save JSON file"] = "companies.json",
) -> str:
    """Filter and save a list of companies based on specified criteria.

    Args:
        currency (str, optional): Currency of companies. Defaults to "USD".
        sector (str, optional): Sector of companies. Defaults to "Information Technology".
        industry_group (str, optional): Industry group. Defaults to "Software & Services".
        industry (str, optional): Industry. Defaults to "Software".
        exchange (str, optional): Stock exchange. Defaults to "NASDAQ".
        market (str, optional): Market. Defaults to "us_market".
        country (str, optional): Country. Defaults to "United States".
        market_cap (str, optional): Market capitalization. Defaults to "Small Cap".
        path (str, optional): Path to save JSON file. Defaults to "companies.json".

    Returns:
        str: Completion message.
    """
    equities = fd.Equities()
    companies = equities.select()

    # Filter the DataFrame based on specific values of multiple columns using .loc
    filtered_companies = companies.loc[
        (companies["currency"] == currency)
        & (companies["sector"] == sector)
        & (companies["industry_group"] == industry_group)
        & (companies["industry"] == industry)
        & (companies["country"] == country)
        & (companies["market_cap"] == market_cap)
    ]

    # Drop rows with NaN values in the 'summary' column
    filtered_companies = filtered_companies.dropna(subset=["summary"])

    # Save the filtered DataFrame to a CSV file
    filtered_companies.to_csv("companies.csv", index=True)

    # Convert the filtered DataFrame to JSON and save to a file
    with open(path, "w") as file:
        json.dump(
            json.loads(filtered_companies.reset_index().to_json(orient="records")),
            file,
            indent=4,
        )

    return "Done"
    # return filtered_companies


def get_number_of_companies(path: Annotated[str, "Path to JSON file"]) -> int:
    """Get the number of companies in the JSON file.

    Args:
        path (str): Path to the JSON file.

    Returns:
        int: Number of companies.
    """
    companies = read_json_from_disk(path)
    return len(companies)


def get_names_and_summaries(path: Annotated[str, "Path to JSON file"]) -> str:
    """Get symbols, names, and summaries of companies from the JSON file.

    Args:
        path (str): Path to the JSON file.

    Returns:
        str: JSON string with symbols, names, and summaries.
    """
    companies = read_json_from_disk(path)
    df = pd.DataFrame(companies, columns=["symbol", "name", "summary"])
    df = df.reset_index(drop=True)
    return df.to_json(orient="records", indent=4)


def collect_and_save_fmp_data(
    symbol: Annotated[str, "Symbol for which data needs to be collected"],
    path: Annotated[str, "Path to save collected data"],
) -> str:
    """Collect FMP data and save it, returning a status message.

    Args:
        symbol (str): Symbol to collect data for.
        path (str): Path to save the collected data.

    Returns:
        str: Status message indicating success or error.
    """
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return (
            "FMP API key not found. Please set the 'FMP_API_KEY' environment variable."
        )
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

        base_path = str(Path(path))
        os.makedirs(base_path, exist_ok=True)
        filepath = Path(base_path) / f"{symbol}_fmp.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return f"Successfully collected and saved FMP data for {symbol}"
    except Exception as e:
        return f"Error processing {symbol}: {str(e)}"


if __name__ == "__main__":
    result = read_json_from_disk(
        "/home/amadgakkhar/code/mna-multi-agent/autogen/outputs/critic_companies.json"
    )
    print(result)
