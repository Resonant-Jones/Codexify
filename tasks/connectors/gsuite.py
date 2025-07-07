# guardian-backend_v2/tasks/connectors/gsuite.py

from prefect import task
from google.oauth2 import service_account
from googleapiclient.discovery import build

@task
def get_gsheet_data(spreadsheet_id: str, range_name: str):
    creds = service_account.Credentials.from_service_account_file(
        "secrets/gsuite_service_account.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()
    return result.get('values', [])