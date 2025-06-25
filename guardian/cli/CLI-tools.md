# 🛠️ Guardian CLI Tools

This page documents the various CLI tools included with Guardian. These tools provide command-line access to key functionality including chat history, companion identity management, memory logging, Codex manipulation, and sovereign routing.

---

## 🧠 Chat History and Summarization

```bash
python -m guardian.cli.main chat-history --session-id YOUR_SESSION
python -m guardian.cli.main summarize-chat --session-id YOUR_SESSION
```

---

## 🧍‍♂️ Companion Identity Tools

### Basic Switcher

```bash
# Create a new companion
python character_switcher.py Velum --create

# Switch to an existing one
python character_switcher.py Gregorios
```

### Full Switcher

```bash
# Create a new companion
python character_switcher_full.py Gregorios --create

# Switch to an existing one
python character_switcher_full.py Velum

# List all companions
python character_switcher_full.py --list

# Delete a companion
python character_switcher_full.py Gregorios --delete
```

---

## 🌀 Terminal UI (TUI)

Launch the interactive companion manager:

```bash
python character_tui.py
```

### Features

- View and select active companions
- Create from Imprint Zero
- Delete with one keystroke
- Curses-based arrow navigation
- Keyboard-only workflow

---

## 💾 Backup Companions

Backup all companions to a dated `.zip` file:

```bash
python character_switcher.py --backup
```

Optional custom destination:

```bash
python character_switcher.py --backup /Users/yourname/Desktop/my_backup
```

(`.zip` extension is appended automatically.)

---

## 🧭 Codexify: Memory Engine

```bash
# Initialize the Codex folder structure
python codexify.py init --path ./my_codex

# Create a new entry
python codexify.py --new-entry --title "Guardian Memory Ritual" --tags guardian ritual

# Extract semantic fragments
python codexify.py --extract-fragments ./codexify/entries/PCX-EP001.md --path ./codexify

# Create a Notion DB from JSON
python codexify.py create --records my_records.json --fieldmap standard_fieldmap.json --aliasmap standard_alias.json

# Export a Notion DB to JSON
python codexify.py export

# Import a Notion DB into Guardian’s SQLite
python codexify.py import-notion
```

### Features

- Structured folder creation
- Auto-generated `.md` entries
- Semantic fragments exported to `fragments.yaml`

### Fragment Extraction Logic

Looks for:

- Quoted lines (`>`)
- Heuristic insights (≥ 20 chars, capitalized start, ending period)

Example output in `fragments.yaml`:

```yaml
- content: "Pain is simply a signal for change."
  source_entry: PCX-EP001
  tags: []
```

### Advanced Options

- `--records <json>`: Specify the record file (e.g., exported from Notion)
- `--fieldmap <json>`: Map Notion fields to internal structure
- `--aliasmap <json>`: Handle aliases or alternate naming
- `--parent-id <id>`: Set Notion parent ID
- `--parent-title <name>`: Override the Notion parent title
- `--seed`: Populate a Notion database from local records
- `--edit-aliases`: Launch alias editing mode

---

## ☁️ Export/Import: Google Drive & iCloud

```bash
# Export Guardian data to Google Drive
python guardian_cli.py export_gdrive

# Import Guardian data from Google Drive
python guardian_cli.py import_gdrive

# Import Guardian data from iCloud
python guardian_cli.py import_icloud
```

---

## 🔬 Notion Export Tests

```bash
# Run test for Notion export pipeline
python -m tests.test_export_notion
```

This validates end-to-end export from Guardian into Notion. Make sure `my_records.json` is in the correct location.

---

## 🧙‍♂️ Ritual CLI

```bash
# Seed Notion DB with records and mappings
python ritual_cli.py seed-notion
```

This is a companion initialization tool to scaffold Notion entries during ritual setup.

---

## 🛰️ Sovereign Routing Toggles

Use hybrid or cloud-only agents with warnings:

```bash
python -m guardian.cli.main --cloud-only history
python -m guardian.cli.main --hybrid log "This is hybrid!"
```

`HybridRouter` will handle the routing transparently.

---

## 🔧 Configuration Tools

Inspect and modify Guardian’s active backend settings:

### Show Active Configuration

```bash
guardian config-status
```

- Displays current backend, models, and API routing flags.
- Warns about missing API keys.

### Set Active Backend

```bash
guardian set-backend ollama
```

- Updates the `AI_BACKEND` value in your `.env` file.
- Options: `ollama`, `openai`, `gemini`, `nebius`, `groq`
---

## ✅ Summary

You now have:

- Full CLI access to companion management
- Codex memory entry and fragment tools
- TUI interface
- Sovereign model routing
- Backup utilities

The command-line is now your wand. Use it with intent.
