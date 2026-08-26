# Whoosh'd launchd bootstrap error 5 diagnosis proof

**Classification:** `WHOOSHD_BOOTSTRAP_ERROR_5_CAUSE_IDENTIFIED`
**First causal classification:** `WHOOSHD_BOOTSTRAP_STALE_LAUNCHD_STATE`
**ADR impact:** No ADR impact — host lifecycle diagnosis only.

## Scope and preserved boundaries

This is a read-only diagnosis of the one operator-authorized system-domain
bootstrap that failed after `bootout`. No lifecycle retry, plist edit,
registry/configuration change, direct daemon start, backend/worker action,
inference, DeepSeek request, Watchdog action, or storage mutation occurred.

The intentionally unrelated unstaged edit in
`guardian/workers/watchdog_review_worker.py` was observed at entry and left
untouched and unstaged.

## Source and runtime baseline

- Codexify branch: `codex/diagnose-tester-fresh-chroma-failure`
- Codexify pre-diagnosis HEAD:
  `3b37023e625bec6352c2da8f66d3a1ad6cbef4c0`
  (`Prove operator Whooshd Qwen reload`)
- Required proof ancestry: the full commit resolved with
  `git cat-file -e` and is an ancestor of the pre-diagnosis HEAD.
- Whoosh'd root: `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd`
- Whoosh'd branch/HEAD: `main` at
  `09e83a8359e3673e7c18a2e0b4733afd334b3bac`
- Whoosh'd status: clean; `main...origin/main [ahead 1, behind 22]`.
- Canonical registry path/blob/content hash:
  `configs/models.friends-family-guest.yaml`,
  `dc70602d29c174560e012943f32b67b14b69d12a`, and
  `93fabb026ec3314271f58f1cea69a05fa96bb1fae8de4d54c0fa40c517775817`.

The operator's only lifecycle sequence was a successful
`bootout system/com.resonant.whooshd`, followed by one failed
`bootstrap system /Library/LaunchDaemons/com.resonant.whooshd.plist` that
reported `Bootstrap failed: 5: Input/output error`. This diagnostic task did
not repeat either operation.

At diagnosis entry and again after inspection:

- `launchctl print system/com.resonant.whooshd` reported that the service was
  not present in the system domain.
- No process matching the Whoosh'd daemon or Uvicorn command was present.
- No listener was present on `127.0.0.1:8000`.

The proxy therefore remained unloaded throughout the diagnosis.

## Plist identity and structural checks

Active plist: `/Library/LaunchDaemons/com.resonant.whooshd.plist`

| Property | Observed value |
| --- | --- |
| SHA-256 | `3a82268a28b81ed35019e2abf9bc587a93e16985572aaa31c6a86f4f4b990c33` |
| Owner/group/mode | `root:wheel`, `-rw-r--r--` |
| ACLs | none reported |
| Extended attribute | `com.apple.provenance` (11 bytes) |
| Syntax | `plutil -lint` returned `OK` |
| Label | `com.resonant.whooshd` |
| Program | not set; `ProgramArguments[0]` is the executable |
| Program arguments | `/Users/chriscastillo/.local/bin/whooshd --host 127.0.0.1 --port 8000` |
| Working directory | `/Volumes/Dev_SSD/ResonantConstructs/Whoosh'd` |
| User/group | `chriscastillo`; no `GroupName` field |
| Standard output/error | `/tmp/whooshd.out`; `/tmp/whooshd.err` |
| RunAtLoad / KeepAlive | `true` / `true` |

Every component of `/Library/LaunchDaemons/com.resonant.whooshd.plist` is
owned by root and is world-traversable/readable as appropriate:
`/`, `/Library`, and `/Library/LaunchDaemons` are `drwxr-xr-x`; the plist is
`root:wheel -rw-r--r--`. The label matches the operator procedure exactly.
No plist syntax, label, or path-access failure was found, and the plist was
not modified.

The non-secret environment contract contains the explicit Whoosh'd root,
registry path, Python path, local model-artifact path, `127.0.0.1` host,
ports `8000` and `8082`, and a PATH containing the wrapper directory. No
credential or token value was recorded.

## Executable and path prerequisites

| Surface | Read-only result |
| --- | --- |
| Launcher | `/Users/chriscastillo/.local/bin/whooshd`: `chriscastillo:staff`, `-rwxr-xr-x`, executable zsh script; SHA-256 `2ad7b8f59038aa644fa694deec3a8b2151f7734ed956e38bfa16c3fc6149d62d` |
| Launcher interpreter | `/usr/bin/env` and `/bin/zsh` exist and are executable; `/bin/zsh` is universal and supports the arm64 host |
| Host architecture | `arm64` |
| Launcher security metadata | `com.apple.provenance` present; no quarantine attribute reported; the script is unsigned, with no launchd security-denial evidence |
| Runtime Python | `.../Whoosh'd/.venv311/bin/python` resolves to an arm64 executable, executable by `chriscastillo`; its ad-hoc signature was readable |
| Working directory | existing `chriscastillo:staff drwxr-xr-x` repository root; all parent directories are traversable |
| Registry resolution | `WHOOSHD_MODEL_REGISTRY_PATH` is the exact absolute canonical registry; the loader consults this environment variable directly |
| Registry access | parent `configs` is `chriscastillo:staff drwx------`; the plist launches as that same user, so it is accessible; registry file is `-rw-r--r--` |
| Canonical Qwen mapping | `qwen3.8-27b-4bit` maps via `mlx_vlm` / `mlx` to `/Volumes/Dev_SSD/whooshd/model-weights/Qwen3.8-27B-4bit` |
| Model artifact | existing `chriscastillo:staff drwxr-xr-x` directory; all parent components are traversable/readable by the launch user; no model data was read, moved, or changed |
| stdout/stderr | `/tmp` resolves to `/private/tmp`; both configured files exist, are `chriscastillo:wheel -rw-r--r--`, and are writable by the configured launch user |

The Whoosh'd root has a quarantine extended attribute, but the same launcher,
working directory, registry, and artifact had already started and served the
pre-bootout process. The bounded launchd evidence below contains no security
denial. It is therefore not a causal security block for this failed bootstrap.

## Bounded daemon-log evidence

The configured logs confirm the previous process started normally and was
shut down during the operator bootout:

- `/tmp/whooshd.err` recorded `Started server process [849]`, successful
  application startup, orderly shutdown, and `Finished server process [849]`.
- `/tmp/whooshd.out` contains only pre-bootout local health and model-inventory
  requests in its bounded tail.
- No second `Started server process` entry or post-failure daemon output was
  present. The stderr file's final modification time was 17:40:27 local time,
  and stdout's was 17:39:48 local time.

Together with the absent service, process, and port listener, this establishes
that the failed bootstrap did not launch a new Whoosh'd child process.

## First causal launchd evidence

The bounded macOS unified-log window (17:40:00–17:41:30 local time) contains
the causal sequence:

```text
2026-08-25 17:40:27.732 launchd[1] [system:] entering bootstrap mode
2026-08-25 17:40:27.733 launchd[1] [system:] Bootstrap by launchctl[7590] for <private> failed (37: Operation already in progress)
2026-08-25 17:40:27.926 launchd[1] [system:] service inactive: com.resonant.whooshd
2026-08-25 17:40:27.926 launchd[1] [system:] removing service: com.resonant.whooshd
```

`37` is the launchd-reported `Operation already in progress` failure. The
bootstrap was rejected while the preceding bootout's service removal was still
in flight; the removal record follows the failed bootstrap. This is the first
evidence-backed blocker and explains the command-line `error 5` receipt
without attributing the failure to any static Whoosh'd configuration surface.

`launchctl print-disabled system` reports `com.resonant.whooshd => enabled`.
There is no disabled-label cause. After the transition completed,
`launchctl print system/com.resonant.whooshd` reported no system-domain
service record; no alternate stale registration was found.

## Result and deferred repair seam

`WHOOSHD_BOOTSTRAP_ERROR_5_CAUSE_IDENTIFIED`

The sole first causal classification is
`WHOOSHD_BOOTSTRAP_STALE_LAUNCHD_STATE`: the bootstrap collided with the
ongoing removal transition, not with a malformed plist or an unavailable
runtime dependency.

The next task may authorize exactly one lifecycle repair/requalification
attempt: wait for and verify completed removal before a single privileged
bootstrap. It must preserve the exact plist, registry, Qwen artifact, and
Tester authority; it must not combine that attempt with Guardian qualification
or model inference.

## Execution and persistence boundaries

| Boundary | Result |
| --- | --- |
| Bootstrap/load/kickstart retries during diagnosis | `0` |
| Direct Whoosh'd daemon launches | `0` |
| Model invocations during diagnosis | `0` |
| DeepSeek requests during diagnosis | `0` |
| Watchdog activity during diagnosis | `0` |
| Backend or `worker-chat` lifecycle actions | `0` |
| Manual Postgres, Redis, Chroma, or model-artifact mutation | `0` |
| Guardian qualification/API probes | `0` |

No release/current-state claim was changed. Previous proof receipts and
`docs/architecture/00-current-state.md` remain unchanged.

## Validation record

Executed read-only checks included:

```text
git cat-file -e 3b37023e625bec6352c2da8f66d3a1ad6cbef4c0^{commit}
git merge-base --is-ancestor 3b37023e625bec6352c2da8f66d3a1ad6cbef4c0 HEAD
git status --short --branch
git rev-parse HEAD
git branch --show-current
git -C /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd status --short --branch
git -C /Volumes/Dev_SSD/ResonantConstructs/Whoosh'd rev-parse HEAD
plutil -lint /Library/LaunchDaemons/com.resonant.whooshd.plist
launchctl print system/com.resonant.whooshd
launchctl print-disabled system
log show (bounded to the failed-bootstrap window)
```

All evidence-gathering commands completed without changing host/runtime
state. The deliberately absent service and port are expected baseline facts,
not validation failures.
