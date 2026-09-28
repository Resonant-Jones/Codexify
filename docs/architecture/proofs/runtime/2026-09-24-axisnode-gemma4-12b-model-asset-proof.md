# AxisNode Gemma 4 12B Model Asset Proof

Date: 2026-09-24
Tracking: Codexify #815 (parent #813)
Classification: `MODEL_STORAGE_TARGET_UNAVAILABLE`

## Scope and execution boundary

This receipt records an early storage-root stop for the operator-approved
`gemma-4-12b-it-qat-4bit` asset. The requested ordinary AxisNode Host Terminal
was unavailable to this Codex session: the computer-use interface refused to
open Terminal. Read-only filesystem and process observations below came from
the managed Codex shell on the same machine. They establish what that shell
could see, not an independent Host Terminal mount or disk diagnosis.

No model directory was created, no repository was contacted, and no model
files were downloaded. A Host Terminal check of the configured volume is the
next prerequisite before any download or storage-path decision.

## Repository and model authority

| Item | Observed value |
| --- | --- |
| Codexify checkout | `feature/ums-continued` at `47b4dfb5edff6ee9fb0b6e8bc386eb377f103b92`; the required sidecar-Python proof commit is in current ancestry. |
| Whoosh'd checkout | `main` at `ed8f75035c00d28604c9262a12894229949074ca`; the local foreground-native repair commit is in current ancestry and remains unpushed. |
| Approved model ID | `gemma-4-12b-it-qat-4bit` |
| Approved upstream repository | `mlx-community/gemma-4-12B-it-qat-4bit` |
| Configured volume | `/Volumes/Dev_SSD` |
| Configured model path | `/Volumes/Dev_SSD/whooshd/model-weights/hub/models--mlx-community--gemma-4-12B-it-qat-4bit` |

The active Whoosh'd `configs/models.yaml` entry is enabled and names the
configured model path exactly. The active
`ops/launchd/render_launchd_plists.py` default for `--mlx-vlm-model-path`
names the same path. This is a read-only source-contract check, not live model
inventory or renderer execution. The machine-local Codexify model choice and
the prior qualified sidecar interpreter remain the preceding proof boundaries;
they were not changed or rerun after the storage stop.

## Storage stop and unperformed asset checks

The managed shell's `/Volumes` directory exists, but checking
`/Volumes/Dev_SSD` returned `No such file or directory`. The required
storage-root guard emitted `MODEL_STORAGE_TARGET_UNAVAILABLE` and exited 20
before any mutation. `diskutil list` and `diskutil info Dev_SSD` could not use
the DiskManagement framework in this session. The configured model path was
also absent. No parent or final model directory was created.

| Check | Result |
| --- | --- |
| Configured volume availability | Absent from the managed shell; ordinary Host Terminal state unverified. |
| Configured volume writability | Not tested because the directory was absent. |
| Free space and required capacity | Not tested; no upstream byte total was requested. |
| Immutable upstream revision SHA | Unresolved. |
| Remote file count and byte total | Unresolved. |
| Pinned download | Not attempted. |
| Remote/local completeness | Not tested. |
| Safetensors and index completeness | Not tested. |
| Offline `mlx_vlm` configuration resolution | Not tested. |

The unresolved upstream values are not represented as zero. The prior
sidecar-Python receipt records Host Terminal qualification of Python 3.14.3,
arm64, `mlx-vlm 0.7.2`, and `pip check` PASS; this task did not promote that
prior evidence into asset qualification.

## Runtime observations and safety

Read-only managed-shell `lsof` checks found no TCP listeners on ports 8000 or
8082. Exact `launchctl print` queries returned exit 113 for
`system/com.resonant.whooshd` and
`system/com.resonant.mlx-vlm-gemma12b`, indicating neither job was registered
in this session. `docker ps` could not access the Docker socket (`permission
denied`), and `tailscale serve status` reported that the CLI could not load
preferences. Docker and Tailscale state were therefore not independently
confirmed. These observations are not Host Terminal runtime proof.

This task did not load a model, run inference, start MLX-VLM, Whoosh'd,
Guardian, a database, a worker, or Scout, render or install launchd, or create
a listener or launchd job. It changed no registry, renderer, `.env`, Compose,
ADR, or service configuration. Codexify `.env` remained ignored and unstaged;
the pre-existing untracked files in both checkouts were left untouched.

## Classification and next prerequisite

`MODEL_STORAGE_TARGET_UNAVAILABLE` is the single outcome for the storage root
visible to this execution session. The specified Host Terminal lane was not
available, so this receipt does not establish whether the Dev SSD is mounted
or writable in an ordinary Host Terminal. The next #815 task must reconcile
the AxisNode model-storage path explicitly, beginning with the exact
`/Volumes/Dev_SSD` availability and writability check in that lane. Do not
download, choose another storage location, or mutate the registry before that
gate is resolved. Keep #815 open.

No new ADR is required. Existing operator model/provider/storage authority is
preserved, and no current-state or release claim advances. The future
render-validation task remains downstream of a complete asset qualification.
