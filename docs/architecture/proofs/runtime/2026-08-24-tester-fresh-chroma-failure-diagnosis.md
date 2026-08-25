# Tester fresh Chroma failure diagnosis

## Result

**MATCHED — post-retirement Tester failure is the proven `chromadb==1.0.15`
fresh-state `PersistentClient` `InternalError` boundary.**

The recovery backend's original exception detail remains intentionally
safety-redacted. This diagnosis does not expose or reconstruct it. Instead,
the fresh partial state it left behind was fingerprinted without opening it,
copied to private disposable paths, and compared with an empty-store control in
the same canonical backend image. The control's first `PersistentClient` call
raised the typed Chroma `InternalError` and generated a state byte-identical to
the original partial evidence; its second independent call succeeded. A
disposable copy of the original partial state also reopened successfully and
completed collection creation.

This is a diagnostic classification only. It does not retry the Tester
backend, restore historical Chroma state, change implementation or logging, or
claim application health.

## Scope and authority

- **Starting recovery receipt:**
  `3fe63b4232f12fb305a50ac789311341d6587a9a`.
- **Diagnosis branch:** `codex/diagnose-tester-fresh-chroma-failure`, created
  directly at that receipt.
- **Audited main:**
  `022c9e07400ee1732932dd505e7d42e76ed11214`; `origin/main` did not move
  during this diagnosis.
- **Governing ADRs:** ADR-067 and ADR-069. Postgres remains canonical
  authority; Chroma remains derived retrieval state.
- **Historical preservation (metadata existence only):**
  `/Volumes/Dev_SSD/Codexify-preservation/chroma/20260824T182108Z-9f263fa2fdb9/canonical-chroma`.
  It remained present and read-only (`dr-xr-xr-x`) and was never mounted,
  opened, copied from, restored, or otherwise modified.

No source, test, Compose, dependency, configuration, provider, persistence,
or logging-policy file changed.

## Frozen evidence and quiescence

The post-recovery fresh partial path was:

`/Users/chriscastillo/.codex/worktrees/5ab6/Codexify-main/.chroma`

Before copying it, read-only Docker inspection found zero running containers
mounting that exact path. No Tester/backend container used the recovery
worktree for this diagnostic. No backend start, worker start, chat, model
inference, or retrieval operation occurred.

The original partial store was never opened with Chroma. Its bounded starting
fingerprint was:

| Property | Value |
| --- | --- |
| Files | 1 |
| Aggregate bytes | 16,384 |
| Relative path-plus-size manifest SHA-256 | `99eba9b649c76e6b2c7a0789ae9257a34b9bfc84c29dcd14c23d09eaf79b7f79` |
| `chroma.sqlite3` SHA-256 | `163ed995f24a76a53571f16c9f1e835271264a11136a25f5df854316ce14c58f` |

Two private copies, `partial-baseline` and `partial-working`, were made under
a mode-0700 temporary diagnostic root. Both had the exact same bounded
fingerprint before testing. A separate `fresh-control` directory was empty:
zero files, zero bytes, and the SHA-256 of an empty manifest.

After all diagnostic probes, the original fingerprint was recomputed and
matched every starting value exactly.

## Canonical runtime and read-only structural inspection

All Chroma probes used the recovery runtime image, not a host dependency:

| Property | Value |
| --- | --- |
| Image | `codexify-backend-runtime:latest` |
| Image digest | `sha256:af108ff65ba1d1fde1417ac776be41eacd106aaf77d2800b7c6e40d2359b6288` |
| Platform | `linux/arm64` |
| Python | `3.11.14` |
| `chromadb` | `1.0.15` |
| Chroma module | `/usr/local/lib/python3.11/site-packages/chromadb/__init__.py` |

The `partial-baseline/chroma.sqlite3` copy was opened only through SQLite
read-only mode. It reported `PRAGMA integrity_check = ok`, contained only the
`acquire_write` and `migrations` tables, had no migration rows, and had no
`collections` or `embeddings` table. No document, embedding, metadata, or
user data was queried or emitted.

This minimal state is distinct from the retired historical incompatible store,
whose recovery receipt recorded higher migration generations and the historical
Rust/SQLite panic. That panic was absent from the one authorized recovery
backend start and from every diagnostic probe here.

## Disposable partial-copy probe

Only `partial-working` was mounted read-write, and only into ephemeral,
network-isolated diagnostic containers.

1. `chromadb.PersistentClient(path=<partial-working>)` succeeded and
   `list_collections()` reported `0` collections.
2. A separate bounded collection discriminator on the same disposable copy
   successfully called
   `get_or_create_collection(name="codexify_vault_supported")`; the collection
   count then became `1`.

The original fresh partial store was not reopened. The result distinguishes
the startup boundary from later collection initialization: the partial
fresh-state can reopen and create the configured collection on a disposable
copy.

## Empty-control first and second calls

The same canonical runtime invoked only
`chromadb.PersistentClient(path=<fresh-control>)` against the independently
verified empty path.

### Attempt 1

The first call failed with the following bounded, non-content metadata:

| Property | Value |
| --- | --- |
| Result | failure |
| Exception module | `chromadb.errors` |
| Exception class | `InternalError` |
| Safe failure class | `chromadb_internal_error` |
| Message characters | 79 |
| Message SHA-256 | `ac1ae4eff9d26b913b75700048984924c50717932b1496bb8426f9f0e260a5f9` |
| Safe traceback locations | `__init__.py:PersistentClient:164`, `client.py:__init__:65`, `shared_system_client.py:__init__:19`, `shared_system_client.py:_create_system_if_not_exists:32`, `config.py:start:471`, `rust.py:start:112` |

No raw exception message was retained or committed.

That failing call created one 16,384-byte `chroma.sqlite3`. Its manifest
SHA-256 and SQLite-file SHA-256 exactly matched the frozen Tester partial
state above. Read-only inspection also matched: integrity `ok`, only
`acquire_write` and `migrations`, no migration rows, and no collections or
embeddings table.

### Attempt 2

Without deleting or changing the attempt-1 control state, a second independent
ephemeral container called `PersistentClient` once. It succeeded, and
`list_collections()` reported `0` collections.

## Classification basis and boundaries

The match criteria are all satisfied:

1. Empty fresh-control attempt 1 produced typed
   `chromadb.errors.InternalError`.
2. That call generated Chroma system state.
3. The separate fresh-control attempt 2 succeeded.
4. The post-recovery partial copy itself reopened successfully and proceeded
   through collection initialization.
5. Its structural metadata exactly matches the control state generated by the
   failing first call and is not the retired historical migration generation.
6. The historical Rust migration panic is absent.

Therefore the safety-redacted post-retirement backend exit is classified by
its exact resulting fresh-state fingerprint and the canonical runtime's
reproduction of that state as the known first-initialization Chroma boundary.
This does **not** establish backend health, authorize a backend retry, or
apply a recovery behavior.

## Preservation and cleanup

- The original fresh partial fingerprint was unchanged before versus after
  diagnosis.
- The historical preservation remained untouched.
- No Tester backend retry, worker, chat, model inference, Postgres mutation,
  historical restoration, dependency change, or repair occurred.
- `partial-baseline`, `partial-working`, `fresh-control`, and the temporary
  safe diagnostic helper were removed after evidence capture.

## Final disposition

`Tester post-retirement failure matched the proven fresh-Chroma initialization boundary — return to Axis for one bounded application of the already-proven fresh-state initialization recovery.`
