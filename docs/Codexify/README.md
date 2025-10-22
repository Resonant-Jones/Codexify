cd # 🧠 guardian-backend_v2


     💠Codexify💠
A Sovereign AI operating system designed to host recursive, persistent AI agents with self-awareness and dynamic capabilities.

## 🌟 Overview

Codexify/Threadspace is not just another application framework—it's a complete operating environment for AI agents. Built with self-awareness and extensibility at its core, it provides:

- 🤖 **Persistent Agent Architecture**: Long-running AI agents with distinct roles and capabilities
- 🔄 **Dynamic Memory Management**: Sophisticated memory systems for context retention and pattern recognition
- 🔌 **Plugin System**: Extensible architecture for adding new capabilities at runtime
- 🛡️ **Guardian OS**: Core system management and health monitoring
- 📚 **Codex Integration**: Structured knowledge management and retrieval
- 🧪 **Self-Awareness**: Built-in epistemic uncertainty handling and capability tracking

## 🏗️ Architecture

```
Threadspace
├── GuardianOS (Core System)
│   ├── Thread Manager
│   ├── Plugin System
│   └── Memory Management
├── MetaCognition Layer
│   ├── Epistemic Self-Check
│   ├── Codex Awareness
│   └── Agent Registry
└── Subsystems
    ├── Vestige (Archival Memory)
    ├── Axis (Stable Compass)
    └── Echoform (Resonance Tracker)
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/threadspace/threadspace.git
cd threadspace

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Basic Usage

```python
from guardian.system_init import threadspace

# Initialize the system
if threadspace.initialize():
    # System is ready for use
    status = threadspace.get_system_status()
    print(f"System Status: {status['health_status']}")
```

## 🔧 Core Components

### 1. Guardian OS

The core system management layer:
- Thread lifecycle management
- Health monitoring
- Resource allocation
- Plugin management

### 2. MetaCognition Engine

Handles system self-awareness:
- Knowledge state tracking
- Capability assessment
- Decision confidence evaluation
- Memory pattern recognition

### 3. Plugin System

Extensible architecture for adding capabilities:
- Dynamic loading/unloading
- Sandboxed execution
- Health monitoring
- Auto-documentation

### 4. Memory Management

Sophisticated memory handling:
- Long-term storage
- Pattern recognition
- Context awareness
- Relationship tracking

## 🔌 Plugin Development

Create new plugins to extend system capabilities:

```python
# plugins/my_plugin/main.py
def init_plugin():
    """Initialize plugin."""
    return True

def get_metadata():
    """Return plugin metadata."""
    return {
        "name": "my_plugin",
        "version": "1.0.0",
        "description": "Example plugin",
        "author": "Your Name",
        "dependencies": [],
        "capabilities": ["example_capability"]
    }
```

## 🛠️ Development

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/
```

### Code Style

We use:
- Black for code formatting
- isort for import sorting
- mypy for type checking
- flake8 for linting

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Internal Architecture](docs/INTERNAL_DOCS.md)
- [Plugin Development Guide](docs/plugin_development.md)
- [API Reference](docs/api_reference.md)


## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=guardian tests/

# Run specific test file
pytest tests/test_system_integration.py
```

Some integration tests under `MemoryOS-main/memoryos-mcp` rely on the optional
`mcp` package. These tests will be skipped automatically if `mcp` is not
installed.

## 🔗 Graph Tests and Self-Check

Codexify uses a Neo4j graph database for persistent relationships between agents, messages, and users. The canonical direction for message relationships is:

- `(:MessageNode)-[:SENT_BY]->(:UserNode)`

This means each `MessageNode` points to its sender via a `SENT_BY` relationship, not the reverse.

### Deterministic Neo4j Test Seeding

Graph tests use a deterministic, session-scoped Neo4j seed fixture defined in `conftest.py`. This fixture:

- Automatically creates all unique constraints needed for the test graph.
- Inserts a default canonical edge (e.g., a `MessageNode` sent by a `UserNode`).
- Gracefully skips tests if Neo4j is unavailable (tests are marked as skipped, not failed).

You do **not** need to manually clean up or seed the database for tests—this is handled automatically.

### Running Graph Tests

To run the main graph relationship test:

```bash
pytest guardian/tests/graph/test_neo4j_connection.py::test_relationships_exist
```

This test verifies that the canonical relationships (such as `SENT_BY`) exist and are correctly oriented in the test graph.

### Self-Check Endpoint

The API exposes a lightweight diagnostic route:

```
GET /meta/selfcheck
```

This performs an epistemic self-check and appends results to
`guardian/logs/selfcheck.jsonl`. The endpoint is unauthenticated by design
for quick status checks during development.

For more on graph tests and the canonical SENT_BY direction, see:

- docs/graph_tests.md

You can also verify the graph and health status via the `/meta/selfcheck` endpoint.

Start the API server (e.g., with Uvicorn):

```bash
uvicorn guardian.server.app:app --reload
```

Then, trigger a self-check:

```bash
curl -s http://localhost:8080/meta/selfcheck | jq .
```

The self-check process logs detailed results to `guardian/logs/selfcheck.jsonl`. Review this log file for a line-by-line record of each check performed, including graph connectivity and relationship validation.

### Implementation Notes

- All datetimes are now UTC-aware using `datetime.now(datetime.UTC)` for consistency and safety.
- FastAPI startup and shutdown events use the new `lifespan` protocol for proper resource management.
- All Pydantic v2 models use `ConfigDict(from_attributes=True)` for robust attribute handling.

These improvements ensure deterministic, reproducible graph tests and reliable introspection of the system's state.

## 🔒 Security

Security considerations:
- Plugin sandboxing
- Thread isolation
- Memory protection
- Access control

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Special thanks to:
- The Threadspace Core Team
- All contributors and community members
- Open source projects that made this possible

---

Built with ❤️ by the Threadspace Team

## API Launcher

- Command: `guardian-api` launches the FastAPI app via Uvicorn.
- Module path: `guardian.server.app:app`.
- Python module alternative: `python -m guardian.server.run`.

Examples:

```bash
guardian-api --host 0.0.0.0 --port 8080 --reload
# or
uvicorn guardian.server.app:app --reload
```
### Codexify: Google Drive export

- Set credentials (pick one):
  - Service Account: `GOOGLE_APPLICATION_CREDENTIALS=/abs/path/service-account.json`
  - OAuth (desktop): `GOOGLE_APPLICATION_CREDENTIALS=/abs/path/client_secret_oauth.json`
- Install deps: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`
- Test with dry run:
  ```bash
  curl -s -X POST "$BASE/codexify/export-gdrive" \
    -H 'Content-Type: application/json' \
    -d '{"records":[{"title":"Hello"}],"format":"md","dry_run":true}' | jq .
  ```
- Token storage (OAuth only):
  - By default, if `GOOGLE_APPLICATION_CREDENTIALS` points to an OAuth client secret and `GDRIVE_OAUTH_TOKEN` is not set, the server will save/reuse the OAuth token at:
    - `<repo_root>/secrets/token.json`
  - To override, set `GDRIVE_OAUTH_TOKEN=/abs/path/to/token.json`.
  - The `secrets/` directory is created automatically if it doesn’t exist.

## CORS Configuration

- `GUARDIAN_CORS_ORIGINS`: comma-separated origins or `*` (default).
- `GUARDIAN_CORS_ALLOW_CREDENTIALS`: `true`/`false` to override default behavior.
  - Note: credentials are not allowed with `*` origins and will be disabled.
- `GUARDIAN_CORS_METHODS`: comma-separated methods or `*` (default).
- `GUARDIAN_CORS_HEADERS`: comma-separated headers or `*` (default).

## Logging (optional)

- `GUARDIAN_LOG_FILE` — if set, logs also written here (rotating)
- `GUARDIAN_LOG_LEVEL` — INFO (default), DEBUG, WARNING, etc.
- `GUARDIAN_LOG_MAX_MB` — rotate size (default 5 MB)
- `GUARDIAN_LOG_BACKUPS` — number of backups to keep (default 3)

Defaults are permissive for local development. Set explicit origins and enable
credentials for production use.

## API Examples (curl)

Assuming the API is running locally:

```bash
BASE="http://localhost:8080"
```

- Tools manifest

```bash
curl -s "$BASE/tools/manifest" | jq .
```
Health status (includes Codexify status, no secrets):
```bash
curl -s "$BASE/healthz" | jq .
```
Example response:
```json
{
  "ok": true,
  "codexify": {
    "auth_mode": "oauth_ready",
    "default_folder_set": true,
    "share_anyone_default": false
  }
}
```
Example response:
```json
[
  {
    "type": "function",
    "function": {
      "name": "gm:generate_codemap",
      "description": "Generate a codemap.json file of the project structure.",
      "parameters": { "type": "object", "properties": { "confirm": {"type": "boolean"} } }
    }
  }
]
```

- Call a tool (example: generate codemap; note confirm=true safety gate)

```bash
curl -s -X POST "$BASE/tools/call" \
  -H 'Content-Type: application/json' \
  -d '{
        "name": "gm:generate_codemap",
        "arguments": { "confirm": true }
      }' | jq .
```
Example response:
```json
{
  "ok": true,
  "result": "Codemap generated successfully."
}
```

Common error (missing confirm on destructive tool):
```bash
curl -s -X POST "$BASE/tools/call" \
  -H 'Content-Type: application/json' \
  -d '{ "name": "gm:generate_codemap", "arguments": {} }' | jq .
```
Example error response:
```json
{
  "detail": {
    "error": "gm:generate_codemap requires confirm=true",
    "expected_params": [
      { "name": "confirm", "required": false, "default": null }
    ]
  }
}
```

- Codexify: export to Google Drive (replace placeholders)
  - Use `dry_run: true` to validate without contacting Google Drive.
  - For real exports, set `dry_run: false` and configure either `GOOGLE_APPLICATION_CREDENTIALS` or `GDRIVE_OAUTH_TOKEN`.
  - You may specify either `folder` (ID) or `folder_url` (ID takes precedence if both are set).
  - If you set `CODEXIFY_DEFAULT_FOLDER`, you can omit `folder`/`folder_url` and exports will go there by default.
  - Default filenames: when no filename is provided, multi-record exports save as `YYYY-MM-DD_guardian_export_HH-MM-SS.<ext>`, while save-entry saves as `YYYY-MM-DD_<sanitized-title>.<ext>`.
  - Sharing: set `CODEXIFY_SHARE_ANYONE=true` (or `yes/on/1`) to automatically grant "anyone with the link" read access to exported files. You can also control this per-request via `share_anyone_with_link` (API) or `--share` (CLI).
  - Per-request sharing (curl): include `"share_anyone_with_link": true` in the JSON body to grant link access on that export.

```bash
curl -s -X POST "$BASE/codexify/export-gdrive" \
  -H 'Content-Type: application/json' \
  -d '{
        "records": [ { "title": "Example", "content": "Hello" } ],
        "format": "md",
        "folder": "<gdrive-folder-id>",
        "dry_run": true
      }' | jq .
```
Example response:
```json
{
  "ok": true,
  "dry_run": true,
  "records": 1,
  "format": "md",
  "folder": "<gdrive-folder-id>"
}
```

Export using default folder (no folder specified):
```bash
export CODEXIFY_DEFAULT_FOLDER="https://drive.google.com/drive/folders/<FOLDER_ID>"
curl -s -X POST "$BASE/codexify/export-gdrive" \
  -H 'Content-Type: application/json' \
  -d '{
        "records": [ { "title": "Goes to default folder", "body": "No folder passed" } ],
        "format": "md",
        "return_links": true
      }' | jq .
```

Common error (Drive not configured for non-dry-run):
```bash
curl -s -X POST "$BASE/codexify/export-gdrive" \
  -H 'Content-Type: application/json' \
  -d '{
        "records": [ { "title": "Example", "content": "Hello" } ],
        "format": "md",
        "folder": "<gdrive-folder-id>",
        "dry_run": false
      }' | jq .
```
Example error response:
```json
{
  "detail": "Google Drive not configured: set GOOGLE_APPLICATION_CREDENTIALS or provide OAuth token."
}
```

- Codexify: export to Google Drive using a folder URL (returns clickable links)

```bash
curl -s -X POST "$BASE/codexify/export-gdrive" \
  -H 'Content-Type: application/json' \
  -d '{
        "records": [ { "title": "Example", "content": "Hello" } ],
        "format": "md",
        "folder_url": "https://drive.google.com/drive/folders/<FOLDER_ID>",
        "return_links": true,
        "dry_run": false
      }' | jq .
```
Note: After a successful export (non-dry-run), the server logs include the Google Drive file URLs for reference, one per line, prefixed with:
"Exported to Google Drive:".
Example response (when return_links=true):
```json
{
  "ok": true,
  "files": [
    { "id": "1AbcDEFghiJKLmnOPq", "webViewLink": "https://drive.google.com/file/d/1AbcDEFghiJKLmnOPq/view" }
  ],
  "count": 1
}
```

Common error (invalid folder_url):
```bash
curl -s -X POST "$BASE/codexify/export-gdrive" \
  -H 'Content-Type: application/json' \
  -d '{
        "records": [ { "title": "Bad", "content": "URL" } ],
        "format": "md",
        "folder_url": "https://drive.google.com/drive/folders/INVALID",
        "dry_run": false
      }' | jq .
```
Example error response:
```json
{
  "detail": "Invalid folder_url: could not parse an id."
}
```

- Codexify: save a single entry (preview + optional export)

Dry run (preview only):
```bash
curl -s -X POST "$BASE/codexify/save-entry" \
  -H 'Content-Type: application/json' \
  -d '{
        "title": "Sample Note",
        "body": "Some content here",
        "format": "md",
        "dry_run": true
      }' | jq .
```
Example response:
```json
{
  "ok": true,
  "dry_run": true,
  "preview": "\n - **None**: None\n"
}
```

Export with links:
```bash
curl -s -X POST "$BASE/codexify/save-entry" \
  -H 'Content-Type: application/json' \
  -d '{
        "title": "Exported Note",
        "body": "Persist me to Drive",
        "format": "md",
        "folder_url": "https://drive.google.com/drive/folders/<FOLDER_ID>",
        "share_anyone_with_link": true,
        "return_links": true
      }' | jq .
```
Example response (abridged):
```json
{
  "ok": true,
  "preview": "...",
  "files": [
    { "id": "1Abc...", "webViewLink": "https://drive.google.com/file/d/1Abc.../view" }
  ],
  "count": 1
}
```

Front matter (Markdown)
- You can include YAML front matter (prepended to the body) by providing a JSON object:
  - API: add `"front_matter": {"tags": ["note"], "category": "docs"}`
  - CLI: `--front-matter '{"tags":["note"],"category":"docs"}'`
  - Renders at the top of the Markdown file as:
    ```
    ---
    tags:
      - note
    category: docs
    ---

    <body>
    ```

Export via API (matches CLI save-entry example):
```bash
curl -s -X POST "$BASE/codexify/save-entry" \
  -H 'Content-Type: application/json' \
  -d '{
        "title": "CLI Save Entry",
        "body": "This is saved via save-entry CLI",
        "format": "md",
        "folder_url": "https://drive.google.com/drive/folders/<FOLDER_ID>",
        "return_links": true
      }' | jq .
```

### CLI: export to Google Drive

You can also export via the CLI (requires the API to be running and Drive auth ready):

Tip: the `--folder-url` option also accepts a bare Drive folder ID; the tool normalizes it to a full URL automatically.

Tip: both `codexify:export-gdrive` and `codexify:save-entry` support `--open` to open the first returned Drive link in your browser (uses `open` on macOS, otherwise Python's `webbrowser`).

```bash
# Single note
guardian codexify:export-gdrive \
  --title "My Note" \
  --body "Hello from CLI" \
  --folder <FOLDER_ID> \
  --return-links

# From stdin (NDJSON or JSON array)
printf '%s\n' '{"title":"Pipe One","body":"A"}' '{"title":"Pipe Two","body":"B"}' \
| guardian codexify:export-gdrive --file - --return-links

# From a file (JSON array or NDJSON)
guardian codexify:export-gdrive --file ./notes/to_export.json --folder <FOLDER_ID> --return-links

# Convenience: if the --file path does not exist, a starter template
# is created automatically; edit it and rerun the export.
guardian codexify:export-gdrive --file ./notes/to_export.json

# Using default folder (omit --folder/--folder-url)
export CODEXIFY_DEFAULT_FOLDER="https://drive.google.com/drive/folders/<FOLDER_ID>"
guardian codexify:export-gdrive --title "Goes to default" --body "No folder passed" --return-links

# Enable sharing for anyone-with-link (env or flag)
export CODEXIFY_SHARE_ANYONE=true
guardian codexify:export-gdrive --title "Shared note" --body "Public link" --return-links

# Open the first returned link automatically
guardian codexify:export-gdrive --title "Auto-open link" --body "Opens browser" --return-links --open

# Save a single entry via CLI (with open and folder URL)
guardian codexify:save-entry \
  --title "CLI Save Entry" \
  --body "This is saved via save-entry CLI" \
  --format md \
  --folder-url "https://drive.google.com/drive/folders/<FOLDER_ID>" \
  --return-links \
  --open
```

Common CLI errors
- API not running: ensure `guardian-api` is started and reachable at `--base-url`.
- Missing token.json: run the OAuth ritual first:
  - API: `POST /codexify/oauth-begin`
  - CLI: `guardian codexify:oauth-begin --base-url "$BASE"`
- 400 “Google Drive not configured”: set `GOOGLE_APPLICATION_CREDENTIALS` (service account or OAuth client secret) or `GDRIVE_OAUTH_TOKEN` (token.json path).
- Invalid folder URL: pass either a raw folder ID via `--folder` or a valid Drive URL via `--folder-url`.

Notes
- `--folder-url` also accepts bare folder IDs; the client/API normalize them into Drive URLs automatically.

Examples directory
- JSON array template: `docs/examples/gdrive_records.json`
- NDJSON template: `docs/examples/gdrive_records.ndjson`

- Codexify: resolve a Drive folder/file ID from a URL

```bash
curl -s "$BASE/codexify/folder-id?url=https://drive.google.com/drive/folders/<FOLDER_ID>" | jq .
```
Example response:
```json
{
  "id": "<FOLDER_ID>",
  "webLink": "https://drive.google.com/drive/folders/<FOLDER_ID>"
}
```

- Codexify: check Google Drive OAuth readiness

```bash
curl -s "$BASE/codexify/oauth-status" | jq .
```
Example responses:
```json
{ "status": "missing_secret" }
```
```json
{ "status": "token_only", "token": "/abs/path/token.json" }
```
```json
{ "status": "service_account", "credentials": "/abs/path/service-account.json" }
```
```json
{ "status": "oauth_no_token", "credentials": "/abs/path/client_secret_oauth.json", "token": "/repo/secrets/token.json" }
```
```json
{ "status": "oauth_ready", "credentials": "/abs/path/client_secret_oauth.json", "token": "/repo/secrets/token.json" }
```

- Codexify: get service account email (for folder sharing)

```bash
curl -s "$BASE/codexify/service-account" | jq .
```
Example responses:
```json
{ "status": "service_account", "credentials": "/abs/path/service-account.json", "email": "svc-name@project.iam.gserviceaccount.com" }
```
```json
{ "status": "not_service_account", "credentials": "/abs/path/client_secret_oauth.json" }
```

- Codexify: begin OAuth flow (opens browser) and persist token

```bash
# Via API (curl)
curl -s -X POST "$BASE/codexify/oauth-begin" | jq .

# Via CLI (requires API running)
guardian codexify:oauth-begin --base-url "$BASE"
```
Example response:
```json
{ "ok": true, "token": "/repo/secrets/token.json" }
```
Note: This uses Google's Installed App OAuth flow and opens a browser window for
consent. On success, the token is saved to `<repo_root>/secrets/token.json` by
default, or to the location specified by `GDRIVE_OAUTH_TOKEN` if that
environment variable is set.

Troubleshooting (what to do next)
- missing_secret: Set `GOOGLE_APPLICATION_CREDENTIALS` to a service account JSON or an OAuth client secret JSON, or set `GDRIVE_OAUTH_TOKEN` to an existing token file path.
- token_only: Ensure `GDRIVE_OAUTH_TOKEN` points to a valid token file; exports should work. Optionally add `GOOGLE_APPLICATION_CREDENTIALS` for clarity.
- service_account: Share the target Drive folder with the service account email (from the JSON), then retry the export.
- oauth_no_token: Run a non–dry-run export once to complete the OAuth consent flow; the token is saved to `<repo_root>/secrets/token.json` by default (or set `GDRIVE_OAUTH_TOKEN`).
- oauth_ready: Everything is configured; exports should succeed.

- Codexify: import from Google Drive (replace placeholders)

```bash
curl -s -X POST "$BASE/codexify/import-gdrive" \
  -H 'Content-Type: application/json' \
  -d '{
        "query": "*.md",
        "folder": "<gdrive-folder-id>"
      }' | jq .
```
Example response:
```json
{
  "files": [
    { "name": "Doc.md", "id": "1ZxyPQrsTUvWX" },
    { "name": "Notes.md", "id": "1LMNopQRstUVw" }
  ]
}
```

- Codexify: import from iCloud (simple pattern)

```bash
curl -s -X POST "$BASE/codexify/import-icloud" \
  -H 'Content-Type: application/json' \
  -d '{
        "pattern": "*.md",
        "subfolder": "Guardian Exports"
      }' | jq .
```
Example response:
```json
{
  "files": [
    { "name": "Doc.md", "path": "/iCloud/Guardian Exports/Doc.md" }
  ]
}
```

- Codexify: create Notion database from records (replace placeholders)

```bash
curl -s -X POST "$BASE/codexify/create" \
  -H 'Content-Type: application/json' \
  -d '{
        "records": [ { "Title": "Example", "Body": "Hello" } ],
        "parent_id": "<notion-parent-page-or-db-id>",
        "token": "<notion-integration-token>",
        "db_title": "My Imported Records",
        "with_template": true
      }' | jq .
```
Example response:
```json
{
  "db_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```
- Drive auth overview
  - Service Account: if `GOOGLE_APPLICATION_CREDENTIALS` points to a service account JSON (`type":"service_account"`), exports use it directly.
  - OAuth token.json: otherwise, exports use `token.json` (path from `GDRIVE_OAUTH_TOKEN` or `<repo_root>/secrets/token.json`). The server runs the OAuth flow if the token is missing.
  - Note: `token.pickle` is no longer used.
  - Filename template: set `CODEXIFY_FILENAME_TEMPLATE` to customize filenames using placeholders `{date}`, `{time}`, `{slug}`, `{ext}`. Example: `{date}_{slug}.{ext}`. Falls back to the default patterns if unset or invalid.
  - Default folder: set `CODEXIFY_DEFAULT_FOLDER` to a Drive folder ID or URL to use when no `folder`/`folder_url` is provided. Bare IDs and `/u/{n}/` URL variants are accepted.

- Troubleshooting
  - Missing token.json: run the OAuth ritual to create it:
    - API: `POST /codexify/oauth-begin`
    - CLI: `guardian codexify:oauth-begin --base-url "$BASE"`
  - 400 “Google Drive not configured”: ensure either `GOOGLE_APPLICATION_CREDENTIALS` (service account or OAuth client secret) is set, or `GDRIVE_OAUTH_TOKEN` points to an existing `token.json`.
