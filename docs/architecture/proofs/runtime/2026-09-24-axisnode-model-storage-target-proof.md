# AxisNode Model Storage Target Proof

Date: 2026-09-24
Tracking: Codexify #815 (parent #813)
Classification: `MODEL_STORAGE_RECONCILIATION_REQUIRED`

## Evidence and repository boundary

The operator supplied an ordinary AxisNode macOS Host Terminal transcript for
the read-only storage checks in this task. The terminal prompt identifies
`AxisNode`, and `diskutil` returned a host disk inventory. Codex did not run
these commands in its managed shell. The transcript is the evidence for the
host-storage classification; the preceding
[model-asset receipt](2026-09-24-axisnode-gemma4-12b-model-asset-proof.md)
remains a separate, managed-lane observation.

| Checkout | Host Terminal observation |
| --- | --- |
| Codexify | `feature/ums-continued` at `97e7006e1eae092c4554b147175a301ea2717a6d`; the required model-asset receipt is in ancestry (`CODEX_ANCESTOR_EXIT=0`). |
| Whoosh'd | `main` at `ed8f75035c00d28604c9262a12894229949074ca`, one local commit ahead of `origin/main`. |

Both checkouts had pre-existing untracked files. They were not part of this
task and were left untouched. Whoosh'd source remained unchanged; its local
foreground-native repair commit remains intact and unpushed.

## Configured path contract

The active Whoosh'd `configs/models.yaml` entry for
`gemma-4-12b-it-qat-4bit` and the active
`ops/launchd/render_launchd_plists.py` default for
`--mlx-vlm-model-path` both identify exactly:

```text
/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit
```

Path equality passed in the Host Terminal transcript and in a read-only
checkout check before writing this receipt. Neither source was edited. This
is configured-path evidence, not installed-model or live-inventory proof.

## Host storage truth

| Check | Host Terminal result |
| --- | --- |
| `/Volumes/Dev_SSD` directory exists | No (`MODEL_VOLUME_EXISTS=no`). |
| Filesystem mounted at `/Volumes/Dev_SSD` | No entry in `mount`; the `/Volumes` root listing also has no `Dev_SSD` entry. |
| `diskutil info /Volumes/Dev_SSD` | `Could not find disk: /Volumes/Dev_SSD`. |
| `diskutil list` | No volume named `Dev_SSD` appeared in the reported inventory. This does not establish why the intended storage is unavailable. |
| Filesystem type | Unavailable because the target is absent. |
| Read-only state and shell writability | Not tested because the target is absent. |
| Free space | Not measurable at the configured target; conditional `df` checks did not run. |
| Expected `whooshd/model-weights/hub` hierarchy | Not directly inspected because the configured root is absent; no path beneath that root is reachable. |
| Canonical model target pre-existing content | Not present at the configured path while the root is absent; no content inspection or provenance claim was made. |

The transcript distinguishes this result from `MODEL_STORAGE_NOT_MOUNTED`:
DiskManagement did not identify a `Dev_SSD` volume that could be associated
with the configured path. It does not prove that a physical device has been
lost, reformatted, or permanently removed.

## Safety, classification, and next prerequisite

`MODEL_STORAGE_RECONCILIATION_REQUIRED` is the single outcome. The current
`/Volumes/Dev_SSD` path is not presently realizable on AxisNode according to
the operator's Host Terminal inventory. No replacement root is selected or
accepted by this receipt.

The Host Terminal capture and this closeout did not mount or unmount a volume,
repair a filesystem, create a directory or file under `/Volumes/Dev_SSD`,
contact Hugging Face, download or load a model, render launchd, start a
service, run inference, or change Docker or Tailscale state. No registry,
renderer, `.env`, Compose, ADR, or runtime configuration changed. Codexify
`.env` remains ignored and unstaged.

The next atomic #815 task must explicitly select and reconcile an AxisNode
model-storage root across the governing registry and renderer contract before
any Gemma 4 12B download. Keep #815 open. No new ADR or current-state/release
claim follows from this storage observation.
