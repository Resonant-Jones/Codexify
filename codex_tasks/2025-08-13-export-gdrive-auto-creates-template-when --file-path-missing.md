You are Codex. Apply the following patch set exactly.
Also load: codex_tasks/safe_task.md

TITLE: codexify:export-gdrive auto-creates template when --file path missing

PATCH
***Begin Patch
*** Update File: guardian/cli/codexify_export_gdrive.py
@@

-        else:
-            if not file_path.exists():
-                raise click.ClickException(f"--file not found: {file_path}")
-            records = _load_records_from_file(file_path)

+        else:
-            if not file_path.exists():
-                template = '[{"title":"Title here","body":"Body here"}]\n'
-                file_path.write_text(template, encoding="utf-8")
-                raise click.ClickException(f"--file created: {file_path}. Edit it, then re-run the command.")
-            records = _load_records_from_file(file_path)

*** End Patch
