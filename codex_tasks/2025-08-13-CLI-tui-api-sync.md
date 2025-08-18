You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add CLI command `codexify:export-gdrive` (TUI will auto-detect)

GOAL
- Provide a convenient Click command that hits POST /codexify/export-gdrive.
- Options:
  --title TEXT           (single record)
  --body TEXT            (single record)
  --file PATH            (JSON file with array of {title,body} OR NDJSON)
  --format [md|txt|html] (default md)
  --folder TEXT          (raw folder ID)
  --folder-url TEXT      (Drive folder URL)
  --share / --no-share   (anyone-with-link, default: no-share)
  --return-links         (default True)
  --base-url TEXT        (default $GUARDIAN_API_BASE or http://127.0.0.1:8888)
- Behavior:
  - If --file is given, ignore --title/--body and send records from file.
  - Validate at least one record exists.
  - Pretty-print response links.
  - Fail fast with helpful error messages.

PATCH
*** Begin Patch
*** Add File: guardian/cli/codexify_export_gdrive.py
+import json
+import os
+from pathlib import Path
+from typing import List, Dict, Any
+import click
+import requests
+
+def _default_base() -> str:
+    return os.environ.get("GUARDIAN_API_BASE", "http://127.0.0.1:8888")
+
+def _load_records_from_file(path: Path) -> List[Dict[str, Any]]:
+    text = path.read_text(encoding="utf-8")
+    try:
+        # try JSON array first
+        data = json.loads(text)
+        if isinstance(data, list):
+            return data
+    except Exception:
+        pass
+    # try NDJSON (one JSON object per line)
+    recs: List[Dict[str, Any]] = []
+    for line in text.splitlines():
+        line = line.strip()
+        if not line:
+            continue
+        obj = json.loads(line)
+        recs.append(obj)
+    return recs
+
+@click.command(name="codexify:export-gdrive")
+@click.option("--title", help="Title of a single note (ignored if --file is used).")
+@click.option("--body", help="Body of a single note (ignored if --file is used).")
+@click.option("--file", "file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Path to JSON array or NDJSON of records.")
+@click.option("--format", "fmt", type=click.Choice(["md","txt","html"]), default="md", show_default=True)
+@click.option("--folder", help="Google Drive folder ID.")
+@click.option("--folder-url", help="Google Drive folder URL.")
+@click.option("--share/--no-share", default=False, show_default=True, help="Set anyone-with-link access.")
+@click.option("--return-links/--no-return-links", default=True, show_default=True)
+@click.option("--base-url", default=_default_base, show_default=True, help="Guardian API base URL.")
+def export_gdrive_cmd(title, body, file_path, fmt, folder, folder_url, share, return_links, base_url):
+    """Export one or more notes to Google Drive via the Guardian API."""
+    try:
+        if file_path:
+            records = _load_records_from_file(file_path)
+        else:
+            records = []
+            if title or body:
+                records.append({"title": title or "Untitled", "body": body or ""})
+        if not records:
+            raise click.ClickException("No records to export. Provide --file or --title/--body.")
+
+        payload = {
+            "records": records,
+            "format": fmt,
+            "return_links": return_links,
+        }
+        if folder:
+            payload["folder"] = folder
+        if folder_url:
+            payload["folder_url"] = folder_url
+        if share:
+            payload["share_anyone_with_link"] = True
+
+        r = requests.post(f"{base_url}/codexify/export-gdrive", json=payload, timeout=60)
+        if r.status_code >= 400:
+            try:
+                detail = r.json().get("detail")
+            except Exception:
+                detail = r.text
+            raise click.ClickException(f"Export failed ({r.status_code}): {detail}")
+
+        data = r.json()
+        click.echo(json.dumps(data, indent=2))
+        # Friendly printing of links, if present
+        files = data.get("files") or []
+        if files:
+            click.echo("\nDrive links:")
+            for f in files:
+                link = f.get("webViewLink") or f.get("webViewURL") or f.get("link")
+                name = f.get("name") or f.get("id")
+                if link:
+                    click.echo(f" - {name}: {link}")
+    except click.ClickException:
+        raise
+    except Exception as e:
+        raise click.ClickException(str(e))
*** End Patch
*** Begin Patch
*** Update File: guardian/cli/__init__.py
@@
-from .memoryos_cli import cli
-from .codexify_oauth_status import oauth_status_cmd
+from .memoryos_cli import cli
+from .codexify_oauth_status import oauth_status_cmd
+from .codexify_export_gdrive import export_gdrive_cmd
@@
 cli.add_command(tools_group)
 cli.add_command(oauth_status_cmd)
+cli.add_command(export_gdrive_cmd)
*** End Patch