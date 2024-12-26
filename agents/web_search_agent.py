# mna_automation/agents/web_search_agent.py

import os
import signal
import threading
from datetime import datetime
from functools import wraps
from typing import Dict, Optional, Union

DATE = datetime.now().strftime("%B %d, %Y")

from autogen import ConversableAgent
from autogen.agentchat.contrib.web_surfer import (
    BingMarkdownSearch,
    RequestsMarkdownBrowser,
    WebSurferAgent,
)

from config.settings import BASE_CONFIG

researcher_prompt = f"""You are an experienced M&A researcher tasked with finding potential publicly listed acquisition targets based on a strategy report that match the target profile. The year is {DATE}.

WORKFLOW:

1. IDENTIFY ACQUIRER
- Extract and validate acquirer information from the strategy report
- Ensure acquirer is a public company with valid stock symbol
- Store acquirer details in the following format:
  * Company Name
  * Stock Symbol
  * Brief Description

2. ANALYZE & GENERATE QUERIES
- Read the provided strategy report focusing on the target profile
- Generate 4 specific search queries based on the report
- Ensure queries focus on relevant aspects (e.g., industry, technology, size) and contemporary trends
- Include stock symbol validation in queries where possible
- Avoid queries that would return large established companies if looking for startups

3. SEQUENTIAL SEARCH & VALIDATION
- Use the generated queries and feed them to the WebSurferAgent one by one
- For each query:
  * WebSurferAgent scrapes the top 5 search results/URLs
  * For each potential target company:
    - Verify it is publicly listed
    - Validate stock symbol exists
    - Collect company description and relevant information
  * Store validated companies with their details
- Repeat for all queries

4. SYNTHESIZE RESULTS
- Review all gathered information
- Select the 5 most relevant public companies that best match the target criteria
- Ensure all selected companies:
  * Are publicly listed
  * Have valid stock symbols
  * Match size/stage requirements from strategy
  * Complement acquirer's strategic goals

5. OUTPUT FORMAT
Output the results in the following format:

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

Follow immediately with `TERMINATE` to end the conversation

Example conversation:
```
[web_surfer]
Here is the acquisition strategy report...

[researcher]
Generated Search Queries

"[ACQUIRER NAME] competitors public companies [INDUSTRY]"
"[INDUSTRY] emerging public companies revenue [SIZE RANGE]"
"listed companies [TECHNOLOGY/PRODUCT] market [REGION]"
"public companies [SPECIFIC CAPABILITY] [INDUSTRY] stock"

First Query: <first search query>
[web_surfer]
// search results

[researcher]
Please open, scrape, and display contents of the first link titled <first search result title>

[web_surfer]
// web scraping and summarization
// Continue process for all queries and links

[researcher]
// Final formatted output with acquirer and target companies table

`TERMINATE`
```

IMPORTANT RULES:
- Generate ALL search queries before starting searches
- Verify public status and stock symbol for EVERY company
- Ensure selected companies match size/stage requirements
- Include only companies that complement acquirer's strategy
- Output EXACTLY 5 target companies
- Follow the exact output format specified
- No additional text or explanations in final output
"""


def timeout_handler(signum, frame):
    raise TimeoutError("Function execution timed out")


def with_timeout(timeout_seconds=30):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wrapper

    return decorator


class WebSearchAgent:
    def __init__(
        self,
        llm_config: Optional[Union[Dict, bool]] = BASE_CONFIG,
        bing_api_key: Optional[str] = os.getenv("BING_API_KEY"),
        timeout: int = 30,
    ):
        if isinstance(llm_config, dict) and "request_timeout" in llm_config:
            del llm_config["request_timeout"]
        self.researcher = ConversableAgent(
            name="researcher",
            system_message=researcher_prompt,
            llm_config=llm_config,
            code_execution_config=False,
            human_input_mode="NEVER",
        )

        search_engine = BingMarkdownSearch(bing_api_key=bing_api_key)
        self.web_surfer = WebSurferAgent(
            name="web_surfer",
            llm_config=llm_config,
            summarizer_llm_config=llm_config,
            human_input_mode="NEVER",
            browser=RequestsMarkdownBrowser(
                viewport_size=4096, search_engine=search_engine
            ),
            is_termination_msg=lambda msg: "`TERMINATE`" in msg["content"],
        )
        self.timeout = timeout

    # @with_timeout(30)
    def initiate_web_search(self, strategy_report: str):
        try:
            result = self.web_surfer.initiate_chat(
                self.researcher,
                message=f"Here is the acquisition strategy report. Generate search queries based on the target profile, then execute them sequentially:\n\n{strategy_report}",
                silent=False,
            )
            return result
        except TimeoutError:
            return "Search operation timed out. Please try again."
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def safe_execute_function(self, func, *args, **kwargs):
        """Execute a function with a timeout"""
        result = [None]
        error = [None]

        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout)

        if thread.is_alive():
            return None, "Operation timed out"
        if error[0] is not None:
            return None, str(error[0])
        return result[0], None
