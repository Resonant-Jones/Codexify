You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: codexify:export-gdrive supports --file -

PATCH
***Begin Patch
*** Update File: guardian/cli/codexify_export_gdrive.py
@@
<-@click.option>("--file", "file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Path to JSON array or NDJSON of records.")
<+@click.option>("--file", "file_path", type=click.Path(exists=False, dir_okay=False, path_type=Path), help="Path to JSON array or NDJSON of records. Use '-' for STDIN.")
@@

- if file_path:
-            records = _load_records_from_file(file_path)

+ if file_path:
-        if str(file_path) == "-":
-            import sys
-            from io import TextIOWrapper
-            data = sys.stdin.read()
-            tmp = Path(".stdin_records.tmp.json")
-            tmp.write_text(data, encoding="utf-8")
-            records = _load_records_from_file(tmp)
-            tmp.unlink(missing_ok=True)
-        else:
-            if not file_path.exists():
-                raise click.ClickException(f"--file not found: {file_path}")
-            records = _load_records_from_file(file_path)

*** End Patch
