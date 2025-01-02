# mna_automation/agents/web_search_agent.py

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

DATE = datetime.now().strftime("%B %d, %Y")

from autogen import ConversableAgent
from autogen.agentchat.contrib.web_surfer import (
    BingMarkdownSearch,
    RequestsMarkdownBrowser,
    WebSurferAgent,
)

from config.settings import BASE_CONFIG, OUTPUT_DIR

WEB_SURFER_PROMPT = """You are a helpful AI assistant with access to a web browser (via the provided functions). In fact, YOU ARE THE ONLY MEMBER OF YOUR PARTY WITH ACCESS TO A WEB BROWSER, so please help out where you can by performing web searches, navigating pages, and reporting what you find.

When asked to save the final output, use the 'save_to_markdown' tool to save the formatted output to a markdown file. Do not use 'download_file' or 'save_file' tools for this task.
"""

WEB_SURFER_DESC = """A helpful assistant with access to a web browser. Ask them to perform web searches, open pages, navigate to Wikipedia, etc. Once on a desired page, ask them to answer questions by reading the page, generate summaries, find specific words or phrases on the page (ctrl+f), or even just scroll up or down in the viewport.

When asked to save the final output, use the 'save_to_markdown' tool to save the formatted output to a markdown file. Do not use 'download_file' or 'save_file' tools for this task.
"""


RESEARCHER_PROMPT = f"""You are an experienced M&A researcher tasked with finding potential publicly listed acquisition targets based on a strategy report that match the target profile. The year is {DATE}.

WORKFLOW:

1. IDENTIFY ACQUIRER
- Extract and validate acquirer information from the strategy report
- Ensure acquirer is a public company with valid stock symbol
- Store acquirer details in the following format:
  * Company Name
  * Stock Symbol
  * Brief Description

2. ANALYZE & GENERATE INITIAL QUERIES
- Read the provided strategy report focusing on the target profile
- Generate initial search queries focused on:
  * Industry-specific stock screeners and market data
  * Recent IPOs in relevant sectors
  * Small to mid-cap public companies in target industry
  * Companies with complementary technology/patents
  * Emerging public companies with relevant market position
- Ensure queries target companies that are:
  * Publicly listed with valid stock symbols
  * Reasonably sized for acquisition (avoid large-cap companies)
  * Within strategic alignment of acquirer

3. DYNAMIC SEARCH PROCESS
- Execute ONE query at a time:
  * Submit a single search query
  * Review the search results list
  * Request to visit EACH relevant link individually
  * After analyzing each page, store found company information
  * Only move to the next query after fully processing current results
- For each visited page:
  * Extract company details if present
  * Validate public listing status and stock symbol
  * Record market cap and financial metrics
- Handle access errors gracefully:
  * If encountering 403 errors, Cloudflare blocks, or JavaScript warnings
  * Skip the problematic link without retrying
  * Move to the next search result immediately
  * Do not waste time troubleshooting access issues
  * Never ask the web_surfer to enable JavaScript or bypass blocks
- Track companies found so far
- Generate additional focused queries if needed until 15 valid companies are found
- Skip any companies that:
  * Are private (no stock symbol)
  * Are too large to be reasonable acquisition targets
  * Don't align with strategic goals
  
IMPORTANT FOR SEARCH EXECUTION:
- Never submit multiple queries at once
- Always process search results one link at a time
- Use explicit commands like "Please open and analyze the link titled [exact title]"
- Keep track of valid companies found so far
- Generate new queries only after exhausting current search results

4. COMPANY VALIDATION
For each potential target company:
- Verify public listing status and stock symbol
- Assess market capitalization and acquisition feasibility
- Evaluate strategic fit with acquirer
- Check for recent relevant news or market changes
- Remove from consideration if validation fails

5. SYNTHESIZE RESULTS
- Review all gathered information
- Select exactly 15 most relevant public companies that:
  * Are publicly listed with verified stock symbols
  * Have appropriate market cap for acquisition
  * Match strategic requirements
  * Complement acquirer's goals

6. OUTPUT FORMAT
Output the results in the following format:

```markdown
# Acquirer

Company: [Company Name]
Stock Symbol: [Symbol]
Description: [Brief description]

# Target Companies

| Company Name | Stock Symbol | Market Cap | Description |
|-------------|--------------|------------|-------------|
| Company 1   | SYM1         | $X.XB      | Description |
| Company 2   | SYM2         | $X.XB      | Description |
... [continue for all exactly 15 companies]
```

Follow immediately with `TERMINATE` to end the conversation

Example conversation:
```
[web_surfer]
Here is the acquisition strategy report. Let's begin the search process:
// report content

[researcher]
// identify target profile details and create relevant queries
// send first query to web_surfer

[web_surfer]
// search results list

[researcher]
// ask web_surfer to open first link

[web_surfer]
// content of first link

[researcher]
// identify valid company details (if any) and ask to open next link

[web_surfer]
// content of second link

[researcher]
// identify valid company details (if any) and ask to open next link

... continue until current query results are exhausted ...

[researcher]
// generate new query based on findings and send to web_surfer

... continue process until exactly 15 valid companies are found ...

[researcher]
// final formatted output with acquirer and exactly 15 target companies table

`TERMINATE`
```

IMPORTANT GUIDELINES:
- Must find exactly 15 valid public companies
- ALL companies must be publicly listed with verified stock symbols
- Exclude any private companies or those too large for acquisition
- Generate new queries dynamically based on findings
- Continue searching until 15 valid targets are identified
- Include market cap in final output to demonstrate acquisition feasibility
- Verify all stock symbols before including in final list

TOOL USAGE:
- Suggest the 'save_formatted_output' tool call to web_surfer to save the final output to a markdown file

IMPORTANT: When saving the final output to a file, do NOT use 'download_file' or any other tool.
Always use the 'save_to_markdown' tool to save the formatted output.
"""


def save_to_markdown(content: str) -> str:
    """Save the formatted output to a markdown file."""
    try:
        filepath = Path(OUTPUT_DIR) / "target_companies.md"
        os.makedirs(filepath.parent, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully saved formatted output to {filepath}"
    except Exception as e:
        return f"Error saving output: {str(e)}"


class WebSearchAgent:
    """Enhanced WebSearchAgent with improved prompts and tool handling"""

    AGENT_FUNCTIONS = {
        "save_to_markdown": (
            "Save the final acquirer information and target companies to a markdown file",
            save_to_markdown,
        ),
    }

    def __init__(
        self,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
        bing_api_key: Optional[str] = os.getenv("BING_API_KEY"),
    ):
        self.researcher = ConversableAgent(
            name="researcher",
            system_message=RESEARCHER_PROMPT,
            llm_config=llm_config,
            code_execution_config=False,
            human_input_mode="NEVER",
        )

        search_engine = BingMarkdownSearch(bing_api_key=bing_api_key)
        self.web_surfer = WebSurferAgent(
            name="web_surfer",
            system_message=WEB_SURFER_PROMPT,
            description=WEB_SURFER_DESC,
            llm_config=llm_config,
            summarizer_llm_config=llm_config,
            human_input_mode="NEVER",
            browser=RequestsMarkdownBrowser(search_engine=search_engine),
            is_termination_msg=lambda msg: "`TERMINATE`" in msg["content"],
        )
        self._register_functions()

    def _register_functions(self) -> None:
        """Register all functions for both agents."""
        for name, (description, func) in self.AGENT_FUNCTIONS.items():
            self.researcher.register_for_llm(name=name, description=description)(func)
            self.web_surfer.register_for_execution(name=name)(func)

    def initiate_web_search(self, strategy_report: str) -> Dict:
        try:
            result = self.web_surfer.initiate_chat(
                self.researcher,
                message=f"Here is the acquisition strategy report. Generate search queries based on the target profile, then execute them sequentially. After formatting the output, save it to 'outputs/target_companies.md':\n\n{strategy_report}",
                silent=False,
            )

            return {"success": True, "content": result}

        except TimeoutError:
            return {
                "success": False,
                "error": "Search operation timed out. Please try again.",
            }
        except Exception as e:
            return {"success": False, "error": f"An error occurred: {str(e)}"}
