import json
import os
import subprocess
import sys
import webbrowser

import click
import requests


def _default_base() -> str:
    return os.environ.get("GUARDIAN_API_BASE", "http://127.0.0.1:8888")


@click.command(name="codexify:save-entry")
@click.option("--title", required=True, help="Title of the note.")
@click.option("--body", default="", show_default=True, help="Body content.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["md", "txt", "html"]),
    default="md",
    show_default=True,
    help="Output format for preview/export.",
)
@click.option("--folder", help="Google Drive folder ID.")
@click.option("--folder-url", help="Google Drive folder URL (bare ID accepted).")
@click.option(
    "--front-matter",
    "front_matter",
    help="JSON object to include as YAML front matter (md only).",
)
@click.option("--return-links/--no-return-links", default=True, show_default=True)
@click.option("--dry-run/--no-dry-run", default=False, show_default=True)
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
def save_entry_cmd(
    title,
    body,
    fmt,
    folder,
    folder_url,
    front_matter,
    return_links,
    dry_run,
    base_url,
    open_link,
    tags,
    share,
):
    """Preview and optionally export a single entry to Google Drive via the API."""
    try:
        payload = {
            "title": title,
            "body": body,
            "format": fmt,
            "return_links": return_links,
            "dry_run": dry_run,
        }
        if tags:
            # Accept both comma‑separated string and JSON list
            if isinstance(tags, str):
                try:
                    tags_parsed = (
                        json.loads(tags)
                        if tags.strip().startswith("[")
                        else [t.strip() for t in tags.split(",") if t.strip()]
                    )
                except Exception:
                    tags_parsed = [t.strip() for t in tags.split(",") if t.strip()]
            else:
                tags_parsed = tags
            payload["tags"] = tags_parsed
        if share:
            payload["share_anyone_with_link"] = True

        if folder:
            payload["folder"] = folder
        if folder_url:
            payload["folder_url"] = folder_url
        if front_matter:
            try:
                payload["front_matter"] = json.loads(front_matter)
            except Exception as e:
                raise click.ClickException(f"Invalid --front-matter JSON: {e}")

        r = requests.post(f"{base_url}/codexify/save-entry", json=payload, timeout=60)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except Exception:
                detail = r.text
            raise click.ClickException(f"Save-entry failed ({r.status_code}): {detail}")

        data = r.json()
        click.echo(json.dumps(data, indent=2))
        # Friendly link printing if available
        files = data.get("files") or []
        if files:
            click.echo("\nDrive links:")
            first_link = None
            for f in files:
                link = f.get("webViewLink") or f.get("webViewURL") or f.get("link")
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
