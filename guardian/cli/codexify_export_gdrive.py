import json
import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Any, Dict, List

import click
import requests


def _default_base() -> str:
    return os.environ.get("GUARDIAN_API_BASE", "http://127.0.0.1:8888")


def _load_records_from_file(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    recs: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        recs.append(obj)
    return recs


@click.command(name="codexify:export-gdrive")
@click.option(
    "--title", help="Title of a single note (ignored if --file is used)."
)
@click.option(
    "--body", help="Body of a single note (ignored if --file is used)."
)
@click.option(
    "--file",
    "file_path",
    type=str,
    help="Path to JSON array or NDJSON of records, or '-' for stdin.",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["md", "txt", "html"]),
    default="md",
    show_default=True,
)
@click.option("--folder", help="Google Drive folder ID.")
@click.option("--folder-url", help="Google Drive folder URL.")
@click.option(
    "--front-matter",
    "front_matter",
    help="JSON object to include as YAML front matter (md only). Applies to batch header.",
)
@click.option(
    "--share/--no-share",
    default=False,
    show_default=True,
    help="Set anyone-with-link access.",
)
@click.option(
    "--return-links/--no-return-links",
    default=True,
    show_default=True,
)
@click.option(
    "--base-url",
    default=_default_base,
    show_default=True,
    help="Guardian API base URL.",
)
@click.option(
    "--open/--no-open",
    "open_link",
    default=False,
    show_default=True,
    help="Open the first returned Drive link in a browser.",
)
def export_gdrive_cmd(
    title,
    body,
    file_path: str,
    fmt: str,
    folder: str,
    folder_url: str,
    front_matter: str,
    share: bool,
    return_links: bool,
    base_url: str,
    open_link: bool,
):
    """Export one or more notes to Google Drive via the Guardian API."""
    try:
        if file_path:
            if file_path.strip() == "-":
                # Read NDJSON or JSON array from stdin
                import sys

                text = sys.stdin.read()
                try:
                    data = json.loads(text)
                    if isinstance(data, list):
                        records = data
                    else:
                        raise ValueError(
                            "Top-level JSON must be an array when using stdin."
                        )
                except Exception:
                    # Fallback to NDJSON parsing
                    records = []
                    for line in text.splitlines():
                        s = line.strip()
                        if not s:
                            continue
                        records.append(json.loads(s))
            else:
                p = Path(file_path)
                if not p.exists():
                    try:
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text(
                            '[\n  {"title": "Example Title", "body": "Your text here"}\n]\n',
                            encoding="utf-8",
                        )
                        click.echo(
                            f"Created template file at {p}. Edit it and rerun.",
                            err=True,
                        )
                        return
                    except Exception as e:
                        raise click.ClickException(
                            f"Failed to create template at {p}: {e}"
                        )
                records = _load_records_from_file(p)
        else:
            records: List[Dict[str, Any]] = []
            if title or body:
                records.append(
                    {"title": title or "Untitled", "body": body or ""}
                )
        if not records:
            raise click.ClickException(
                "No records to export. Provide --file or --title/--body."
            )

        payload: Dict[str, Any] = {
            "records": records,
            "format": fmt,
            "return_links": return_links,
        }
        if folder:
            payload["folder"] = folder
        if folder_url:
            payload["folder_url"] = folder_url
        if share:
            payload["share_anyone_with_link"] = True
        if front_matter:
            try:
                payload["front_matter"] = json.loads(front_matter)
            except Exception as e:
                raise click.ClickException(f"Invalid --front-matter JSON: {e}")

        r = requests.post(
            f"{base_url}/codexify/export-gdrive", json=payload, timeout=60
        )
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except Exception:
                detail = r.text
            raise click.ClickException(
                f"Export failed ({r.status_code}): {detail}"
            )

        data = r.json()
        click.echo(json.dumps(data, indent=2))
        files = data.get("files") or []
        if files:
            click.echo("\nDrive links:")
            first_link = None
            for f in files:
                link = (
                    f.get("webViewLink") or f.get("webViewURL") or f.get("link")
                )
                name = f.get("name") or f.get("id")
                if link:
                    click.echo(f" - {name}: {link}")
                    if not first_link:
                        first_link = link
            if open_link and first_link:
                try:
                    if sys.platform == "darwin":
                        subprocess.run(["open", first_link], check=False)
                    else:
                        webbrowser.open(first_link)
                except Exception:
                    pass
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(str(e))
