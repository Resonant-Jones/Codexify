import logging
from typing import List

from pydantic import BaseModel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AgentsRequest(BaseModel):
    agents: List[str]  # List of strings

    def __init__(self, **data):
        super().__init__(**data)
        logger.info(f"AgentsRequest initialized with agents: {self.agents}")
