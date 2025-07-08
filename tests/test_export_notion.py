import pytest
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
class FakePages:
    def create(self, **kwargs):
        return {"url": "https://notion.so/fake-page"}

class FakeClient:
    def __init__(self, **kwargs):
        self.pages = FakePages()

from dotenv import load_dotenv

load_dotenv()

import os

print("NOTION_API_KEY is:", os.environ.get("NOTION_API_KEY"))

import json

from guardian.export_engine import export_to_notion

from guardian import export_engine
export_engine.Client = FakeClient

def test_export_to_notion():
    # Sample records to export
    records = [
        {
            "id": "1",
            "title": "Test Record 1",
            "content": "This is a test record.",
            "tags": ["test", "export"],
        },
        {
            "id": "2",
            "title": "Test Record 2",
            "content": "This is another test record.",
            "tags": ["notion", "export"],
        },
    ]

    # Set parent_id from Notion URL
    parent_id = "207beb70dda980d689c3eb67a2645124" 

    # Get Notion token from .env (must have NOTION_API_KEY set in .env)
    notion_token = os.environ.get("NOTION_API_KEY")
    if not notion_token:
        raise ValueError("NOTION_API_KEY not set in environment or .env file!")

    url = export_to_notion(
        records, parent_id, notion_token, format="md", title="Guardian Export Test"
    )
    print("Exported to Notion! Page URL:", url)
