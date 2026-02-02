"""
Backfill status CLI command.

Provides a simple CLI entrypoint to view backfill status snapshots.
"""

import json

import click

from guardian.workers.backfill_status import get_backfill_status


@click.command("backfill:status")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit compact JSON output.",
)
def backfill_status_cmd(as_json: bool) -> None:
    """Print the backfill status snapshot."""
    status = get_backfill_status()
    if as_json:
        click.echo(json.dumps(status, sort_keys=True))
    else:
        click.echo(json.dumps(status, indent=2, sort_keys=True))
