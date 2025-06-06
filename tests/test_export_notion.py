from dotenv import load_dotenv
load_dotenv()

import os
print("NOTION_API_KEY is:", os.environ.get("NOTION_API_KEY"))

import json
from guardian.export_engine import export_to_notion

# Load from JSON file
with open("my_records.json") as f:
    records = json.load(f)

# Set parent_id from Notion URL
parent_id = "207beb70dda980d689c3eb67a2645124"    # <--- Replace with your actual Notion page or database ID

# Get Notion token from .env (must have NOTION_API_KEY set in .env)
notion_token = os.environ.get("NOTION_API_KEY")
if not notion_token:
    raise ValueError("NOTION_API_KEY not set in environment or .env file!")

url = export_to_notion(
    records,
    parent_id,
    notion_token,
    format="md",
    title="Guardian Export Test"
)
print("Exported to Notion! Page URL:", url)