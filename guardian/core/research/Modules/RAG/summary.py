"""
This file provide method so summaries content with long length with LLM
"""

from ..model import Model
from ..prompt import summary_prompt

from pydantic import BaseModel, Field

import json
import re
import secrets
import string

class Summary(object):
    def __init__(self, model: Model, k: int = 10000):
        self.model = model
        self.db = []
        self.result = []
        # k corresponding to the chunk
        self.k = k
        self.chunks: list[str] = []
        
        self.length = 4

    def summary(self, content: str):
        """
            input content read from markdown 
            output a dict 
            {
                id , url, title , summary , brief_summary , keywords 
            } 
        """
        texts = content.split()
        counter = 0
        paragraph = ""

        for text in texts:
            counter += 1
            paragraph += text + " "
            if counter >= self.k:
                self.chunks.append(paragraph)
                paragraph = ""
                counter = 0
        self.chunks.append(paragraph)
        for chunk in self.chunks:
            prompt = summary_prompt(chunk, self.db)
            """
            """
            alphabet = string.ascii_letters + string.digit

            r = self.model.completion(prompt)  
            json_str = self.extract_json_from_codeblock(r)
            if json_str is None:
                print("No JSON code block found in response")
                continue

            try:
                d = json.loads(json_str)
                rand_id = ''.join(secrets.choice(alphabet) for _ in range(self.length))
                response_obj = {
                    'id': rand_id,
                    'url': d.get('url', ""),
                    'title': d.get('title', ""),
                    'summary': d.get('summary', ""),
                    'brief_summary': d.get('brief_summary', ""),
                    'keywords': d.get('keywords', [])
                }


                full_summary = response_obj['summary']
                short_summary = response_obj['brief_summary']

                self.db.append(short_summary)
                self.result.append(response_obj)

            except:
                print(f"Failed to parse or validate JSON summary")

        return self.result

    def extract_json_from_codeblock(self, text: str) -> str | None:
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        return None


class _Response(BaseModel):
    full_summary: str
    short_summary: str
