import json
import os
import click
import requests


@click.command(name="codexify:oauth-begin")
@click.option(
    "--base-url",
    default=os.environ.get("GUARDIAN_API_BASE", "http://127.0.0.1:8080"),
    show_default=True,
    help="Base URL of the Guardian API",
)
def oauth_begin_cmd(base_url: str):
    """Trigger the Google Drive OAuth flow via the running API and print the token path."""
    try:
        r = requests.post(f"{base_url}/codexify/oauth-begin", timeout=30)
        r.raise_for_status()
        data = r.json()
        click.echo(json.dumps(data, indent=2))
    except Exception as e:
        raise click.ClickException(str(e))

