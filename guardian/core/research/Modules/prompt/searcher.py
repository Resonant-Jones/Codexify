import datetime


def search_plan(
    task: str,
    todo: list[str],
    k: int = 4,
    search_engine: list[str] = ["google", "arxiv", "google_news"],
    data: list[str] = [],
) -> str:
    step_left = k - len(todo)
    return f"""
        Today is {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        You are an expert planner for search tasks. Your current assignment is to search and gather information on the following topic:

        {task}

        Below is the existing todo list of tasks completed so far:

        {todo}

        You are given the following short_summary information in the data:

        {data}

        You have access to the following tools:

        - **url_search**:  
        Use search engines such as Google, arXiv, Google News, etc., to find relevant URLs for further investigation.  
        *Note:* You only need to provide the search keyword, not the specific site.  
        This tool returns a list of URLs and page descriptions — it does **not** return page content.
        You are given the following search engine:
            {search_engine}

        - **page_content**:  
        Given list of URL from previous search. 
        Summarize the content and key information from the given pages.  
        This tool should be used **only after** performing `url_search` to obtain URLs to summarize.
        You don't need to answer search_engine for this function.

        ---

        Instructions:

        - You have {step_left} remaining tasks allowed; do **not** exceed this limit. Each function call count as a step.
        - CRITICAL: Each url_search MUST be followed by page_content, and this pair counts as TWO steps.
        - For k={k} steps, you can only perform {k//2} search-content pairs maximum.
        - Plan your searches carefully - fewer, more targeted searches are better than many broad ones.
        - Prioritize the most important aspects of the task first, as you may not have steps for everything.
        - If you have odd number of steps remaining, only use even numbers of steps to maintain pairs.
        - The planning step will be invoked repeatedly as new content is added.
        - Your tasks list will be **APPEND** to the list.
        - Use better key words. Don't repeat key words. YOU CAN ALWAYS USE LESS THAN K STEPS. 
        
        Example of correct task planning for k=3:
        [
            {{
                "tool": "url_search",
                "keyword": "specific targeted search term",
                "search_engine": "google",
                "content": "",
                "COMPLETE": "not started"
            }},
            {{
                "tool": "page_content",
                "keyword": "Previous URLs",
                "search_engine": "",
                "content": "",
                "COMPLETE": "not started"
            }}
        ]
        
        Please respond strictly using the following JSON format:

        ```json
        [
            {{
                "tool": "<TOOL_NAME>",
                "keyword": "<SEARCH_KEYWORD>",
                "search_engine":<EXPECTED SEARCH PAGE>,
                "content": "<EMPTY>",
                "COMPLETE": "not started"
            }}
        ]
        ```
    """
