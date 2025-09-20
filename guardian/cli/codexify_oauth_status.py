import json
import os

import click
import requests


@click.command(name="codexify:oauth-status")
@click.option(
    "--base-url",
    default=os.environ.get("GUARDIAN_API_BASE", "http://127.0.0.1:8080"),
    show_default=True,
    help="Base URL of the Guardian API",
)
def oauth_status_cmd(base_url: str):
    """Print Google Drive OAuth status from the running API."""
    try:
        r = requests.get(f"{base_url}/codexify/oauth-status", timeout=5)
        r.raise_for_status()
        data = r.json()
        click.echo(json.dumps(data, indent=2))
    except Exception as e:
        raise click.ClickException(str(e))
