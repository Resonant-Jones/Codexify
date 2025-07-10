import argparse
import json
import pickle

from ..export_engine import export_to_gdrive, import_from_gdrive, import_from_icloud
from ..flows.sync_gsuite_to_notion import sync_gsuite_to_notion


def cli_sync_gsuite_to_notion(args):
    sync_gsuite_to_notion()


def cli_export_gdrive(args):
    with open(args.file) as f:
        records = json.load(f)
    with open(args.token, "rb") as token:
        creds = pickle.load(token)
    result = export_to_gdrive(
        records, format=args.format, folder_id=args.folder, credentials=creds
    )
    print("Exported to Google Drive:", result)


def cli_import_gdrive(args):
    with open(args.token, "rb") as token:
        creds = pickle.load(token)
    files = import_from_gdrive(
        query=args.query,
        folder_id=args.folder,
        credentials=creds,
        download_dir=args.out,
    )
    print("Downloaded files:", files)


def cli_import_icloud(args):
    files = import_from_icloud(args.pattern, args.subfolder)
    print("Found iCloud files:", files)


def main():
    parser = argparse.ArgumentParser(description="Guardian CLI: Digital Archive Nexus")
    subparsers = parser.add_subparsers(dest="command")

    # Google Drive Export
    exp_gd = subparsers.add_parser(
        "export_gdrive", help="Export records to Google Drive"
    )
    exp_gd.add_argument(
        "--file", type=str, required=True, help="Local file with records (JSON)"
    )
    exp_gd.add_argument(
        "--format", type=str, default="md", help="Export format (md, json, csv)"
    )
    exp_gd.add_argument(
        "--folder", type=str, default=None, help="Google Drive folder ID (optional)"
    )
    exp_gd.add_argument(
        "--token",
        type=str,
        default="token.pickle",
        help="Path to token.pickle (from OAuth flow)",
    )
    exp_gd.set_defaults(func=cli_export_gdrive)

    # Google Drive Import
    imp_gd = subparsers.add_parser(
        "import_gdrive", help="Import files from Google Drive"
    )
    imp_gd.add_argument(
        "--query", type=str, default=None, help="Search string for file names"
    )
    imp_gd.add_argument(
        "--folder", type=str, default=None, help="Google Drive folder ID (optional)"
    )
    imp_gd.add_argument(
        "--token", type=str, default="token.pickle", help="Path to token.pickle"
    )
    imp_gd.add_argument("--out", type=str, default="/tmp", help="Download directory")
    imp_gd.set_defaults(func=cli_import_gdrive)

    # iCloud Import
    imp_ic = subparsers.add_parser(
        "import_icloud", help="Import files from iCloud Guardian Exports"
    )
    imp_ic.add_argument(
        "--pattern", type=str, default="*", help="File glob pattern, e.g., '*.md'"
    )
    imp_ic.add_argument(
        "--subfolder", type=str, default="Guardian Exports", help="iCloud subfolder"
    )
    imp_ic.set_defaults(func=cli_import_icloud)

    # Sync GSuite to Notion Flow
    sync_flow = subparsers.add_parser(
        "sync_gsuite_to_notion", help="Sync GSuite Sheets to Notion database"
    )
    sync_flow.set_defaults(func=cli_sync_gsuite_to_notion)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
