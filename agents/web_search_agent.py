# mna_automation/agents/web_search_agent.py

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import financedatabase as fd
from autogen import ConversableAgent

from config.settings import BASE_CONFIG, OUTPUT_DIR

DATE = datetime.now().strftime("%B %d, %Y")

ANALYZER_PROMPT = f"""You are a financial analysis expert tasked with analyzing M&A strategies and suggesting appropriate database searches. The year is {DATE}.

FIRST STEP:
You must start by using the obtain_options tool to get valid search parameters:

SUGGESTED_TOOL: obtain_database_options
RATIONALE: Need to get valid search parameters before starting company search

After receiving the options, follow this process:
1. Analyze the strategy report to identify target company criteria
2. Suggest appropriate tool calls using ONLY the parameters available in the database
3. Help refine the search until 5 relevant targets are found

For each subsequent search suggestion, use this format:
SUGGESTED_TOOL: search_companies
PARAMETERS: {{
    "sector": "one from obtained options",
    "industry": "one from obtained options",
    "country": "one from obtained options",
    "market_cap": "one from obtained options",
    "summary_keywords": "relevant keywords"  # Optional
}}
RATIONALE: Brief explanation of why this search matches the strategy

Wait for the researcher to execute each suggestion and provide results before making new ones.
Each suggestion should be focused and specific rather than too broad.

After finding suitable targets, help verify them with validate_stock_symbol tools.

REMEMBER:
- Only use valid parameters from the database options
- Focus searches based on the strategy's key requirements
- Ensure suggested companies match strategic fit
- Help refine searches if initial results aren't suitable"""

RESEARCHER_PROMPT = """You are an M&A research professional who executes company searches and builds target lists based on strategic criteria.

Your responsibilities:
1. Execute tool calls suggested by the analyzer
2. Review and summarize search results
3. Build and maintain a list of potential targets
4. Format and save the final output

WORKFLOW:
1. First execute the obtain_database_options tool call when suggested
2. Share the complete options with the analyzer
3. Execute subsequent search tool calls
4. Share result statistics with analyzer (e.g., "Found 25 matches, 10 in target size range")
5. For promising results, get detailed company info
6. Maintain running list of best matches
7. Once 5 suitable targets identified, format output

The final output format must be:
```markdown
# Acquirer
Company: [Company Name]
Stock Symbol: [Symbol]
Description: [Brief description]

# Target Companies
| Company Name | Stock Symbol | Description |
|-------------|--------------|-------------|
| Company 1   | SYM1         | Description |
| Company 2   | SYM2         | Description |
| Company 3   | SYM3         | Description |
| Company 4   | SYM4         | Description |
| Company 5   | SYM5         | Description |
```

IMPORTANT:
- Execute one search at a time
- Keep track of promising companies
- Validate symbols before adding to final list
- Use save_formatted_output when list is complete
- End with 'TERMINATE' after saving output

Final companies must be:
- Publicly traded with verified symbols
- Match strategy requirements
- Have complete information available
- Represent diverse opportunities within criteria"""


def obtain_database_options() -> Dict:
    """Get all available options from financedatabase."""
    try:
        options = fd.obtain_options("equities")
        return {
            "success": True,
            "data": {
                "sectors": options.get("sector", []).tolist(),
                "industries": options.get("industry", []).tolist(),
                "countries": options.get("country", []).tolist(),
                "market_caps": options.get("market_cap", []).tolist(),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_companies(
    sector: str = "",
    industry: str = "",
    country: str = "",
    market_cap: str = "",
    summary_keywords: str = "",
) -> Dict:
    """Search for companies matching specified criteria using financedatabase."""
    try:
        equities = fd.Equities()
        results = equities.search(
            sector=sector,
            industry=industry,
            country=country,
            market_cap=market_cap,
            summary=summary_keywords,
        )
        return {"success": True, "data": results.to_dict("index")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_company_info(symbol: str) -> Dict:
    """Get detailed information about a specific company."""
    try:
        equities = fd.Equities()
        info = equities.select(symbols=[symbol])
        return {"success": True, "data": info.to_dict("index")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def validate_stock_symbol(symbol: str) -> Dict:
    """Validate if a stock symbol exists in the database."""
    try:
        equities = fd.Equities()
        exists = symbol in equities.select().index
        return {"success": True, "exists": exists}
    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_formatted_output(content: str) -> str:
    """Extract the formatted output section from the chat content."""
    try:
        start_idx = content.rfind("# Acquirer")
        if start_idx == -1:
            return ""

        end_idx = content.find("`TERMINATE`", start_idx)
        if end_idx == -1:
            return content[start_idx:]

        return content[start_idx:end_idx].strip()
    except Exception as e:
        return f"Error extracting output: {str(e)}"


def save_formatted_output(content: str, filepath: str) -> str:
    """Save the formatted output to a file."""
    try:
        output = extract_formatted_output(content)
        if not output:
            return "Error: No valid formatted output found"

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(output)
        return f"Successfully saved formatted output to {filepath}"
    except Exception as e:
        return f"Error saving output: {str(e)}"


class WebSearchAgent:
    AGENT_FUNCTIONS = {
        "obtain_database_options": (
            "Get all available search options from database",
            obtain_database_options,
        ),
        "search_companies": (
            "Search for companies matching specified criteria",
            search_companies,
        ),
        # "get_company_info": (
        #     "Get detailed information about a company",
        #     get_company_info,
        # ),
        "validate_stock_symbol": (
            "Validate if a stock symbol exists",
            validate_stock_symbol,
        ),
        "save_formatted_output": (
            "Save the formatted company list output",
            save_formatted_output,
        ),
    }

    def __init__(
        self,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
    ):
        self.researcher = ConversableAgent(
            name="researcher",
            system_message=RESEARCHER_PROMPT,
            llm_config=llm_config,
            code_execution_config=False,
            human_input_mode="NEVER",
        )

        self.analyzer = ConversableAgent(
            name="analyzer",
            system_message=ANALYZER_PROMPT,
            llm_config=llm_config,
            code_execution_config=False,
            human_input_mode="NEVER",
        )

        self._register_functions()

    def _register_functions(self) -> None:
        """Register all functions for both agents."""
        for name, (description, func) in self.AGENT_FUNCTIONS.items():
            self.analyzer.register_for_llm(name=name, description=description)(func)

            self.researcher.register_for_execution(name=name)(func)

    def initiate_web_search(self, strategy_report: str) -> Dict:
        """Initiate the web search process."""
        try:
            result = self.analyzer.initiate_chat(
                self.researcher,
                message=(
                    f"Here is the acquisition strategy report. Analyze it and suggest "
                    f"appropriate tool calls to find matching companies. After finding "
                    f"suitable targets, format the output and save it to "
                    f"'outputs/target_companies.md':\n\n{strategy_report}"
                ),
                silent=False,
            )

            if hasattr(result, "summary"):
                formatted_output = extract_formatted_output(result.summary)
            else:
                formatted_output = extract_formatted_output(str(result))

            return {"success": True, "content": formatted_output}

        except Exception as e:
            return {"success": False, "error": f"An error occurred: {str(e)}"}
