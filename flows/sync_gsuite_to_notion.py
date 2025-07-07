# guardian-backend_v2/flows/sync_gsuite_to_notion.py

from prefect import flow
from tasks.connectors.gsuite import get_gsheet_data
from tasks.connectors.notion import push_to_notion
from tasks.transforms import clean_rows

@flow
def sync_gsuite_to_notion():
    # Extract
    raw_rows = get_gsheet_data(
        spreadsheet_id="YOUR_SPREADSHEET_ID",
        range_name="Sheet1!A1:D10"
    )

    # Transform
    parsed_rows = clean_rows(raw_rows)

    # Load
    push_to_notion(parsed_rows)

if __name__ == "__main__":
    sync_gsuite_to_notion()