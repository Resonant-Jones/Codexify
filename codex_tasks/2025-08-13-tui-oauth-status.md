You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: Add a small CLI command `codexify:oauth-status` that prints Drive auth status

GOAL

- Register a Click command under the existing CLI that fetches /codexify/oauth-status and prints it nicely.
- No external deps beyond `requests` (already present or install if needed).

PATCH
***Begin Patch
*** Add File: guardian/cli/codexify_oauth_status.py
+import json, os, click
+import requests
+
<+@click.command>(name="codexify:oauth-status")
<+@click.option>("--base-url", default=os.environ.get("GUARDIAN_API_BASE","<http://127.0.0.1:8888>"), show_default=True)
+def oauth_status_cmd(base_url: str):
- """Print Google Drive OAuth status from the running API."""
- try:
-        r = requests.get(f"{base_url}/codexify/oauth-status", timeout=5)
-        r.raise_for_status()
-        data = r.json()
-        click.echo(json.dumps(data, indent=2))
- except Exception as e:
-        raise click.ClickException(str(e))

***End Patch
*** Begin Patch
***Update File: guardian/cli/__init__.py
@@
-from .memoryos_cli import cli
+from .memoryos_cli import cli
+from .codexify_oauth_status import oauth_status_cmd
@@
-cli.add_command(tools_group)
+cli.add_command(tools_group)
+cli.add_command(oauth_status_cmd)
*** End Patch
