# UMS-02B Persona-Subject Lifecycle Token Proof

Date: 2026-09-07

Status: **VALIDATED — SCOPED COMMIT BLOCKED**

## Qualification identity

- Execution lane: architecture-impact
- Task kind: identity contract / canonical-token implementation
- Starting HEAD: `79d571259d4d715316d313371c6bede54e52fbce`
- Starting Alembic head: `d4e8f1a2b6c9`
- Git commit SHA after commit: not available; the managed harness cannot
  create `.git/index.lock` for the final receipt update.

## Implemented canonical domain

`guardian.protocol_tokens.PersonaSubjectLifecycle` defines exactly:

```text
active
retired
```

- `active` is a current durable attribution identity.
- `retired` is a retained historical durable attribution identity and is not a
  current attribution target.
- `retired` is not deletion, purge, merge, or ownership transfer. It does not
  rewrite attribution, delete bindings or memory, or grant another Persona
  access to history.

The token is an identity-persistence vocabulary only. It does not create
`persona_subjects` or `persona_subject_bindings`, introduce a retirement
transition, or add a route, service, memory attribution, export, restore, or
frontend behavior.

## Contract and architecture alignment

- The Runtime Protocol Token Contract registers the domain before any future
  persistence/runtime consumer may use it.
- The Unified Memory Store Contract records the exact vocabulary and preserves
  the frozen UMS-02A ownership, coalescing, cross-account, and binding-history
  rules.
- ADR-082 and ADR-084 are unchanged and remain aligned: PersonaProfile is
  mutable runtime configuration, stable Persona subjects are account-owned
  attribution identities, and Persona subjects never own memory.
- UMS-02C, not this task, owns matching ORM schema, Alembic persistence,
  deterministic legacy backfill, account-consistency and binding-history
  enforcement, and PostgreSQL qualification.

## Invariant and non-impact check

- Exact lifecycle domain: `active | retired`; no additional state was added.
- No ORM model or Alembic migration was added or modified.
- No runtime call site consumes `PersonaSubjectLifecycle` yet.
- No route, service, worker, memory, export, restore, Persona Studio, or
  frontend behavior was added.
- UMS-02 remains open; UMS-03 remains unauthorized; no release claim changed.
- The known unrelated Pi fixture remains untouched and unstaged:
  `tests/pi/fixtures/fake_pi_package/package.json`
  (`SHA-256 1589b9d20d0fd6e5865abe5b1f23bd3867a339c7ac3806dac584c2ceacbff93b`).

## Validation record

| Check | Result | Evidence |
| --- | --- | --- |
| Full protocol-token contract suite | PASS | `.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py` — 33 passed, 1 warning; zero failures, errors, or skips. |
| Focused Persona-subject lifecycle assertion | PASS | `.venv/bin/python -m pytest -v tests/contracts/test_protocol_tokens.py -k persona_subject` — 1 passed, 32 deselected, 1 warning. |
| Token module compilation | PASS | `.venv/bin/python -m py_compile guardian/protocol_tokens.py`. |
| Alembic non-impact, before and after | PASS | `.venv/bin/python -m alembic -c backend/alembic.ini heads` — `d4e8f1a2b6c9 (head)` before and after. `history` retains the existing chain; no revision, predecessor, or head changed. |
| ORM and migration diff | PASS | `guardian/db/models.py` and `guardian/db/migrations/**` are unchanged. |
| Runtime-consumer inventory | PASS | No route, service, worker, memory, export, restore, Persona Studio, or frontend consumer was added; only the registry definition and its contract assertion refer to the new token. |
| Documentation validation | PASS | `.venv/bin/python scripts/validate_docs.py` — required architecture docs, README links, and source headings verified. |
| Diff whitespace check | PASS, scoped | The task-owned and staged diffs pass `git diff --check`. The repository-wide command reaches the known unrelated Pi fixture and is blocked by the harness's inability to write `.git/lfs/tmp`; it does not identify a task-owned whitespace error. |
| Edit boundary | PASS | The six modified tracked task files plus this new receipt are the only task-owned changes; no task file is staged outside the seven authorized paths. |

The known unrelated Pi fixture remains modified but untouched and unstaged.
The seven authorized paths were staged before the final receipt update, but
restaging that update failed with `fatal: Unable to create '.git/index.lock':
Operation not permitted`. No commit, hook, push, or merge was attempted after
that failure; the receipt remains intentionally unstaged rather than allowing
a stale proof to be committed. This is contract/token implementation proof
only, never runtime proof.
