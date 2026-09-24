# Imported-history worker store parity preflight — 2026-09-23

## Classification and proof boundary

**BLOCKED: shared-store isolation.** The temporary proof override now renders a `worker-chat` Chroma bind identical to the retained probe backend's bind, and no other resolved Compose setting changed. The corrected worker was **not** started. The physical source is also mounted by the running default `codexify` backend and document-embedding worker. A read-only census of its one `codexify_vault_supported` collection at `2026-09-23T18:11:03Z` found the two exact imported messages alongside ten other records. Attaching this probe's completion worker to that active, uncontrolled corpus would expose unrelated application data and could write derived state there. The task's isolation stop condition therefore takes precedence over replay.

This artifact proves the configuration defect and a static, minimal correction. It does **not** prove live worker/backend parity, worker selection, context assembly, provider injection, answer use, or persistence after correction. The preceding failed thread and assistant message remain the only executed provider-context attempt. There is no private-preview or release qualification claim.

## Evaluated source and topology

- Repository `/Volumes/Dev_SSD/Codexify-main`, clean `main` at `bccbe5a331ade57e8f6db5a59bc5e568d8dbaff7` before this artifact; `git merge-base --is-ancestor bccbe5a331ade57e8f6db5a59bc5e568d8dbaff7 HEAD` exited 0. Initial status: `## main...origin/main [ahead 4]`.
- Docker context: `desktop-linux`. Project: `codexify_account_import_ui_probe_20260923`. Docker labels on the retained worker give project directory `/Volumes/Dev_SSD/Codexify-main` and, in order, `/Volumes/Dev_SSD/Codexify-main/docker-compose.yml`, `/Volumes/Dev_SSD/Codexify-main/docker-compose.whooshd-smoke.yml`, `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml`, `/private/tmp/codexify-import-retrieval-probe-provider-20260923/compose.capture.override.yml`. The backend was created before the capture layer and its label lists the first three files. The capture layer only adds the existing outbound receipt hook to `worker-chat`.
- Both retained containers used `codexify-backend-runtime:latest`, image `sha256:f86d6720655406ac6943710e1fc3ea22b9d3d2b230a0c1ef999adfb71679d3f9`. The prior probe used the local Whoosh'd route, logical model `local-chat`, and streamed the request. No physical model inventory was refreshed because replay was blocked.
- The previous receipt does not state whether its original CLI used an explicit `--env-file`. The base Compose file resolves service `env_file` through `CODEXIFY_RUNTIME_ENV_FILE`, defaulting to `.env`; the current shell has no `CODEXIFY_RUNTIME_ENV_FILE`. For repeatable static rendering, this preflight explicitly used `--env-file /Volumes/Dev_SSD/Codexify-main/.env` and `--project-directory /Volumes/Dev_SSD/Codexify-main`. This establishes the evaluated render, not an unrecorded historical CLI argument. Full rendered JSON remains private under the temporary evidence directory because it includes environment values.

The responsible layer is the proof's file list: it omits `docker-compose.override.yml`, whose development `worker-chat` definition contains `./.chroma:/app/.chroma`. The base file already binds Chroma for `backend` and `worker-chat-embed` but not for `worker-chat`. The temporary override supplied no replacement Chroma bind. The separate `docker-compose.private-preview.yml` uses a shared named volume and is not part of this proof project; it was neither mounted nor edited. Adding the whole development override would also add unrelated mounts, so the proof override received one mount only.

## Preservation and store safety

The stopped original worker is `codexify_account_import_ui_probe_20260923-worker-chat-1`, container ID `2b0d6d75da41dc9165b1ce7d60615212ae034257d04936a499bb0ab471440acf`. Its container-local `/app/.chroma` was copied before any replacement to `/private/tmp/codexify-account-import-ui-staging-20260923/worker-store-parity/worker-local-chroma/`. The five-file SHA-256 manifest is `worker-store-parity/worker-local-manifest.sha256`. The copied SQLite database has one embedding in `codexify_vault_supported`. The original container and its local store remain retained; the copy was not mounted or merged into the host corpus.

The retained backend mount is a Docker `bind` from `/Volumes/Dev_SSD/Codexify-main/.chroma` to `/app/.chroma`. Its resolved Chroma path is `/app/.chroma`, backend `chroma`, collection `codexify_vault_supported`, local embedder, and `LOCAL_EMBED_MODEL=/models/bge-large-en-v1.5`. Before correction the worker had no Chroma mount, although its `/app` working directory and default vector settings resolved the same path, backend, and collection. The actual stopped worker's local directory contained one record; the host directory contained 12 at this preflight. Equal path strings were therefore insufficient.

Docker mount inspection found these known consumers of the host Chroma source: the stopped probe backend and `worker-chat-embed`, plus the **running** default project's `codexify-backend-1` and `codexify-worker-document-embed-1`. The private-preview containers instead reference `codexify_private_preview_chroma`, a distinct named volume. A read-only SQLite metadata census of the host collection found `local/chatgpt_import=2`, `local/api/embeddings=4`, `local/document=5`, and `local/builtin_help_asset=1`. The imported pair has source thread `axis-import-materialization-20260923-01`, source message IDs `axis-import-user-message-20260923-01` and `axis-import-assistant-message-20260923-01`, and vector metadata message IDs 1 and 2 respectively. Those metadata IDs corroborate the preceding canonical-source receipt; the stopped PostgreSQL service was not restarted for a new canonical readback. No message body was printed.

This census establishes unrelated application records in the same collection and an active external consumer of the same physical bind. It does not establish isolation merely because every vector row currently reports owner `local`. The safety decision was to stop before activating the corrected worker, without stopping the default project or moving, cloning, retiring, or rebuilding either store.

## Static correction and validation

The only temporary edit was to `/private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml`:

```yaml
  worker-chat:
    volumes:
      - /Volumes/Dev_SSD/Codexify-main/.chroma:/app/.chroma
```

For both renders the Bash Compose prefix was:

```bash
DC=(docker compose --env-file /Volumes/Dev_SSD/Codexify-main/.env \
  --project-directory /Volumes/Dev_SSD/Codexify-main \
  -p codexify_account_import_ui_probe_20260923 \
  -f /Volumes/Dev_SSD/Codexify-main/docker-compose.yml \
  -f /Volumes/Dev_SSD/Codexify-main/docker-compose.whooshd-smoke.yml \
  -f /private/tmp/codexify-account-import-ui-staging-20260923/compose.override.yml \
  -f /private/tmp/codexify-import-retrieval-probe-provider-20260923/compose.capture.override.yml)
"${DC[@]}" config --quiet
"${DC[@]}" config --format json > /private/tmp/codexify-account-import-ui-staging-20260923/worker-store-parity/compose-before.private.json
```

After the override edit, the same `DC` array was used with `"${DC[@]}" config --quiet` and `"${DC[@]}" config --format json > /private/tmp/codexify-account-import-ui-staging-20260923/worker-store-parity/compose-after.private.json`. Both `config --quiet` runs passed. A structured JSON comparison removed only the new `/app/.chroma` worker volume from the after render and then compared the complete render with the before render: equality was `true`. The after render assigns both backend and worker the same `bind` source `/Volumes/Dev_SSD/Codexify-main/.chroma` and target `/app/.chroma`. Their rendered `LOCAL_EMBED_MODEL` values agree. The worker's vector backend, path, and collection remain the runtime defaults (`chroma`, resolved `/app/.chroma`, `codexify_vault_supported`); the backend sets the same values explicitly. All unrelated service settings, mounts, auth, provider, queue, concurrency, and source mounts compare equal. No repository Compose file was edited.

The decisive equality expression was:

```bash
jq -n \
  --slurpfile b /private/tmp/codexify-account-import-ui-staging-20260923/worker-store-parity/compose-before.private.json \
  --slurpfile a /private/tmp/codexify-account-import-ui-staging-20260923/worker-store-parity/compose-after.private.json \
  '($a[0].services["worker-chat"].volumes | map(select(.target != "/app/.chroma"))) as $v |
   ($a[0] | .services["worker-chat"].volumes = $v) == $b[0]'
```

It returned `true`. The private JSON files have mode `0600`.

Read-only checks used `docker context show`, filtered `docker inspect` labels/mounts, `docker ps -a`, and `sqlite3 'file:/Volumes/Dev_SSD/Codexify-main/.chroma/chroma.sqlite3?mode=ro'` against collection and metadata tables. Preservation used `docker cp codexify_account_import_ui_probe_20260923-worker-chat-1:/app/.chroma .../worker-local-chroma` and `find ... -type f -exec shasum -a 256 {} \;` to write the manifest. These commands passed. The before/after rendered configuration was stored privately and only the allowlisted vector/mount comparison is reported here.

## Replay boundaries and next prerequisite

No service-context vector readback or fresh native-thread completion was attempted. Consequently there are no new thread, user-message, request, task, turn, attempt, or assistant-message IDs. There is no executed worker retrieval trace, assembled context, provider payload, answer, or durable readback from this correction. A missing provider capture is an evidence gap, not an injection failure. The last proven-good boundary is static Compose agreement on the intended mount and vector settings; the first blocked boundary is safe worker activation against a physically shared corpus.

The first corrective prerequisite is an explicitly controlled, isolated probe vector backing store that preserves the canonical imported records without copying active vectors or attaching a writer to the default project's host corpus. Defining or migrating such a store is outside this task. After that separately authorized isolation decision, the exact canonical source, both service environments, and actual request capture must be revalidated before one replay. No retrieval or provider policy change is implied.

All retained probe services were stopped at closeout; this task started and stopped none. The original worker container, project volumes, shared host store, and diagnostic preservation copy remain. No import, embedding enqueue, backfill, vector seeding, source-message edit, or private-preview mutation occurred. The preceding failed thread and assistant message remain intact. No production code tests apply to this proof-runtime configuration-only correction; the required live replay was blocked by the stated safety gate.

**ADR impact:** aligned with ADR-067's canonical PostgreSQL/derived Chroma distinction and ADR-081's account/Project authority; no amendment. **Documentation follow-through:** this proof only. **Current-state and release claims:** unchanged. A repository-wide Compose correction is deferred and would need to distinguish the base file, development override, and private-preview overlay rather than treating them as one deployment topology.
