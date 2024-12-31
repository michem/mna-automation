# mna_automation/agents/web_search_agent.py

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import financedatabase as fd
from autogen import ConversableAgent

from config.settings import BASE_CONFIG, OUTPUT_DIR

DATE = datetime.now().strftime("%B %d, %Y")

ANALYZER_PROMPT = f"""You are a financial analysis expert tasked with analyzing M&A strategies and identifying potential acquisition targets using specialized database tools. The current date is {DATE}.

Available Tools:
1. Company Search:
   - search_companies(sector: str, industry: str, market_cap: str, summary_keywords: str) -> Dict
     Search for companies matching specified criteria
     Returns: {{"success": bool, "data": Dict[str, Any]}}
     For summary_keywords, use a single keyword or phrase to identify key capabilities. You may use multiple calls with different keywords.

2. Symbol Validation:
   - validate_stock_symbol(symbol: str) -> Dict
     Verify if a stock symbol exists in the database
     Returns: {{"success": bool, "exists": bool}}

3. Results Storage:
   - save_table_to_markdown(content: str) -> str
     Save final target list in markdown format
     Returns: Status message

Valid Database Parameters:
SECTORS: {{"Communication Services", "Consumer Discretionary", "Consumer Staples", "Energy", "Financials", "Health Care", "Industrials", "Information Technology", "Materials", "Real Estate", "Utilities"}}

INDUSTRIES: {{"Aerospace & Defense", "Air Freight & Logistics", "Airlines", "Auto Components", "Automobiles", "Banks", "Beverages", "Biotechnology", "Building Products", "Capital Markets", "Chemicals", "Commercial Services & Supplies", "Communications Equipment", "Construction & Engineering", "Construction Materials", "Consumer Finance", "Distributors", "Diversified Consumer Services", "Diversified Financial Services", "Diversified Telecommunication Services", "Electric Utilities", "Electrical Equipment", "Electronic Equipment, Instruments & Components", "Energy Equipment & Services", "Entertainment", "Equity Real Estate Investment Trusts (REITs)", "Food & Staples Retailing", "Food Products", "Gas Utilities", "Health Care Equipment & Supplies", "Health Care Providers & Services", "Health Care Technology", "Hotels, Restaurants & Leisure", "Household Durables", "Household Products", "IT Services", "Independent Power and Renewable Electricity Producers", "Industrial Conglomerates", "Insurance", "Interactive Media & Services", "Internet & Direct Marketing Retail", "Machinery", "Marine", "Media", "Metals & Mining", "Multi-Utilities", "Oil, Gas & Consumable Fuels", "Paper & Forest Products", "Pharmaceuticals", "Professional Services", "Real Estate Management & Development", "Road & Rail", "Semiconductors & Semiconductor Equipment", "Software", "Specialty Retail", "Technology Hardware, Storage & Peripherals", "Textiles, Apparel & Luxury Goods", "Thrifts & Mortgage Finance", "Tobacco", "Trading Companies & Distributors", "Transportation Infrastructure", "Water Utilities"}}

MARKET CAPS: {{"Large Cap", "Mega Cap", "Micro Cap", "Mid Cap", "Nano Cap", "Small Cap"}}

Process Steps:
1. Strategy Analysis:
   - Parse strategy document for key requirements
   - Identify target sectors, industries, and market caps
   - Extract key capabilities and determine summary keywords
   - Document search criteria

2. Company Search:
   - Execute targeted searches using search_companies
   - Always specifify all arguments for sector, industry, market cap, and summary keywords
   - Validate results using validate_stock_symbol
   - Track promising matches
   - Continue until 5 strong candidates identified

3. Results Compilation:
   - Format final list according to template
   - Save results using save_table_to_markdown
   - Verify save success

Data Validation:
- Verify sector names match exactly
- Confirm industry names are from valid list
- Validate market cap categories
- Check stock symbols exist
- Ensure company descriptions match strategy

Required Output Format:
```markdown
# Acquirer
Company: [Exact Name]
Stock Symbol: [Valid Symbol]
Description: [Clear Description]

# Target Companies
| Company Name | Stock Symbol | Description |
|-------------|--------------|-------------|
| Name 1      | SYM1         | Description |
| [... exactly 5 entries ...]
```

Example Workflow:
1. Search Implementation:
   ```python
   # Search for software companies
   result = await search_companies(
       sector="Information Technology",
       industry="Software",
       market_cap="Large Cap",
       summary_keywords="cloud"
   )
   if result["success"]:
       companies = result["data"]
   ```

2. Symbol Validation:
   ```python
   # Validate potential target
   validation = await validate_stock_symbol("MSFT")
   if validation["success"] and validation["exists"]:
       potential_targets.append("MSFT")
   ```

3. Save Results:
   ```python
   # Save final list
   status = await save_table_to_markdown(formatted_table)
   if "Successfully saved" in status:
       return "TERMINATE"
   ```

Error Handling:
- Retry failed searches with modified parameters
- Skip invalid symbols
- Report data quality issues
- Document search refinements

Key Reminders:
1. Use exact parameter names from valid lists
2. Validate all symbols before including
3. Maintain clear search rationale
4. Document all decisions
5. Ensure exactly 5 final targets

After completing analysis and finding suitable targets, use save_table_to_markdown with the exact format above and respond with 'TERMINATE'.
"""

RESEARCHER_PROMPT = """You are an M&A research professional who executes company searches and validates potential targets.

PROCESS:
1. When analyzer suggests a search:
   - Execute search_companies exactly as specified
   - Validate results exist and match criteria
   - Report back: "Found X matches. Notable companies: [2-3 examples]"

2. For promising companies:
   - Use validate_stock_symbol to confirm symbol
   - Confirm strategic fit

3. When saving final list:
   - Execute save_table_to_markdown with exact format
   - Verify save was successful
   - Reply only with "TERMINATE"

REQUIREMENTS FOR FINAL TABLE:
- Must contain exactly 5 companies
- Each company must have:
  * Valid, verified stock symbol
  * Full company name
  * Clear description emphasizing strategic fit
- Table must match this exact format:

# Acquirer

Company: [Exact Name]
Stock Symbol: [Valid Symbol]
Description: [Clear Description]

# Target Companies

| Company Name | Stock Symbol | Description |
|-------------|--------------|-------------|
| Name 1      | SYM1         | Description |
| Name 2      | SYM2         | Description |
| Name 3      | SYM3         | Description |
| Name 4      | SYM4         | Description |
| Name 5      | SYM5         | Description |"""


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
    market_cap: str = "",
    summary_keywords: str = "",
) -> Dict:
    """Search for companies matching specified criteria using financedatabase."""
    try:
        equities = fd.Equities()
        results = equities.search(
            sector=sector,
            industry=industry,
            market_cap=market_cap,
            summary=summary_keywords,
        )
        return {"success": True, "data": results.to_dict("index")}
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


def save_table_to_markdown(content: str) -> str:
    """Save the provided table content to target_companies.md file."""
    try:
        filepath = Path(OUTPUT_DIR) / "target_companies.md"
        os.makedirs(filepath.parent, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return "Successfully saved table to target_companies.md"
    except Exception as e:
        return f"Error saving table: {str(e)}"


class WebSearchAgent:
    AGENT_FUNCTIONS = {
        "search_companies": (
            "Search for companies matching specified criteria",
            search_companies,
        ),
        "validate_stock_symbol": (
            "Validate if a stock symbol exists",
            validate_stock_symbol,
        ),
        "save_table_to_markdown": (
            "Save the final acquirer and target companies table",
            save_table_to_markdown,
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

            return {"success": True, "data": result}

        except Exception as e:
            return {"success": False, "error": f"An error occurred: {str(e)}"}
