# Group Chat Module Merge Inspection

Base branch: `origin/main`
Feature branch: `origin/ZacContributions/group-chat-module`
Integration branch: `chore/resolve-group-chat-module-merge`

## Ahead commits

The feature branch currently contributes these commits ahead of `origin/main`:

1. `c8882e3e8` - `Record Zac Whooshd local setup proof`
2. `ef18a6542` - `fix(retrieval): namespace-aware search with dedup and project fallback`
3. `2b3a2c500` - `fix(completion): clean retrieval query, cap output tokens, add diagnostics`
4. `c235103cb` - `feat: webui-basic with group chat, @luna routing, and 2D atlas vector map`
5. `4634cb81f` - `feat: project scope picker — filters threads and atlas by project`

## Files changed by the feature branch

- `backend/rag/embedder.py`
- `config/supported_profiles/v1-local-core-web-mcp.yaml`
- `docker-compose.override.yml`
- `docs/guardian/setup-proofs/zac-whooshd-local-setup.md`
- `guardian/context/broker.py`
- `guardian/core/ai_router.py`
- `guardian/core/chat_completion_service.py`
- `guardian/guardian_api.py`
- `guardian/routes/atlas.py`
- `guardian/routes/chat.py`
- `guardian/runtime/embed/embedder.py`
- `webui-basic/index.html`

## Likely conflict hotspots with current `main`

These files are the highest-risk overlap points because they touch runtime routing, chat assembly, or app shell wiring that has likely moved on `main`:

- `guardian/core/chat_completion_service.py`
- `guardian/core/ai_router.py`
- `guardian/guardian_api.py`
- `guardian/routes/chat.py`
- `guardian/context/broker.py`
- `guardian/runtime/embed/embedder.py`
- `backend/rag/embedder.py`
- `webui-basic/index.html`

Lower-risk but still worth checking:

- `docker-compose.override.yml`
- `config/supported_profiles/v1-local-core-web-mcp.yaml`
- `guardian/routes/atlas.py`

## Changes worth preserving

- Group chat support in `guardian/routes/chat.py`
- `@luna` routing changes in the chat completion and router layers
- Atlas route and 2D vector-map support in `guardian/routes/atlas.py` and `webui-basic/index.html`
- Project-scope filtering in the web UI
- Namespace-aware retrieval deduplication and project fallback behavior
- Output-token capping and retrieval diagnostics in completion assembly

The proof artifact at `docs/guardian/setup-proofs/zac-whooshd-local-setup.md` is low-risk and should port cleanly if we preserve the feature history.
