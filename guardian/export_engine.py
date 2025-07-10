import os

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=env_path, override=True)
import csv
import io
import json
import logging
import os
from pathlib import Path

import pandas as pd
import yaml
from jinja2 import Template

# For Notion export markdown -> blocks
from .codexify import flatten_notion_blocks, markdown_to_notion_blocks


logging.basicConfig(level=logging.INFO)
logging.debug("NOTION_API_KEY loaded")
# ========== Export Functions ==========


def export_json(records):
    """Export records as pretty JSON."""
    return json.dumps(records, indent=2)


def export_csv(records):
    """Export records as CSV string."""
    if not records:
        return ""
    df = pd.DataFrame(records)
    return df.to_csv(index=False)


def export_markdown(records, template_str=None):
    """Export records as Markdown using Jinja2 templates."""
    # Default Markdown template if none provided
    default_template = """{% for rec in records %}
- **{{ rec.timestamp }}**: {{ rec.command }}{% if rec.tag %} [{{ rec.tag }}]{% endif %}{% if rec.agent %} ({{ rec.agent }}){% endif %}
{% endfor %}"""
    template = Template(template_str or default_template)
    return template.render(records=records)


def export_html(records, template_str=None):
    """Export records as HTML using Jinja2 templates."""
    default_template = """
    <html>
    <head><title>Guardian Export</title></head>
    <body>
    <ul>
    {% for rec in records %}
        <li><b>{{ rec.timestamp }}</b>: {{ rec.command }}{% if rec.tag %} [{{ rec.tag }}]{% endif %}{% if rec.agent %} ({{ rec.agent }}){% endif %}</li>
    {% endfor %}
    </ul>
    </body>
    </html>
    """
    template = Template(template_str or default_template)
    return template.render(records=records)


def export_yaml(records):
    """Export records as YAML."""
    return yaml.dump(records, sort_keys=False)


def export_mermaid(records):
    """Export memory graph in Mermaid format."""
    # Simple example: parent_id -> id for records with parent/child
    lines = []
    for rec in records:
        if rec.get("parent_id"):
            lines.append(f'{rec["parent_id"]} --> {rec["id"]}')
    graph = "\n".join(lines)
    return f"flowchart LR\n{graph}"


# ========== Export Dispatcher ==========

EXPORTERS = {
    "json": export_json,
    "csv": export_csv,
    "md": export_markdown,
    "html": export_html,
    "yaml": export_yaml,
    "mermaid": export_mermaid,
}


def export_records(records, format, template=None):
    """Dispatch export to correct format using dict-based dispatch."""
    fn = EXPORTERS.get(format)
    if not fn:
        raise ValueError(f"Unsupported export format: {format}")
    if format in ("md", "html"):
        return fn(records, template)
    return fn(records)


# ========== iCloud Export Function ==========


def export_to_icloud(
    records, format="md", filename=None, template=None, subfolder="Guardian Exports"
):
    """
    Export records to iCloud Drive (Guardian Exports subfolder).
    - format: 'md', 'csv', 'json', etc.
    - filename: if None, auto-generates a timestamped filename.
    - template: Jinja2 template for markdown/html (optional).
    - subfolder: Folder inside iCloud Drive (default 'Guardian Exports')
    Returns the path to the exported file.
    """
    icloud_base = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
    export_dir = os.path.join(icloud_base, subfolder)
    try:
        os.makedirs(export_dir, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"Failed to create export directory {export_dir}: {e}")

    # Determine filename
    from datetime import datetime

    ext = format if format != "md" else "md"
    if not filename:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"guardian_export_{ts}.{ext}"
    export_path = os.path.join(export_dir, filename)

    # Export data
    output = export_records(records, format, template)
    mode = "w"
    if isinstance(output, bytes):
        mode = "wb"
    with open(export_path, mode, encoding="utf-8" if "b" not in mode else None) as f:
        f.write(output)

    return export_path


# ========== Notion Export Function ==========


def export_to_notion(
    records,
    parent_id,
    notion_token,
    format="md",
    title=None,
    template=None,
    parent_type="page",
):
    """
    Export records to Notion as a new page under the given parent_id (page or database).
    - parent_id: Notion page or database ID
    - notion_token: API token (from user input/env/secure storage)
    - format: 'md', 'csv', etc. (md recommended for readability)
    - title: Title for the Notion page (optional)
    - template: Jinja2 template for markdown/html (optional)
    Returns Notion page URL or response data.
    """
    # Lazy import for optional dependency
    try:
        from notion_client import Client
    except ImportError:
        raise ImportError(
            "notion-client package required. Run 'pip install notion-client'."
        )

    if not notion_token:
        raise ValueError("Notion token required (from app secure storage or argument).")
    if not parent_id:
        raise ValueError("Notion parent_id (page or database) required.")

    client = Client(auth=notion_token)

    # Prepare content (markdown to Notion blocks, robust production)
    if format == "md":
        # Use export_markdown (Jinja2) to get markdown string
        md_content = export_markdown(records, template)
        # Parse markdown to Notion blocks (robust, production)
        blocks = markdown_to_notion_blocks(md_content)
        children = flatten_notion_blocks(blocks)
        # If empty fallback (shouldn't happen), insert a dummy paragraph
        if not children:
            children = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": md_content}}]
                    },
                }
            ]
    elif format == "json":
        json_content = export_json(records)
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": json_content}}]
                },
            }
        ]
    elif format == "csv":
        csv_content = export_csv(records)
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": csv_content}}]
                },
            }
        ]
    else:
        raise ValueError(
            "Only 'md', 'json', 'csv' formats supported for Notion MVP export."
        )

    # Set page title
    if not title:
        from datetime import datetime

        title = f"Guardian Export {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Build parent param (page or database) explicitly from parent_type
    # Notion API: parent must be {"page_id": ...} or {"database_id": ...}
    parent = {f"{parent_type}_id": parent_id}

    # Create Notion page
    try:
        response = client.pages.create(
            parent=parent,
            properties={"title": [{"type": "text", "text": {"content": title}}]},
            children=children,
        )
        page_url = response.get("url")
        return page_url or response
    except Exception as e:
        raise RuntimeError(f"Failed to export to Notion: {e}")


# ========== Google Drive Export/Import Functions ==========


def export_to_gdrive(
    records, format="md", filename=None, folder_id=None, credentials=None, template=None
):
    """
    Export records to Google Drive as a file.
    - format: 'md', 'csv', 'json', etc.
    - filename: if None, auto-generates timestamped filename.
    - folder_id: target Drive folder ID (None = user's root).
    - credentials: user OAuth credentials object or path to token.pickle file.
    - template: Jinja2 template for markdown/html (optional).
    Returns: file metadata from Drive.
    """
    try:
        import pickle

        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        raise ImportError(
            "google-api-python-client required. Run 'pip install google-api-python-client google-auth-oauthlib'."
        )

    from datetime import datetime

    ext = format if format != "md" else "md"
    if not filename:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"guardian_export_{ts}.{ext}"
    tmp_path = os.path.join("/tmp", filename)
    output = export_records(records, format, template)
    mode = "w"
    if isinstance(output, bytes):
        mode = "wb"
    with open(tmp_path, mode, encoding="utf-8" if "b" not in mode else None) as f:
        f.write(output)

    creds = credentials
    if not creds:
        token_path = "token.pickle"
        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
        else:
            raise ValueError(
                "Google Drive credentials required. Provide as argument or run OAuth flow to create token.pickle."
            )

    service = build("drive", "v3", credentials=creds)
    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(tmp_path, resumable=True)
    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
        .execute()
    )
    os.remove(tmp_path)
    return uploaded


def import_from_gdrive(
    query=None, folder_id=None, credentials=None, download_dir="/tmp"
):
    """
    Import files from Google Drive matching query/folder_id.
    - query: search string for filenames (optional).
    - folder_id: restrict to a folder (optional).
    - credentials: OAuth credentials object or path.
    - download_dir: where to save downloaded files.
    Returns: list of file paths (downloaded), or file contents.
    """
    try:
        import pickle

        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError:
        raise ImportError(
            "google-api-python-client required. Run 'pip install google-api-python-client google-auth-oauthlib'."
        )

    creds = credentials
    if not creds:
        token_path = "token.pickle"
        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
        else:
            raise ValueError(
                "Google Drive credentials required. Provide as argument or run OAuth flow to create token.pickle."
            )

    service = build("drive", "v3", credentials=creds)
    q = []
    if query:
        q.append(f"name contains '{query}'")
    if folder_id:
        q.append(f"'{folder_id}' in parents")
    qstr = " and ".join(q) if q else None

    results = (
        service.files().list(q=qstr, pageSize=10, fields="files(id, name)").execute()
    )
    files = results.get("files", [])
    downloaded_files = []

    for file in files:
        file_id = file["id"]
        name = file["name"]
        request = service.files().get_media(fileId=file_id)
        file_path = os.path.join(download_dir, name)
        with open(file_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        downloaded_files.append(file_path)
    return downloaded_files


def import_from_icloud(filename_or_pattern="*", subfolder="Guardian Exports"):
    """
    Import (read) files from iCloud Drive's Guardian Exports folder.
    - filename_or_pattern: glob or exact match (default '*').
    - subfolder: folder in iCloud Drive (default 'Guardian Exports').
    Returns: list of file paths or file contents.
    """
    icloud_base = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
    export_dir = os.path.join(icloud_base, subfolder)
    if not os.path.exists(export_dir):
        raise FileNotFoundError(f"iCloud folder not found: {export_dir}")

    paths = list(Path(export_dir).glob(filename_or_pattern))
    return [str(p) for p in paths]
