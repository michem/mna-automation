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

RESEARCHER_PROMPT = f"""You are an experienced M&A researcher tasked with finding potential publically listed acquisition targets based on a strategy report that match the target profile. The year is {DATE}.

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
- Avoid queries that would return large established companies if looking for startups

3. SEQUENTIAL SEARCH
- Use the generated queries and feed them to the WebSurferAgent one by one. You may use queries as "First, Second, Third, Fourth" to indicate the order.
- For each query
  * WebSurferAgent scrapes the top 5 search results/URLs for each query
  * Collect and store relevant company information from the results
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
Here is the acquisition strategy report. Generate search queries based on the target profile, then execute them sequentially:
// report content

[researcher]
### Generated Search Queries

1. <first search query>
2. <second search query>
3. <third search query>
4. <fourth search query>

First, please search for the following.

First Query: <first search query>
[web_surfer]
// search results

[researcher]
Please open, scrape, and display contents of the first link titled <first search result title>

[web_surfer]
// web scraping and summarization

[researcher]
Please open, scrape, and display contents of the second link titled <second search result title>

... same process ...

[researcher]
Second Query: <second search query>

[web_surfer]
// search results

[researcher]
Please open, scrape, and display contents of the first link titled <first search result title>

... same process ...

[researcher]
// Final formatted output with acquirer and target companies table

`TERMINATE`
```

IMPORTANT:
- Generate ALL search queries before starting any searches
- Ensure companies in the final table match size/stage requirements
- All companies must be publicly listed and have a stock symbol
- Do not include any conversation or additional text in final output

TOOL USAGE:
- Use the 'save_formatted_output' tool once your final formatted results are ready.
- For web scraping, instruct the 'web_surfer' to open or summarize search results by referencing their titles. Summaries can be kept until final output.
"""


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


RESEARCHER_PROMPT += """
\n\nAfter formatting the output, use the save_formatted_output tool to save only the formatted section to the specified file.
"""


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
            system_message=RESEARCHER_PROMPT,
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
        self.web_surfer.register_for_llm(
            name="save_formatted_output",
            description="Save the formatted output (acquirer details and target companies table) to a file",
        )(save_formatted_output)

        self.researcher.register_for_execution(name="save_formatted_output")(
            save_formatted_output
        )

    # @with_timeout(30)
    def initiate_web_search(self, strategy_report: str) -> Dict:
        try:
            result = self.web_surfer.initiate_chat(
                self.researcher,
                message=f"Here is the acquisition strategy report. Generate search queries based on the target profile, then execute them sequentially. After formatting the output, save it to 'outputs/target_companies.md':\n\n{strategy_report}",
                silent=False,
            )

            if hasattr(result, "summary"):
                formatted_output = extract_formatted_output(result.summary)
            else:
                formatted_output = extract_formatted_output(str(result))

            return {"success": True, "content": formatted_output}

        except TimeoutError:
            return {
                "success": False,
                "error": "Search operation timed out. Please try again.",
            }
        except Exception as e:
            return {"success": False, "error": f"An error occurred: {str(e)}"}

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
