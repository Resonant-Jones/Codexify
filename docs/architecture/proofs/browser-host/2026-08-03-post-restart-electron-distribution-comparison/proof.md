# Post-restart Electron distribution comparison

- Comparison proof: **passed**
- Primary classification: `clean_electron_43_2_0_also_fails`
- Repository commit: `0c229374e1af46afe4d7bcde71c3d82674ec392b`
- Prerequisite: `a8b3dd00e` is in ancestry
- Host: macOS `26.5.2`, `arm64`, Gatekeeper enabled, Aqua available
- Apple control: Calculator strict signature and Gatekeeper assessment passed
- Repository Electron minimal launch: **passed**
- Clean Electron minimal launch: **passed**
- Production Browser Host live qualification: **next-proof-needed**

## Comparison result

One isolated `npm ci --no-audit --no-fund --cache <isolated-cache>` workspace
was created under the temporary directory. Only the Browser Host package and
lock files were copied. Electron's package-provided install hook obtained the
exact locked Electron `43.2.0` arm64 distribution. The workspace, cache,
minimal applications, user data, bounded diagnostic area, and temporary proof
output were removed after the run.

The repository and clean distributions have the same executable SHA-256:

`79019361f697c1a81489dba3e94631b0977770c1ab15236f1f033f9de6238874`

Their deterministic bundle-relative regular-file manifests are also equal:

`9b5e226efda46377fa2ccfaeaead62ac93ab7f9ab3dde0425f6344d436f314f8`

Each manifest contains 258 regular files and 288,611,706 bytes. There are zero
missing paths, zero extra paths, and zero content-hash mismatches. No complete
per-file manifest is committed.

Both bundles are quarantine-free and expose matching bounded signature
metadata. Both fail strict signature and Gatekeeper resource validation with
the same `code has no resources but signature indicates they must be present`
failure. Both `--version` checks return `v43.2.0`. Both minimal applications
reach `app.whenReady()`, create and load one local hidden `BrowserWindow`, and
exit 0 with sandbox requested, Node integration disabled, context isolation
enabled, no preload, no network, no Browser Host or Guardian code, no
credentials, and no insecure flags.

No authoritative minimal attempt terminated with `SIGABRT`, so no diagnostic
report search was required and no raw report is committed.

## Classification boundary

The Apple control passes, while both identical Electron distributions fail the
same signature and Gatekeeper surface. This satisfies the task's
`clean_electron_43_2_0_also_fails` rule through materially equivalent
signature/assessment failure. It does not demonstrate repository-local bundle
corruption or metadata/resource drift, and it does not justify a repository
reinstall.

The committed historical qualification runner also completed in a temporary
output directory, attempted no repair, validated successfully with its
directory argument, and returned its older vocabulary
`isolated_electron_distribution_invalid`. It did not rerun the production live
proof because the clean bundle did not pass its signature/assessment gate.

The Browser Host syntax check, seven contract tests, dependency-tree check, and
35 unit tests passed. The full test command is not green: Electron tests passed
9 of 10, with the real Guardian development-adapter integration exiting 2
instead of 0. Those test results do not qualify a production Browser Host or a
full real-Guardian process.

## Invariants and non-claims

No repository repair was attempted. Repository `node_modules`, package and
lock files, Browser Host source and contracts, Guardian, prior proof packets,
macOS security, quarantine, signing, and release posture were unchanged. No
full real-Guardian session was attempted. No persistence, provider execution,
Command Bus action, packaging, signing/notarization, updater, rollback, beta,
or release behavior was added or proven. Gate C remains passed and Gate D
remains closed.

## Exactly one next atomic task

Qualify Electron 43.2.0 compatibility with macOS 26.5.2 using a temporary
adjacent-version matrix without changing Codexify dependencies or release
posture.
