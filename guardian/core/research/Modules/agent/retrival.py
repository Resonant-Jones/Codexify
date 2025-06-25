import json
import logging
import re

from ..prompt import retrival_agent_prompt
from ..RAG.chrome import VectorSearch
from .agent import Agent

logger = logging.getLogger(__name__)


class RAG_agent(Agent):
    """
    RAG Agent is capable of searching relevant content given a query.
    It maintains its own database for searching and caching recent results.

    Args:
        model: an LLM model
        path: database path, default is "./db"
        filelist: file directory path, default is "./tmp"
    """

    def __init__(self, model, path: str = "./db", filelist="./tmp"):
        self.model = model
        self.db = VectorSearch(path=path)
        self.tool_list = ["add_document", "query", "reset"]
        self.filelist = filelist

    def run(self, task: str, data: str) -> str:
        """
        Processes the task with the given data using the internal tools and vector database.

        Args:
            task: the task to perform
            data: the input data

        Returns:
            A response string based on the result
        """
        logger.info(f"Running RAG_agent with task: {task}, data: {data}")
        return "RAG_agent processing complete."

    def _json_handler(self, res: str):
        """
        Handles JSON response and dispatches to the appropriate tool.

        Args:
            res: the response string to process
        """
        pass

    def get_recv_format(self):
        return {"task": "string", "data": "string"}

    def get_send_format(self):
        return {"result": "string"}

    def __repr__(self):
        return f"<RAG_agent tools={self.tool_list}, filelist='{self.filelist}'>"
