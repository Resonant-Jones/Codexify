# Parent-owned FAISS snapshot transfer prerequisite — 2026-10-04

## Authority and scope

Resonant Jones selected the policy directly in this chat: keep the parent FAISS
instance as sole mutable authority; authorize a coherent read-only snapshot per
bounded search; include snapshot preparation in the same accepted deadline;
prohibit child additions, persistence and parallel vector authority; fail closed
on deadline rather than falling back to unbounded search.

This resolves the policy question in the preceding
[authority frontier report](./2026-10-04-chat-faiss-deadline-authority-frontier.md).
It does not prove implementation or close qualification. No persistent worker,
replay subsystem, model substitution or second success path is authorized.

Development Operator Level 0, PROOF_REQUIRED, PROOF mode; ADR-087 and existing
Chat Runtime/Completion Pipeline account, namespace, model, store and identity
boundaries apply. Clean evaluated repair source
`8c52b0cef06eec6de63197ae34ac20e65957e597`, branch
`codex/chat-postgres-terminal-deadline-20261003`. One private Task Spec preceded
execution. No application source or accepted ADR changed; no service restart,
application write, download, merge, push or deployment.

## Controlled transfer mechanism

Evidence root:
`/private/tmp/codexify-chat-faiss-readonly-snapshot-8c52b0cef-20261004/`.
The initial probe/source, preparation companion, results, stderr, Task Spec and
independent source/health verification are retained.

The private host fixture uses real FAISS 1.12.0 and the existing explicit mock
embedding backend. A mutex protects parent additions and snapshot capture.
Fork captures a coherent copy-on-write view while that mutex is held. The parent
then releases the mutex. The serializer child reads its captured native index,
text, metadata and model binding and writes ephemeral bytes through an owned
pipe. It exits and is reaped before a fresh interpreter searches the snapshot.
No snapshot file, persisted vector state, application collection or daemon is
created. The search child performs search only; it never calls an add method.

One work deadline derived from the original immutable 720/60 envelope covers
mutex acquisition, capture, serialization/pipe transfer, fresh process startup,
model initialization, search and return. Each wait uses remaining time against
that same deadline. Expiry kills/reaps owned children; cleanup checks the
original terminal deadline. No new work budget, fallback or retry is issued.

## Observations

| Case | Result | Remaining work at return |
| --- | --- | --- |
| First snapshot, parent adds second text after fork | Snapshot has exactly first text; parent reference parity | 41.626437 s |
| Next snapshot | Both acknowledged texts; complete parent result parity | 41.873020 s |
| Negative account | Same two indexed texts, zero returned hits | 41.545862 s |
| Already expired work | Canonical expiry before child admission | n/a |
| 0.050 s work remaining | Search startup expiry; child killed/reaped | n/a |
| 0.025 s work remaining with mutex held | Canonical expiry; no child admitted; 0.030009 s elapsed | n/a |
| 0.002 s work remaining | Preparation-phase expiry; serializer killed/reaped; 0.009181 s total | n/a |

The first successful snapshot excluded an addition acknowledged after capture;
the next snapshot included it. All result text, metadata and scores matched the
parent reference at the corresponding capture. The parent retained its two
acknowledged index/text/metadata entries after the search timeout and still
returned the same results. The separate preparation fixture retained its one
entry. Original acceptance/work/terminal fields remained unchanged.

All successful fixture assertions passed. Main driver exited zero; corrected
preparation driver exited zero. PIDs 23738/23739, 23742/23743, 23755/23756,
23759/23760 and 23973 were reaped; independent `ps` returned no rows, exit 1.
Elapsed timeout observations include cleanup in the terminal reserve; they do
not claim the precise kernel instant every child instruction stopped.

The preparation phase census does not prove serialization was actively
executing at kill time. It proves capture/transfer did not yield a result beyond
the work deadline and the owned process was reaped. The 0.050 s case interrupted
fresh search startup, not proven native SentenceTransformer encoding.

The first preparation companion exited 1 at compile time because its source
delimiter matched the embedded child program, producing an unterminated string.
It entered no native work. Its source, empty stdout and stderr are preserved as
`initial-preparation-*`. The corrected delimiter succeeded. The initial healthy
probe source is retained separately; the companion maps mutex acquisition
timeout to canonical deadline failure instead of the initial fixture assertion.

## Validation, custody and next task

Independent read-only runtime verification matched all 1,136 tracked
Guardian/backend Python files across repair checkout, retained snapshot and
backend/worker containers. This is source custody only; no fresh user turn was
submitted. General health, queue and heartbeat observations are retained in
the private runtime-check artifacts.

Private proof drivers and independent process absence checks passed.
`python3 scripts/validate_docs.py`, local Markdown link resolution and
`git diff --check` passed before the scoped documentation commit. No application
regression suite applies to this docs-only receipt. The commit is recorded in
the Task closeout. Main and its unrelated staged dev-log deletion were preserved.

The policy gate is resolved; the mechanism remains a prerequisite proof.
Production parent additions do not yet use the fixture mutex, and production
search does not yet use this process boundary. Parent buffer assembly/result
decoding, coherent capture across every addition path, model binding across a
fresh process, arbitrary corpus transfer cost and cleanup under pressure still
need production design and verification inside the same deadline. This mock
embedding proof does not qualify native SentenceTransformer initialization or
encoding. The next atomic task is native model/result parity and interruption
with the authorized parent-owned snapshot policy, before production integration.
The complete ordinary-chat Goal remains active; release qualification HOLD.
