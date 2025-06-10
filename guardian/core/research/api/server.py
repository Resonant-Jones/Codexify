from typing import List
from pydantic import BaseModel

class AgentsRequest(BaseModel):
    agents: List[str]  # List of strings