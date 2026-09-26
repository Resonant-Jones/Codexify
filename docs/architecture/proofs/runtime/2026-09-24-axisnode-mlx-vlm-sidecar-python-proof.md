# AxisNode MLX-VLM Sidecar Python Proof

Date: 2026-09-24
Tracking: Codexify #815 (parent #813)
Classification: `MLX_VLM_SIDECAR_PYTHON_READY` on the AxisNode Host Terminal

## Scope and source identity

This receipt records the operator-reported Host Terminal qualification of the
dedicated MLX-VLM sidecar Python. It does not qualify a model or a running
service. The Host Terminal transcript was not attached to this closeout; the
operator supplied the results below directly. Read-only checks in the managed
closeout session are identified separately where their execution conditions
matter.

Codexify was `feature/ums-continued` at
`c0989b8ade80e6940bba7a2a462cb378549f1332` before this receipt. That
commit was in current ancestry. Whoosh'd was `main` at the unpushed local
foreground-native repair commit
`ed8f75035c00d28604c9262a12894229949074ca`, also in current ancestry.
The prior [12B prerequisite proof](2026-09-23-axisnode-whooshd-12b-prerequisite-proof.md)
is time-bounded: its launcher finding was repaired by the Whoosh'd commit, and
this receipt records the subsequent sidecar prerequisite. Pre-existing
untracked Codexify cache/Scout files and the Whoosh'd Pi session HTML file
were left untouched.

## Dedicated interpreter qualification

| Check | Evidence and result |
| --- | --- |
| Environment | `/Users/resonant_jones/.local/share/whooshd/venvs/mlx-vlm`, created in ordinary AxisNode Host Terminal outside both repositories. Its `bin/python` exists and is executable in this closeout session. |
| Interpreter | `/Users/resonant_jones/.local/share/whooshd/venvs/mlx-vlm/bin/python`; Python `3.14.3`, `arm64`, reconfirmed by read-only metadata here. |
| Package | Host Terminal installed `mlx-vlm 0.7.2` only in the dedicated environment. Installed distribution version `0.7.2` was reconfirmed read-only through `importlib.metadata`. |
| Dependencies | Host Terminal reported `pip check`: `No broken requirements found`; this closeout's read-only `pip check` returned the same result. |
| Import | Host Terminal reported `import mlx_vlm`: PASS. The managed closeout session could not reproduce this import because MLX reported `No Metal device available` in the sandbox. That is a managed execution limitation, not a Host Terminal import failure. |
| CLI | Host Terminal reported `python -m mlx_vlm server --help`: PASS without a model or server start; the parser exposed `--host`, `--port`, and `--model`. The same read-only probe in the managed session stopped during Metal initialization before parser output. |
| Renderer input | The current Whoosh'd renderer accepts the explicit absolute `--mlx-vlm-python` path; its paired sidecar plist invokes that Python with `-m mlx_vlm server`. No renderer invocation occurred in this task. |

The prospective renderer input is:

```text
--mlx-vlm-python /Users/resonant_jones/.local/share/whooshd/venvs/mlx-vlm/bin/python
```

This interpreter is outside either Git checkout and does not require shell
activation. The Whoosh'd proxy Python remains independently selected. No
Python package was installed, upgraded, or removed during this proof closeout.

## Runtime and evidence boundaries

The operator reported no TCP 8000 or 8082 listeners and no registered
`system/com.resonant.whooshd` or
`system/com.resonant.mlx-vlm-gemma12b` jobs after Host Terminal qualification.
Read-only closeout checks also found no listeners on either port; both exact
`launchctl` queries returned absent (exit 113). Docker container state and
Tailscale Serve state were not reverified in the Host Terminal capture or this
closeout. No state is inferred for those surfaces.

The operator reported no model-weight download. This closeout did not download
or load a model, run inference, render or install a plist, start a service, or
change a registry, Compose file, Codexify `.env`, Whoosh'd source, or host
configuration. Codexify `.env` remains ignored and unstaged. The selected
Gemma 4 12B asset at the configured Dev SSD path is still absent in this
closeout's read-only path check.

`MLX_VLM_SIDECAR_PYTHON_READY` proves the Host Terminal interpreter and
documented command parser only. It does not prove Gemma 12B loading, live
inventory, inference, Whoosh'd-to-sidecar connectivity, Guardian provider
readiness, Scout continuity, or release readiness. The next atomic #815
prerequisite is to restore and qualify only the operator-approved
`gemma-4-12b-it-qat-4bit` asset before any launchd render or installation.
No new ADR or current-state/release claim is made. #815 remains open.
