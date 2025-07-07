# guardian-backend_v2/tasks/connectors/notion.py

from prefect import task
from notion_client import Client
import os

@task
def push_to_notion(rows):
    notion = Client(auth=os.environ["NOTION_API_KEY"])
    database_id = os.environ["NOTION_DATABASE_ID"]

    for row in rows:
        notion.pages.create(
            parent={"database_id": database_id},
            properties={
                "Name": {"title": [{"text": {"content": row[0]}}]},
                "Description": {"rich_text": [{"text": {"content": row[1]}}]}
                # Extend with your columns!
            }
        )