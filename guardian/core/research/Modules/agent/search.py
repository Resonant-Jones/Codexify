from .agent import Agent
from ..model import Model

from ..prompt.searcher import search_plan

from ..browser.crawl_ai import Crawl

from collections import deque
import json

import time 

import ast

class Search_agent(Agent):
    def __init__(self, model:Model, k: int = 10):
        """
        take some default URL for search
        k: number of steps
        """
        self.model = model
        self.crawl = Crawl(model=model)
        self.description = "search latest information"

        self.search_web = [
            "https://google.com",
            "https://arxiv.com",
            "https://news.google.com",
            "https://scholar.google.com",
        ]

        self.todo = deque()
        self.step = 10
        self.url_list = []
        self.db = [] 
        self.name = "searcher"
    
    def set_name(self , name):
        self.name = name

    def _extract_response(self, res):
        import re
        import json
        import codecs
        import ast

        print(f"[DEBUG] _extract_response: Raw input:\n{res}\n--- end raw input ---")

        # Unescape string if it's str type, with ast.literal_eval for robust decoding
        if isinstance(res, str):
            try:
                res = ast.literal_eval(f"'{res}'")
            except Exception:
                try:
                    res = codecs.decode(res, 'unicode_escape')
                except Exception:
                    pass

        # 1. If it's a dict with 'choices', extract actual string content
        if isinstance(res, dict) and 'choices' in res:
            try:
                res = res['choices'][0]['message']['content']
            except Exception as e:
                print(f"[DEBUG] _extract_response: Could not extract content from dict: {e}\nGot: {res}")
                return None

        # 2. If not string now, bail out with debug
        if not isinstance(res, str):
            print(f"[DEBUG] _extract_response: Expected string, got {type(res)}: {res}")
            return None

        # 3. Try to extract JSON from Markdown code block
        markdown_pattern = r"```(?:json)?\n([\s\S]+?)\n```"
        markdown_matches = re.findall(markdown_pattern, res, re.DOTALL)
        if markdown_matches:
            extracted = markdown_matches[0].strip()
            print(f"[DEBUG] _extract_response: Extracted markdown block:\n{extracted}")
            return extracted

        # 4. Try to parse the raw string as JSON
        try:
            json.loads(res.strip())
            print(f"[DEBUG] _extract_response: Raw content is valid JSON:\n{res.strip()}")
            return res.strip()
        except Exception:
            print(f"[DEBUG] _extract_response: Raw content is not valid JSON. Trying fallback extraction.")

        # 5. Fallback: Try to extract JSON objects or arrays from within the string
        json_candidates = []
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start_idx = 0
            while True:
                start_pos = res.find(start_char, start_idx)
                if start_pos == -1:
                    break
                bracket_count = 0
                end_pos = start_pos
                for i in range(start_pos, len(res)):
                    char = res[i]
                    if char == start_char:
                        bracket_count += 1
                    elif char == end_char:
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_pos = i
                            break
                if bracket_count == 0 and end_pos > start_pos:
                    candidate = res[start_pos : end_pos + 1].strip()
                    json_candidates.append(candidate)
                start_idx = start_pos + 1
        for candidate in reversed(json_candidates):
            try:
                json.loads(candidate)
                print(f"[DEBUG] _extract_response: Extracted valid fallback JSON candidate:\n{candidate}")
                return candidate
            except json.JSONDecodeError:
                continue

        print(f"[DEBUG] _extract_response: No valid JSON found after all attempts.")
        return None

    async def run(self, task, data) -> str:
        """
        Search function need to user the brower methods to search relevant contents
        - note that search agent should have it's own planner to plan search with what links

        Steps:
            1. Generate a to do list
            2. For each task
                read current short summary to plan the searching key word
                selecte the search_web
                allow one step depth search [hyper paramerter ?]
                script the content if irrelevant --> ignore
                if relevant --> self to db
                generate long short summary
            3. Return two things
                data: we want to reutrn the long summary
                for response we just need to response "FINISHED"
                AGENT: PLANNER
        """
        print("SEARCHER: RUNNING ")
        print(f"{self.todo} testing..")
        steps =self._plan(task)
        tools = {} 
        url_list = []
        cur_task = 0

        cur_db = [] 
        for d in data:
            cur_db.append(d["summary_list"])
        query = task[:]

        while cur_task < len(self.todo):
            new_task = self.todo[cur_task]
            print(f"new task: {new_task}")
            tool , keyword , search_engine = new_task.get('tool', '') , new_task.get('keyword' , '') , new_task.get("search_engine" , "")

            match tool: 
                case "url_search":
                    urls = await self._search_url(keyword , cur_db , search_engine)
                    for url in urls:
                        self.url_list.append(url)
                case "page_content":
                    #print(self.url_list)
                    await self._page_content(query)
                    self.url_list = [] 
                case _:
                    print("TOOL NOT FOUND")
            cur_task +=1 

        return {"agent": "planner" , "data":self.db , "task":""}

    def get_send_format(self):
        pass

    def get_recv_format(self):
        pass

    def _plan(self , task:str , k:int=6):
        """
        Searcher planner
        """
        prompt = search_plan(task , self.todo , k)
        print(f"task {task}")
        print(prompt)

        response = self.model.completion(prompt)
        print(f"searcher response: {response}")
        time.sleep(3) ## foo foo solution

        # Handle both string and dict responses (Ollama's are dicts with 'choices')
        if isinstance(response, dict) and "choices" in response:
            # Grab the content string from the response object
            res_str = response["choices"][0]["message"]["content"]
        else:
            res_str = response

        raw = self._extract_response(res_str)
        if raw is None:
            raise ValueError("Failed to extract JSON from response")
        todo_list = json.loads(raw)
        
        print(todo_list)
        k -= len(todo_list)
        for todo in todo_list:
            self.todo.append(todo)
        print(f"self.todo in searcher: {self.todo}") 
        #print(tasks)
        return k

    def _task_handler(self , task:str):
        pass

    async def _search_url(self , query, db , search_engine):
        """
            search url with google 
        """
        # test with google first
        # result is an array 

        print("Search URL handling ... ")

        result = await self.crawl.get_url_llm("https://google.com/search?q="+query , query)
        return result

    async def _page_content(self, query):
        print("page content handling ... ")
        if not self.url_list:
            print("[DEBUG] No URLs in self.url_list.")
            return None  # no url

        print(f"[DEBUG] url_list: {self.url_list}")

        urls = []
        for element in self.url_list:
            print(f"[DEBUG] Inspecting element: {element}")
            if isinstance(element, dict) and 'url' in element:
                urls.append(element['url'])
            else:
                print(f"[DEBUG] Skipping element without 'url': {element}")
        print(f"[DEBUG] Collected URLs: {urls}")

        summary_list = await self.crawl.get_summary(urls, query)
        print(f"[DEBUG] Summary list: {summary_list}")

        for summary in summary_list:
            print(f"[DEBUG] Individual summary: {summary}")
            summary['url'] = summary.get('url', "")
            summary['title'] = summary.get('title', "")
            summary['summary'] = summary.get('summary', "")
            summary['brief_summary'] = summary.get('brief_summary', "")
            summary['keywords'] = summary.get('keywords', [])
            self.db.append(
                {
                    "title": summary['title'],
                    "brief_summary": summary['brief_summary'],
                    "summary": summary['summary'],
                    "keywords": summary["keywords"],
                    "url": summary["url"],
                }
            )
        return summary_list
        
        

# --- CLI Entrypoint ---
if __name__ == "__main__":
    import argparse
    from ..model import ollama, gemini, openai  # add imports for your backends as needed
    import asyncio

    parser = argparse.ArgumentParser(description="Run a search agent with a specific query")
    parser.add_argument("--query", type=str, required=True, help="Query to search for")
    parser.add_argument("--backend", type=str, default="ollama", help="Which backend to use: ollama, gemini, openai")
    parser.add_argument("--model", type=str, default="gemma:4b", help="Model name (e.g., gemma:4b, llama3:8b, etc.)")

    args = parser.parse_args()

    # Dynamically select backend/model class
    backend_map = {
        "ollama": ollama.Ollama,
        "gemini": gemini.Gemini,
        "openai": openai.OpenAI,
    }
    ModelClass = backend_map.get(args.backend, ollama.Ollama)
    model_instance = ModelClass(args.model)

    agent = Search_agent(model_instance)
    # The agent's planner and crawl are async, so use asyncio to run them
    async def run_agent():
        # agent.run expects (task, data) -> str (see class above). We'll pass the query and an empty list for data.
        result = await agent.run(args.query, [])
        print(result)

    asyncio.run(run_agent())