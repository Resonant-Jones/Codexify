"""
This project uses markitdown to handle local files. The key is to process types of document
to markdown.
"""

from openai import OpenAI
from markitdown import MarkItDown

from .chrome import VectorSearch
from ..model import model

import hashlib


class LocalRAG:
    """
    Expected APIs:
        - convert any document to md
        - retrieval based on query
        - convert to patch: set 1000 words per chunk ?
        - add new document to db
    """

    def __init__(self, model: model):
        """
        Args:
            model: model instance to create llm client
        """
        self.vector_db = VectorSearch(name="local_search", path="./local_db")
        self.model = model

    def convert_to_markdown(self, path: str) -> str:
        client = self.model.get_client()
        md = MarkItDown(llm_client=client, llm_model=self.model.get_model())
        result = md.convert(path)
        return result.markdown

    def add_document(self, path: str, k: int = 1000):
        """
        Args:
            path: the path of that file
            k: how many words per patch, default set to be 1000
        add_document will add the document to the db, ID with sha256 of content
        """
        text = self.convert_to_markdown(path)
        words = text.split()
        patch = []
        counter = 0
        arr = []

        for word in words:
            counter += 1
            arr.append(word)
            if counter == k:
                patch.append(" ".join(arr))
                arr = []
                counter = 0

        if counter != 0:
            patch.append(" ".join(arr))

        # now patch is an array of strings
        patch_counter = 0  # reset counter for metadata
        for p in patch:
            sha_id = hashlib.sha256(p.encode("utf-8")).hexdigest()
            self.vector_db.add_document(
                p, sha_id, {"source": path, "patch": patch_counter}
            )
            patch_counter += 1

    def search_document(self, query: str, k: int = 1):
        return self.vector_db.query(query=query, k=k)

    def reset_db(self):
        self.vector_db.reset()
