#!/usr/bin/env python3
"""
ritual_cli.py — The Ritual Conductor for Guardian Backend

Summon, track, and channel ritual automations: Notion seeding, Drive import, iCloud sync, AI distillation, and beyond.

This is not your average CLI. This is the backbone of automation and background magic for the Guardian ecosystem.
"""

import argparse

from guardian_rituals import (  # In the future: import_from_drive_with_progress, etc.
    RITUAL_JOBS,
    seed_notion_db_with_progress,
    start_ritual_job,
)


def cli_seed_notion(args):
    from export_engine import get_notion_token, load_records

    records = load_records(args.records)
    db_id = args.db_id
    notion_token = get_notion_token(args.token)
    job_id = start_ritual_job(
        target=seed_notion_db_with_progress,
        description=f"Seeding Notion DB {db_id}",
        total=len(records),
        records=records,
        db_id=db_id,
        notion_token=notion_token,
    )
    print(f"✨ Summoned Ritual Job: {job_id}")
    print(
        "Use 'ritual_cli.py ritual-status --job-id <id>' to check the progress of your magic."
    )


def cli_ritual_status(args):
    job = RITUAL_JOBS.get(args.job_id)
    if not job:
        print("No such ritual in progress.")
        return
    print(
        f"Job {job.job_id}: {job.state} {job.current}/{job.total} ({job.description})"
    )
    if job.state == "failed":
        print(f"Error: {job.error}")
    elif job.state == "done":
        print("Result:", job.result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ritual CLI — channel batch automations and background processes for Guardian."
    )
    subparsers = parser.add_subparsers(dest="command")

    # Ritual: Seed Notion DB
    parser_seed = subparsers.add_parser(
        "seed-notion", help="Seed a Notion DB with progress tracking."
    )
    parser_seed.add_argument("--records", required=True)
    parser_seed.add_argument("--db-id", required=True)
    parser_seed.add_argument("--token", required=True)
    parser_seed.set_defaults(func=cli_seed_notion)

    # Ritual: Check Ritual Status
    parser_status = subparsers.add_parser(
        "ritual-status", help="Check status of a ritual job."
    )
    parser_status.add_argument("--job-id", required=True)
    parser_status.set_defaults(func=cli_ritual_status)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
