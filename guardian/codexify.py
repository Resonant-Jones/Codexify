try:
    from notion_client import Client
except ImportError:
    raise ImportError(
        "notion-client package required. Run 'pip install notion-client'."
    )


def load_alias_map(alias_path):
    if not alias_path or not os.path.exists(alias_path):
        return {}
    with open(alias_path) as f:
        return json.load(f)


def save_alias_map(alias_map, path):
    with open(path, "w") as f:
        json.dump(alias_map, f, indent=2)


def prompt_for_aliases(record_keys, canonical_keys):
    print("\n🪄 Alias Mapping Wizard — Give your fields magical nicknames!\n")
    alias_map = {}
    for k in record_keys:
        if k in canonical_keys:
            alias_map[k] = k
            continue
        suggestion = k.replace("_", " ").title()
        print(f"Original field: '{k}' — Suggestion: [{suggestion}]")
        dest = input(
            f"What alias should '{k}' map to? (press Enter for '{suggestion}'): "
        ).strip()
        if not dest:
            dest = suggestion
        alias_map[k] = dest
    print("\nFinal alias map:")
    for src, dest in alias_map.items():
        print(f"  {src} → {dest}")
    save = input("\nSave this alias map for future use? [y/N]: ").strip().lower() == "y"
    path = None
    if save:
        path = input(
            "Enter filename to save alias map (e.g., my_aliases.json): "
        ).strip()
        save_alias_map(alias_map, path)
        print(f"Alias map saved to {path}")
    return alias_map


def apply_alias_map(records, alias_map):
    """Return a new list of records with user-supplied aliases mapped to canonical field names."""
    mapped_records = []
    for rec in records:
        new_rec = {}
        for k, v in rec.items():
            canonical = alias_map.get(k, k)
            new_rec[canonical] = v
        mapped_records.append(new_rec)
    return mapped_records


def prompt_for_sanctum_name():
    print("\nNo parent page specified for your Codex.")
    print("Would you like to create a new home base for your Guardian's archives?")
    name = input(
        "What shall we name your new sanctum? (press Enter for ‘Guardian Root’): "
    ).strip()
    if not name:
        name = "Guardian Root"
    print(f"Sanctum will be named: '{name}'")
    return name


def prompt_for_db_name(default_title):
    print("\nTime to name your new database (Codex)!")
    name = input(f"Enter a name (press Enter for '{default_title}'): ").strip()
    return name or default_title


def prompt_for_page_id():
    print("\n⚠️  Notion API requires a parent page for all new pages/databases.")
    print(
        "Create a 'Guardian Home' page in Notion, share it with your integration, then paste its Page ID below."
    )
    page_id = input(
        "Paste the Notion page ID of your Guardian's home base (must be shared), or press Enter to cancel: "
    ).strip()
    return page_id or None


from dotenv import load_dotenv

load_dotenv()
import copy


def load_field_map(fieldmap_path):
    if not fieldmap_path or not os.path.exists(fieldmap_path):
        return None
    with open(fieldmap_path) as f:
        fmap = json.load(f)
        # If any value is a string, expand to canonical dict format
        if fmap and all(isinstance(val, str) for val in fmap.values()):
            # User supplied e.g. {"foo": "date", "bar": "rich_text"}
            fmap = {k: {"column": k, "type": v} for k, v in fmap.items()}
        # Normalize minimal ("key": "colname") vs advanced
        elif fmap and isinstance(list(fmap.values())[0], str):
            return {k: {"column": v, "type": None} for k, v in fmap.items()}
        return fmap


def save_field_map(fieldmap, path):
    export_map = {
        k: v["column"] if not v["type"] else {"column": v["column"], "type": v["type"]}
        for k, v in fieldmap.items()
    }
    with open(path, "w") as f:
        json.dump(export_map, f, indent=2)


def prompt_for_fieldmap(record_keys, notion_columns):
    print("\n🧭 Field Mapping Wizard — Guide your chaos!\n")
    fieldmap = {}
    for rk in record_keys:
        if rk in notion_columns:
            fieldmap[rk] = {"column": rk, "type": None}
            continue
        print(f"\nRecord field: '{rk}' does not match any Notion column.")
        print(f"Available Notion columns: {list(notion_columns)}")
        # Offer creative suggestions
        alt1 = rk.replace("_", " ").title()
        alt2 = f"{rk}_field"
        print(f"Suggestions: [{rk}] [{alt1}] [{alt2}]")
        dest = input(
            f"Map '{rk}' to which Notion column? (choose or enter your own): "
        ).strip()
        if not dest:
            dest = rk
        col_type = (
            input(
                f"Type hint for '{dest}'? (press Enter for auto, or specify: text, number, date, select, etc): "
            ).strip()
            or None
        )
        fieldmap[rk] = {"column": dest, "type": col_type}
    print("\nFinal mapping:")
    for src, v in fieldmap.items():
        print(f"  {src} -> {v['column']}" + (f" [{v['type']}]" if v["type"] else ""))
    save = (
        input("\nSave this field mapping for future use? [y/N]: ").strip().lower()
        == "y"
    )
    path = None
    if save:
        path = input(
            "Enter filename to save field map (e.g., my_fieldmap.json): "
        ).strip()
        save_field_map(fieldmap, path)
        print(f"Mapping saved to {path}")
    return fieldmap


class CodexifyError(Exception):
    """Custom error for more readable CLI output."""


import argparse
import datetime
import json
import os

import jinja2


def export_notion_database_to_json(db_id, notion_token, out_file):
    import sys

    client = Client(auth=notion_token)
    # Get database schema
    try:
        db = client.databases.retrieve(db_id)
    except Exception as e:
        print(f"❌ Failed to retrieve Notion database {db_id}: {e}")
        sys.exit(1)
    # Fetch all rows (pagination)
    results = []
    next_cursor = None
    while True:
        resp = client.databases.query(db_id, start_cursor=next_cursor)
        results.extend(resp.get("results", []))
        next_cursor = resp.get("next_cursor")
        if not next_cursor:
            break

    # Flatten Notion blocks to plain dicts
    def notion_row_to_dict(row):
        flat = {}
        props = row["properties"]
        for k, v in props.items():
            if v["type"] == "title":
                flat[k] = v["title"][0]["plain_text"] if v["title"] else ""
            elif v["type"] == "rich_text":
                flat[k] = v["rich_text"][0]["plain_text"] if v["rich_text"] else ""
            elif v["type"] == "date":
                flat[k] = v["date"]["start"] if v["date"] else ""
            elif v["type"] == "number":
                flat[k] = v["number"]
            elif v["type"] == "checkbox":
                flat[k] = v["checkbox"]
            elif v["type"] == "select":
                flat[k] = v["select"]["name"] if v["select"] else ""
            elif v["type"] == "multi_select":
                flat[k] = [opt["name"] for opt in v["multi_select"]]
            elif v["type"] == "people":
                flat[k] = [p.get("name", "") for p in v["people"]]
            elif v["type"] == "url":
                flat[k] = v["url"]
            elif v["type"] == "email":
                flat[k] = v["email"]
            elif v["type"] == "phone_number":
                flat[k] = v["phone_number"]
            else:
                flat[k] = str(v.get(v["type"], ""))
        flat["id"] = row.get("id", "")
        return flat

    as_dicts = [notion_row_to_dict(row) for row in results]
    with open(out_file, "w") as f:
        json.dump(as_dicts, f, indent=2)
    print(
        f"✅ Exported {len(as_dicts)} records from Notion database {db_id} to {out_file}"
    )


def get_or_create_page(client, parent_title, notion_token):
    # LLM NOTE: Notion API limitation — cannot create pages at the workspace (root) level via API.
    # All new pages or databases MUST have an existing parent page (page_id) that is shared with the integration.
    # See https://developers.notion.com/reference/page for details.
    # Try to find an existing page with the title; if not, create it at workspace root
    query = client.search(
        query=parent_title, filter={"property": "object", "value": "page"}
    )
    for res in query.get("results", []):
        if (
            res["object"] == "page"
            and "properties" in res
            and "title" in res["properties"]
            and res["properties"]["title"]["title"][0]["plain_text"] == parent_title
        ):
            print(f"Found existing Notion page: {parent_title}")
            return res["id"]
    # If not found, create at workspace root
    page = client.pages.create(
        parent={"type": "workspace", "workspace": True},
        properties={"title": [{"type": "text", "text": {"content": parent_title}}]},
    )
    print(f"Created new Notion page: {parent_title}")
    return page["id"]


def add_records_to_notion_database(records, db_id, notion_token, fieldmap=None):
    client = Client(auth=notion_token)
    # Fetch columns from Notion DB schema for field matching
    notion_cols = client.databases.retrieve(db_id)["properties"]
    for record in records:
        props = {}
        rec_map = (
            fieldmap if fieldmap else {k: {"column": k, "type": None} for k in record}
        )
        for k, v in record.items():
            mapped = rec_map.get(k, {"column": k, "type": None})
            col = mapped["column"]
            col_type = mapped["type"]
            if col == "Title":
                props[col] = {"title": [{"type": "text", "text": {"content": str(v)}}]}
            else:
                # LLM NOTE: Notion API expects date properties in the form {"date": {"start": ...}} and blank dates must not be included.
                # Prefer type hint, else guess
                if col_type:
                    t = col_type
                else:
                    t = guess_notion_type(v)
                # Map value to Notion property using type
                if t == "checkbox":
                    props[col] = {"checkbox": bool(v)}
                elif t == "number":
                    props[col] = {"number": float(v)}
                elif t == "date":
                    # Fix: Don't create 'date' key if v is blank/None; Notion expects either a valid date or not present at all
                    if v:
                        props[col] = {"date": {"start": str(v)}}
                else:
                    props[col] = {
                        "rich_text": [{"type": "text", "text": {"content": str(v)}}]
                    }
        client.pages.create(parent={"database_id": db_id}, properties=props)
    print(f"Seeded database with {len(records)} records.")


def codexify_database_cli_wrapper():
    parser = argparse.ArgumentParser(
        description="Create a Notion database from JSON records with optional page template and seeding. Supports field and alias mapping for flexible import."
    )
    subparsers = parser.add_subparsers(dest="command")

    # Create parser (existing)
    parser_create = subparsers.add_parser(
        "create",
        help="Create a Notion database from JSON records with optional template and seeding. Supports alias and field mapping.",
    )
    parser_create.add_argument(
        "--records",
        required=True,
        help="Path to JSON file containing records (list of dicts).",
    )
    parser_create.add_argument(
        "--parent-title",
        default=None,
        help="Title of parent page (will create if not found).",
    )
    parser_create.add_argument(
        "--parent-id",
        default=None,
        help="Notion parent page ID (ignored if --parent-title is set).",
    )
    parser_create.add_argument(
        "--token",
        default=os.environ.get("NOTION_API_KEY"),
        help="Notion integration token. Reads from NOTION_API_KEY env if not provided.",
    )
    parser_create.add_argument(
        "--db-title", default=None, help="Title for new database."
    )
    parser_create.add_argument(
        "--with-template", action="store_true", help="Include a page template."
    )
    parser_create.add_argument(
        "--template", default=None, help="Path to markdown file for custom template."
    )
    parser_create.add_argument(
        "--seed",
        action="store_true",
        help="Seed the database with your records as entries.",
    )
    parser_create.add_argument(
        "--verbose", action="store_true", help="Show extra debugging info."
    )
    parser_create.add_argument(
        "--fieldmap",
        default=None,
        help="Path to a JSON field mapping (record key to Notion column/type).",
    )
    parser_create.add_argument(
        "--aliasmap",
        default=None,
        help="Path to a JSON alias map (user alias to canonical field).",
    )
    parser_create.add_argument(
        "--edit-aliases", action="store_true", help="Prompt to edit or preview aliases."
    )

    parser_export = subparsers.add_parser(
        "export", help="Export a Notion database to a JSON file."
    )
    parser_export.add_argument(
        "--db-id", required=True, help="ID of the Notion database to export."
    )
    parser_export.add_argument(
        "--token",
        default=os.environ.get("NOTION_API_KEY"),
        help="Notion integration token. Reads from NOTION_API_KEY env if not provided.",
    )
    parser_export.add_argument("--out", required=True, help="Output JSON file.")

    # New: import-notion subcommand
    parser_import_notion = subparsers.add_parser(
        "import-notion",
        help="Import a Notion database into Guardian's SQLite DB with mapping and preview.",
    )
    parser_import_notion.add_argument(
        "--token",
        default=os.environ.get("NOTION_API_KEY"),
        help="Notion integration token. Reads from NOTION_API_KEY env if not provided.",
    )
    parser_import_notion.add_argument(
        "--preview",
        type=int,
        default=5,
        help="Number of records to preview before import (default: 5).",
    )
    parser_import_notion.add_argument(
        "--save-mapping",
        action="store_true",
        help="Prompt to save alias/field mapping after mapping wizard.",
    )
    parser_import_notion.add_argument(
        "--aliasmap", default=None, help="Path to a JSON alias map to use (or create)."
    )
    parser_import_notion.add_argument(
        "--fieldmap", default=None, help="Path to a JSON field map to use (or create)."
    )
    parser_import_notion.add_argument(
        "--verbose", action="store_true", help="Show extra debugging info."
    )

    args = parser.parse_args()

    if hasattr(args, "command") and args.command == "export":
        if not args.token or not args.token.startswith("ntn_"):
            print(
                "❌ Notion API key not set or invalid. Set NOTION_API_KEY in your .env or use --token."
            )
            import sys

            sys.exit(1)
        export_notion_database_to_json(args.db_id, args.token, args.out)
        import sys

        sys.exit(0)

    if hasattr(args, "command") and args.command == "import-notion":
        # --- Begin import-notion logic ---
        import sys
        import time

        try:
            # Notion token
            notion_token = args.token or os.environ.get("NOTION_API_KEY")
            if not notion_token or not notion_token.startswith("ntn_"):
                notion_token = input(
                    "Enter your Notion API key (starts with 'ntn_'): "
                ).strip()
            if not notion_token or not notion_token.startswith("ntn_"):
                print(
                    "❌ Notion API key not set or invalid. Set NOTION_API_KEY in your .env or use --token."
                )
                sys.exit(1)

            # Notion client
            client = Client(auth=notion_token)
            print("\n🔍 Fetching databases shared with your integration...")
            dbs = []
            next_cursor = None
            while True:
                resp = client.search(
                    filter={"property": "object", "value": "database"},
                    start_cursor=next_cursor,
                )
                dbs.extend(resp.get("results", []))
                next_cursor = resp.get("next_cursor")
                if not next_cursor:
                    break
            if not dbs:
                print(
                    "❌ No Notion databases found. Make sure you have shared at least one database with your integration."
                )
                sys.exit(1)
            print("\nAvailable Notion databases:")
            db_choices = []
            for i, db in enumerate(dbs):
                title = ""
                try:
                    title = (
                        db["title"][0]["plain_text"] if db["title"] else "(Untitled)"
                    )
                except Exception:
                    title = "(Untitled)"
                db_choices.append((db["id"], title))
                print(f"  [{i+1}] {title} (ID: {db['id']})")
            sel = input(
                "\nSelect a database by number, or paste a Notion database ID: "
            ).strip()
            if sel.isdigit() and 1 <= int(sel) <= len(db_choices):
                db_id = db_choices[int(sel) - 1][0]
                db_title = db_choices[int(sel) - 1][1]
            else:
                db_id = sel
                db_title = "(Custom DB ID)"
            # Fetch DB schema and rows
            print("\nFetching database schema and records from Notion...")
            try:
                db_schema = client.databases.retrieve(db_id)
            except Exception as e:
                print(f"❌ Failed to retrieve database: {e}")
                sys.exit(1)
            # Get Notion columns
            notion_columns = list(db_schema["properties"].keys())

            # Fetch records (limit for preview, then all for import)
            def flatten_row(row):
                props = row["properties"]
                flat = {}
                for k, v in props.items():
                    t = v["type"]
                    if t == "title":
                        flat[k] = v["title"][0]["plain_text"] if v["title"] else ""
                    elif t == "rich_text":
                        flat[k] = (
                            v["rich_text"][0]["plain_text"] if v["rich_text"] else ""
                        )
                    elif t == "date":
                        flat[k] = v["date"]["start"] if v["date"] else ""
                    elif t == "number":
                        flat[k] = v["number"]
                    elif t == "checkbox":
                        flat[k] = v["checkbox"]
                    elif t == "select":
                        flat[k] = v["select"]["name"] if v["select"] else ""
                    elif t == "multi_select":
                        flat[k] = [opt["name"] for opt in v["multi_select"]]
                    elif t == "people":
                        flat[k] = [p.get("name", "") for p in v["people"]]
                    elif t == "url":
                        flat[k] = v["url"]
                    elif t == "email":
                        flat[k] = v["email"]
                    elif t == "phone_number":
                        flat[k] = v["phone_number"]
                    else:
                        flat[k] = str(v.get(t, ""))
                flat["id"] = row.get("id", "")
                return flat

            # Fetch preview rows
            preview_rows = []
            next_cursor = None
            preview_count = 0
            print(f"\nPreviewing first {args.preview} records from Notion...")
            while preview_count < args.preview:
                resp = client.databases.query(
                    db_id,
                    start_cursor=next_cursor,
                    page_size=min(args.preview - preview_count, 10),
                )
                batch = resp.get("results", [])
                preview_rows.extend(batch)
                preview_count += len(batch)
                next_cursor = resp.get("next_cursor")
                if not next_cursor or preview_count >= args.preview:
                    break
            flat_preview = [flatten_row(row) for row in preview_rows]
            if flat_preview:
                for i, rec in enumerate(flat_preview):
                    print(f"\n--- Record {i+1} ---")
                    for k in notion_columns:
                        print(f"{k}: {rec.get(k, '')}")
            else:
                print("No records found in this database.")
            # Prompt for alias/field mapping
            # Use first record as sample
            if not flat_preview:
                print("Nothing to import (no records).")
                sys.exit(0)
            sample_keys = list(flat_preview[0].keys())
            # Alias mapping
            alias_map = None
            if getattr(args, "aliasmap", None):
                alias_map = load_alias_map(args.aliasmap)
            else:
                alias_map = prompt_for_aliases(sample_keys, sample_keys)
            # Field mapping (Notion columns to Guardian canonical fields)
            fieldmap = None
            if getattr(args, "fieldmap", None):
                fieldmap = load_field_map(args.fieldmap)
            else:
                fieldmap = prompt_for_fieldmap(sample_keys, notion_columns)
            # Optionally save mapping
            if getattr(args, "save_mapping", False):
                if alias_map:
                    path = input(
                        "Save alias map as (filename)? (blank to skip): "
                    ).strip()
                    if path:
                        save_alias_map(alias_map, path)
                        print(f"Alias map saved to {path}")
                if fieldmap:
                    path = input(
                        "Save field map as (filename)? (blank to skip): "
                    ).strip()
                    if path:
                        save_field_map(fieldmap, path)
                        print(f"Field map saved to {path}")
            # Confirm import
            confirm = (
                input("\nReady to import records into Guardian? [y/N]: ")
                .strip()
                .lower()
            )
            if confirm != "y":
                print("Aborted.")
                sys.exit(0)
            # Fetch ALL records for import
            print("\nFetching all records from Notion for import...")
            all_rows = []
            next_cursor = None
            while True:
                resp = client.databases.query(db_id, start_cursor=next_cursor)
                batch = resp.get("results", [])
                all_rows.extend(batch)
                next_cursor = resp.get("next_cursor")
                if not next_cursor:
                    break
            flat_records = [flatten_row(row) for row in all_rows]
            # Apply alias mapping
            if alias_map:
                flat_records = apply_alias_map(flat_records, alias_map)
            # Map field names using fieldmap to Guardian canonical fields
            mapped_records = []
            for rec in flat_records:
                new_rec = {}
                for k, v in rec.items():
                    # Map using fieldmap
                    if fieldmap and k in fieldmap:
                        dest = fieldmap[k]["column"]
                    else:
                        dest = k
                    new_rec[dest] = v
                mapped_records.append(new_rec)
            # Import to Guardian DB
            print("\nImporting records into Guardian's SQLite DB...")
            try:
                # Defensive: Import GuardianDB here
                try:
                    from guardian_db import GuardianDB
                except ImportError:
                    try:
                        from guardian_db import GuardianDB
                    except Exception:
                        GuardianDB = None
                if "GuardianDB" not in locals() or GuardianDB is None:
                    print(
                        "❌ GuardianDB module/class not found. Please ensure GuardianDB is available in your environment."
                    )
                    sys.exit(1)
                db = GuardianDB()
                imported = 0
                for idx, rec in enumerate(mapped_records):
                    db.insert_record(rec)
                    if (idx + 1) % 25 == 0:
                        print(f"  Imported {idx+1}/{len(mapped_records)} records...")
                    imported += 1
                print(
                    f"\n✅ Import complete! {imported} records imported into Guardian DB."
                )
            except Exception as e:
                print(f"❌ Error during import: {e}")
                if getattr(args, "verbose", False):
                    import traceback

                    traceback.print_exc()
                sys.exit(1)
            print("🎉 All done! Your Notion database is now in Guardian.")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if getattr(args, "verbose", False):
                import traceback

                traceback.print_exc()
            sys.exit(2)
        # --- End import-notion logic ---

    if args.command != "create":
        parser.print_help()
        print(
            "⚠️  All Notion exports require a valid parent page ID. Create and share a home base page with your integration, then use its ID for all Codex/database operations."
        )
        import sys

        sys.exit(1)

    try:
        # Check Notion token
        if not args.token or not args.token.startswith("ntn_"):
            raise CodexifyError(
                "❌ Notion API key not set or invalid. Set NOTION_API_KEY in your .env or use --token. Find your integration token at https://www.notion.so/my-integrations"
            )

        # Check records file
        if not os.path.exists(args.records):
            raise CodexifyError(f"❌ Records file not found: {args.records}")

        with open(args.records) as f:
            try:
                records = json.load(f)
            except Exception as e:
                raise CodexifyError(f"❌ Could not parse JSON in {args.records}: {e}")
        if not isinstance(records, list) or not all(
            isinstance(r, dict) for r in records
        ):
            raise CodexifyError(
                "❌ Records must be a JSON list of dicts. See the CLI docs for a sample."
            )

        # Check for field consistency
        base_keys = set(records[0].keys())
        for i, rec in enumerate(records):
            rec_keys = set(rec.keys())
            if rec_keys != base_keys:
                raise CodexifyError(
                    f"❌ Inconsistent fields in record {i+1}: Expected {base_keys}, got {rec_keys}"
                )

        # Alias mapping support
        alias_map = {}
        if getattr(args, "aliasmap", None):
            alias_map = load_alias_map(args.aliasmap)
        elif getattr(args, "edit_aliases", False):
            # Prompt for alias mapping if desired, using current record keys and canonical keys (base_keys)
            alias_map = prompt_for_aliases(
                list(base_keys), list(base_keys)
            )  # Expand to support more flexible canonical keys if needed
        else:
            alias_map = {}  # Identity mapping if not set

        if alias_map:
            records = apply_alias_map(records, alias_map)

        template_md = None
        if args.template:
            if not os.path.exists(args.template):
                raise CodexifyError(f"❌ Template file not found: {args.template}")
            with open(args.template) as f:
                template_md = f.read()

        client = Client(auth=args.token)
        if args.parent_title:
            parent_page_id = get_or_create_page(client, args.parent_title, args.token)
        elif args.parent_id:
            parent_page_id = args.parent_id
        else:
            # Hybrid: Offer to create or let user paste ID
            page_id = prompt_for_page_id()
            if page_id:
                parent_page_id = page_id
            else:
                # Let user name the new page
                sanctum_name = prompt_for_sanctum_name()
                parent_page_id = get_or_create_page(client, sanctum_name, args.token)

        # Prompt user for DB name if not provided (always after parent_page_id is set)
        default_db_title = (
            f"Guardian Codex {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        db_title = args.db_title or prompt_for_db_name(default_db_title)

        try:
            db_id = create_notion_database_from_records(
                records,
                parent_page_id,
                args.token,
                db_title=db_title,
                with_template=args.with_template,
                template_markdown=template_md,
            )
        except Exception as e:
            if "permission" in str(e).lower():
                raise CodexifyError(
                    "❌ Notion permission error. Did you share the parent page with your integration?\nSee: https://www.notion.so/my-integrations"
                )
            raise CodexifyError(f"❌ Notion API error: {e}")
        print(f"✅ Database created! ID: {db_id}")

        if args.seed:
            fieldmap = None
            if args.fieldmap:
                fieldmap = load_field_map(args.fieldmap)
            # If not supplied, prompt if any mismatches:
            else:
                # Infer Notion columns from created DB
                client_for_map = Client(auth=args.token)
                db_schema = client_for_map.databases.retrieve(db_id)
                notion_cols = set(db_schema["properties"].keys())
                rec_keys = set(records[0].keys())
                if rec_keys - notion_cols or notion_cols - rec_keys:
                    fieldmap = prompt_for_fieldmap(rec_keys, notion_cols)
            try:
                add_records_to_notion_database(
                    records, db_id, args.token, fieldmap=fieldmap
                )
                print("✅ Database seeded with all records.")
            except Exception as e:
                raise CodexifyError(f"❌ Failed to seed database: {e}")

    except CodexifyError as ce:
        print(str(ce))
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        exit(1)
    except Exception as e:
        print("❌ Unexpected error:", e)
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        exit(2)


def markdown_to_notion_blocks(md_text):
    """
    Converts markdown to Notion-style block objects (headings, bullets, code, quotes, todos, etc.).
    Uses mistune for AST parsing and robust mapping, adapting to mistune version.
    """
    import mistune
    from packaging import version

    mistune_version = version.parse(getattr(mistune, "__version__", "0.0.0"))

    if mistune_version >= version.parse("3.0.0"):
        markdown = mistune.create_markdown(renderer="ast")
        ast = markdown(md_text)
    else:
        try:
            from mistune.renderers import AstRenderer

            markdown = mistune.create_markdown(renderer=AstRenderer())
            ast = markdown(md_text)
        except ImportError:
            raise RuntimeError(
                "AstRenderer not available and mistune version is too old"
            )

    blocks = []
    for node in ast:
        if node["type"] == "heading":
            level = node["level"]
            text = (
                "".join(
                    child.get("text", "") if isinstance(child, dict) else str(child)
                    for child in node.get("children", [])
                )
                if "children" in node
                else node["text"]
            )
            block_type = f"heading_{min(level, 3)}"
            blocks.append(
                {
                    "type": block_type,
                    "block": {
                        block_type: {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        }
                    },
                }
            )
        elif node["type"] == "list":
            ordered = False
            if "ordered" in node:
                ordered = node["ordered"]
            elif isinstance(node.get("attrs"), dict):
                ordered = node["attrs"].get("ordered", False)
            for item in node["children"]:
                block_type = (
                    "bulleted_list_item" if not ordered else "numbered_list_item"
                )
                text = (
                    "".join(
                        child.get("text", "") if isinstance(child, dict) else str(child)
                        for child in item.get("children", [])
                    )
                    if "children" in item
                    else item["text"]
                )
                blocks.append(
                    {
                        "type": block_type,
                        "block": {
                            block_type: {
                                "rich_text": [
                                    {"type": "text", "text": {"content": text}}
                                ]
                            }
                        },
                    }
                )
        elif node["type"] == "block_code":
            blocks.append(
                {
                    "type": "code",
                    "block": {
                        "code": {
                            "rich_text": [
                                {"type": "text", "text": {"content": node["text"]}}
                            ],
                            "language": node.get("info") or "plain text",
                        }
                    },
                }
            )
        elif node["type"] == "block_quote":
            text = (
                "".join(
                    child.get("text", "") if isinstance(child, dict) else str(child)
                    for child in node.get("children", [])
                )
                if "children" in node
                else node.get("text", "")
            )
            blocks.append(
                {
                    "type": "quote",
                    "block": {
                        "quote": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        }
                    },
                }
            )
        elif node["type"] == "task_list":
            # Notion does not have a native todo block, so map to to-do
            for item in node["children"]:
                checked = item.get("checked", False)
                text = (
                    "".join(
                        child.get("text", "") if isinstance(child, dict) else str(child)
                        for child in item.get("children", [])
                    )
                    if "children" in item
                    else item.get("text", "")
                )
                blocks.append(
                    {
                        "type": "to_do",
                        "block": {
                            "to_do": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": text}}
                                ],
                                "checked": checked,
                            }
                        },
                    }
                )
        elif node["type"] == "paragraph":
            text = (
                "".join(
                    child.get("text", "") if isinstance(child, dict) else str(child)
                    for child in node.get("children", [])
                )
                if "children" in node
                else node.get("text", "")
            )
            blocks.append(
                {
                    "type": "paragraph",
                    "block": {
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        }
                    },
                }
            )
        # Extend: add toggle, image, etc. as needed
    return blocks


def flatten_notion_blocks(blocks):
    """
    Returns a list of Notion block dicts (API-ready).
    """
    return [b["block"] for b in blocks if "block" in b]


import datetime

import jinja2
import requests


def guess_notion_type(value):
    if isinstance(value, bool):
        return "checkbox"
    try:
        float(value)
        return "number"
    except (TypeError, ValueError):
        pass
    try:
        datetime.datetime.fromisoformat(str(value))
        return "date"
    except Exception:
        pass
    return "rich_text"


def field_to_property(field, value):
    prop_type = guess_notion_type(value)
    if prop_type == "checkbox":
        return {"checkbox": bool(value)}
    elif prop_type == "number":
        return {"number": float(value)}
    elif prop_type == "date":
        # Notion API expects {"start": ...}
        return {"date": {"start": str(value)}}
    else:
        return {"rich_text": [{"type": "text", "text": {"content": str(value)}}]}


def build_notion_db_properties_from_fieldmap(fieldmap, sample_record):
    """
    Returns a Notion-ready 'properties' dict using the user's fieldmap or inferring from the sample record.
    Ensures all columns have proper Notion types and use empty objects (never lists) per Notion API spec.
    """
    # Normalize fieldmap: if any type is a string (e.g., "date"), convert to Notion object
    type_map = {
        "date": {"date": {}},
        "checkbox": {"checkbox": {}},
        "number": {"number": {}},
        "title": {"title": {}},
        "rich_text": {"rich_text": {}},
        "select": {"select": {}},
        "multi_select": {"multi_select": {}},
        # Add more as needed
    }
    # If user provided a fieldmap with simple strings, expand to object
    if fieldmap:
        for k, v in fieldmap.items():
            if isinstance(v, str):
                # Interpret as property type (use field name as column)
                fieldmap[k] = {"column": k, "type": v}
            elif isinstance(v, dict) and isinstance(v.get("type", None), str):
                # Convert type string to Notion type object if needed later
                pass  # We'll use .type in schema logic below
    props = {}
    if fieldmap:
        for k, v in fieldmap.items():
            notion_col = v["column"]
            t = v["type"]
            if t in type_map:
                props[notion_col] = type_map[t]
            else:  # Default to rich_text as Notion expects {}
                props[notion_col] = {"rich_text": {}}
    else:
        for k, val in sample_record.items():
            ntype = guess_notion_type(val)
            if ntype in type_map:
                props[k] = type_map[ntype]
            else:
                props[k] = {"rich_text": {}}
    if "Title" not in props:
        props["Title"] = {"title": {}}
    return props


def create_notion_database_from_records(
    records,
    parent_page_id,
    notion_token,
    db_title=None,
    with_template=True,
    template_markdown=None,
):
    # LLM NOTE: Notion API is strict. For "date" columns, always set "type": "date" and "date": {}. No fallback to text. If schema mismatches, Notion will reject data. Recreate DB if needed.
    """
    Creates a Notion database under the given parent page, infers columns from records,
    and attaches a page template (markdown) if desired.
    Returns the new database ID.
    """
    client = Client(auth=notion_token)
    if not db_title:
        db_title = (
            f"Guardian Codex {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    # Use fieldmap (if supplied) to define schema, else infer
    # LLM NOTE: Notion API is strict. For date columns, property must be type "date". No fallback to text.
    from pathlib import Path

    fieldmap = None
    if Path("my_fieldmap.json").exists():
        with open("my_fieldmap.json") as f:
            fieldmap = json.load(f)
    properties = build_notion_db_properties_from_fieldmap(fieldmap, records[0])
    print(
        f"\nDEBUG: Notion DB schema to be created:\n{json.dumps(properties, indent=2)}"
    )

    db_payload = {
        "parent": {"page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": db_title}}],
        "properties": properties,
    }

    # Optionally add a page template
    if with_template:
        if not template_markdown:
            template_markdown = (
                "# {{ Title }}\n"
                "{% for k, v in record.items() if k != 'Title' %}\n"
                "- **{{ k }}:** {{ v }}\n"
                "{% endfor %}"
            )
        # Render template with Jinja2 for demo
        # Attach as page content to every new entry
        # (Notion DB templates only support a fixed template—true per-row customization requires post-processing)
        blocks = markdown_to_notion_blocks(
            jinja2.Template(template_markdown).render(
                record=records[0], Title=records[0].get("Title", "Entry")
            )
        )
        template_block = {
            "name": [{"type": "text", "text": {"content": "Guardian Template"}}],
            "is_default": True,
            "template_id": "guardian-template",
            "children": flatten_notion_blocks(blocks),
        }
        db_payload["template"] = template_block

    db = client.databases.create(**db_payload)
    db_id = db["id"]
    print(f"Created Notion database '{db_title}' with ID: {db_id}")

    return db_id


if __name__ == "__main__":
    codexify_database_cli_wrapper()


def extract_fragments_from_entry(entry_path, fragments_path):
    """
    Scans a markdown Codex entry for notable lines and appends them to fragments.yaml.
    Lines starting with '>' or marked as key phrases will be extracted.
    """
    import yaml

    if not os.path.exists(entry_path):
        print(f"❌ Entry file not found: {entry_path}")
        return
    with open(entry_path) as f:
        lines = f.readlines()

    fragments = []
    for line in lines:
        line = line.strip()
        if line.startswith(">") or (
            len(line) > 20 and line[0].isupper() and line.endswith(".")
        ):
            result = {}
            result["properties"] = {}
            result["properties"]["Name"] = {"title": [{"text": {"content": line}}]}
            fragments.append(
                {
                    "content": line,
                    "source_entry": os.path.basename(entry_path).split(".")[0],
                    "tags": [],
                }
            )

    if not fragments:
        print("⚠️  No fragments found.")
        return

    if not os.path.exists(fragments_path):
        with open(fragments_path, "w") as f:
            yaml.dump([], f)

    with open(fragments_path) as f:
        existing = yaml.safe_load(f) or []

    existing.extend(fragments)

    with open(fragments_path, "w") as f:
        yaml.dump(existing, f, default_flow_style=False)

    print(f"✅ Extracted {len(fragments)} fragments to {fragments_path}")


# --- Codexify CLI Tool ---
def main():
    parser = argparse.ArgumentParser(description="Codexify CLI Tool")
    parser.add_argument(
        "--init", action="store_true", help="Initialize Codexify folder structure"
    )
    parser.add_argument("--new-entry", metavar="TITLE", help="Create a new Codex entry")
    parser.add_argument("--tags", nargs="*", default=[], help="Tags for the entry")
    parser.add_argument(
        "--extract-fragments",
        metavar="ENTRY",
        help="Extract fragments from an entry markdown file",
    )
    parser.add_argument("--path", default="./codexify", help="Target Codexify path")

    args = parser.parse_args()

    if args.init:
        ensure_structure(args.path)
        print(f"🌱 Codexify vault initialized at {args.path}")

    if args.new_entry:
        create_entry(args.path, args.new_entry, args.tags)

    if args.extract_fragments:
        extract_fragments_from_entry(
            args.extract_fragments, os.path.join(args.path, "fragments.yaml")
        )


def ensure_structure(root):
    import yaml

    dirs = ["entries", "foresight", "artifacts", "persons", "rituals"]
    for d in dirs:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    if not os.path.exists(os.path.join(root, "threads.yaml")):
        with open(os.path.join(root, "threads.yaml"), "w") as f:
            yaml.dump([], f)
    if not os.path.exists(os.path.join(root, "fragments.yaml")):
        with open(os.path.join(root, "fragments.yaml"), "w") as f:
            yaml.dump([], f)


def create_entry(root, title, tags):
    now = datetime.datetime.now()
    entry_id = f"PCX-EP{now.strftime('%j')}-{now.strftime('%H%M')}"
    filename = os.path.join(root, "entries", f"{entry_id}.md")
    content = f"""# Codex Entry: {entry_id}
**Title:** {title}
**Date:** {now.date()}
**Tags:** {', '.join(tags)}
**Linked Threads:** []
**Fragments:** []
**Artifacts:** []
**Content:**

Write your memory here.
"""
    with open(filename, "w") as f:
        f.write(content)
    print(f"✅ Entry created: {filename}")


if __name__ == "__main__":
    main()
