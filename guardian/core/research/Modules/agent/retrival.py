from ..RAG.chrome import VectorSearch
from .agent import Agent
from ..prompt import retrival_agent_prompt

import json
import re


class RAG_agent(Agent):
    """
    RAG Agent should able to do search relevant content given a query
    It should also have it's own database for search relevant content and also chacing recent result
    Args:
        model: a LLM model
        path: db path , default "./db"
    """

    """
        TODO: dynamic file list ? 
    """
    def __init__(self, model, path: str = "./db" , filelist = "./tmp"):
        self.model = model
        self.db = VectorSearch(path=path)
        self.tool_list = ["add_document", "query", "reset"]
        
        self.filelist = filelist

    def run(self, task: str , data:str) -> str:
        """
            give a promp with:
                task , list of file , list of data in the vector search
                based on the tasks generate what to do next 
            handle every task 
        """
        return {"agent": "planner" , "data" : "" , "task": ""}

    def _json_handler(self, res: str):
        """
        json handler handlers handle json response and then pass it to correct tool
        Args:
            res: the response should be a json string. If it is pure response it should pass to _extract_response first before
            passing to _json_handle
        """
        pass

    def get_recv_format(self):
        pass

    def get_send_format(self):
        pass
