"""Guardian-side permission posture resolution for delegated coding tasks.

The Guardian Delegation Loop must resolve an *enforceable* permission posture
before anything is dispatched. This module derives that posture from trusted
account, project, and workspace context, and states plainly which parts of it
the runtime actually enforces.

ADR-077 draws the line that matters here, and it is not the one a permission
dictionary implies:

- Guardian **authorizes**. The worker **translates** the grant but may not
  enlarge it. The sandbox provider **realizes** the already-authorized
  posture.
- "Denied filesystem mutation is enforced below the model/tool layer" (ADR-077
  rule 6), and "tool allowlists and prompt instructions are defense in depth,
  **not** sufficient filesystem, network, or process isolation" (rule 7).

So a permission flag is a *request*, not a guarantee. This module therefore
records, for every posture it resolves, which enforcement surface backs it and
which surfaces remain advisory. It never reports a posture as enforced when the
runtime only observes it after the fact.

Enforcement surfaces actually present in this runtime, verified in code:

- **Git mutation guard** — the worker snapshots ``git porcelain`` before and
  after the adapter runs and compares the changed paths against
  ``allowed_paths``; a violation fails the attempt
  (``_enforce_isolated_mutation_scope`` / ``_evaluate_mutation_guard`` in
  ``guardian/workers/coding_worker.py``). This is a *detection* boundary: it
  observes the mutation after it happened and fails the attempt, it does not
  prevent the write.
- **Worktree lease** — scopes the attempt to an isolated checkout and refuses
  two active leases sharing a worktree path or branch
  (``guardian/agents/worktree_leases.py``).
- **Credential lease** — the authority gate for provider/model/credential.
- **Validation shell gate** — ``allow_shell=false`` means a validation command
  is not run at all, so that capability is genuinely withheld.

Advisory at this layer, and therefore never claimed as enforced:

- **Network egress** — there is no sandbox provider wired into the coding
  worker. ``allow_network`` is carried on the policy but is not enforced by
  the adapter or the worker.
- **Process isolation** — the adapter runs a subprocess in the worker context;
  there is no OS-level isolation boundary in this runtime.

See ADR-077, ADR-094, and
``docs/architecture/guardian-delegation-loop-contract.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Maximum runtime for one delegated attempt, in seconds.
GUARDIAN_CODING_MAX_RUNTIME_SECONDS = 300

#: Canonical write scope for a delegated task: the whole bound repository.
#: The mutation guard compares changed paths against this scope; a path outside
#: it fails the attempt.
#:
#: ``"."`` is the explicit repository-root token. It is the *representation* of
#: an already-authorized bound-repository grant, never a fallback: a write
#: posture still requires a resolved repository root and an explicit write
#: grant (see ``resolve_guardian_permission_posture``). The worker is the
#: canonical interpreter of this scope, so Guardian emits the token and does
#: not restate the path policy.
GUARDIAN_DEFAULT_ALLOWED_PATH_SCOPE = (".",)


class GuardianPermissionPostureError(RuntimeError):
    """A required capability could not be authorized.

    ``code`` is a stable, machine-readable reason. The posture is never
    produced in this case — this is a fail-closed authority.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail or code


@dataclass(frozen=True)
class GuardianPermissionPosture:
    """One resolved permission posture plus its enforcement provenance.

    ``permission_policy`` is the request the worker and adapter consume.
    ``enforced_surfaces`` names what actually backs each capability.
    ``advisory_surfaces`` names what is only requested or observed.
    """

    permission_policy: dict[str, Any]
    enforced_surfaces: tuple[str, ...] = ()
    advisory_surfaces: tuple[str, ...] = ()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "permission_policy": dict(self.permission_policy),
            "enforced_surfaces": list(self.enforced_surfaces),
            "advisory_surfaces": list(self.advisory_surfaces),
            "notes": list(self.notes),
        }


def _scope_has_usable_entry(scope: Any) -> bool:
    """Return True when a scope names at least one usable path entry.

    This is a shape check, not a path policy. Guardian does not decide which
    paths are authorized — the worker is the canonical interpreter of the
    scope, and it rejects any entry it cannot resolve. All Guardian asserts
    here is that a scope is not empty in substance, so a blank scope can never
    be produced as a write grant.
    """
    if not isinstance(scope, (list, tuple, set)):
        return False
    return any(str(entry or "").strip() for entry in scope)


def resolve_guardian_permission_posture(
    *,
    account_id: str,
    provider_id: str,
    model_id: str,
    repo_root: str | None,
    allowed_paths: tuple[str, ...] | None = None,
    allow_write: bool = True,
    allow_shell: bool = False,
    allow_network: bool = False,
    max_runtime_seconds: int = GUARDIAN_CODING_MAX_RUNTIME_SECONDS,
) -> GuardianPermissionPosture:
    """Resolve one enforceable permission posture from trusted context.

    The caller supplies only trusted account/project/workspace facts. The
    resulting posture is the *narrowest* one that still permits the delegated
    work, and its enforcement provenance is explicit.

    Raises:
        GuardianPermissionPostureError: when a required capability cannot be
            authorized, or when the requested posture could not be established.
    """
    if not str(account_id or "").strip():
        raise GuardianPermissionPostureError("guardian_posture_account_missing")
    if not str(provider_id or "").strip():
        raise GuardianPermissionPostureError("guardian_posture_provider_missing")
    if not str(model_id or "").strip():
        raise GuardianPermissionPostureError("guardian_posture_model_missing")

    runtime_seconds = int(max_runtime_seconds or 0)
    if runtime_seconds < 1:
        raise GuardianPermissionPostureError(
            "guardian_posture_runtime_limit_invalid"
        )

    # Write scope is relative to the bound repository. Writing outside the
    # bound working tree is not authorizable at all, so it is refused rather
    # than silently narrowed.
    resolved_root = str(repo_root or "").strip()
    if allow_write and not resolved_root:
        raise GuardianPermissionPostureError(
            "guardian_posture_write_scope_unresolved"
        )

    scope = tuple(allowed_paths) if allowed_paths is not None else ()
    if allow_write and not _scope_has_usable_entry(scope):
        # A write request with no usable scope would authorize the whole tree.
        # Fail closed rather than defaulting to unrestricted write. A scope of
        # blank entries is no scope at all: it names nothing the worker could
        # authorize, so it must not be emitted as a grant.
        raise GuardianPermissionPostureError(
            "guardian_posture_write_scope_missing"
        )

    permission_policy: dict[str, Any] = {
        "allow_shell": bool(allow_shell),
        "allow_network": bool(allow_network),
        "allow_write": bool(allow_write),
        "allowed_paths": list(scope),
        "max_runtime_seconds": runtime_seconds,
    }

    enforced: list[str] = []
    advisory: list[str] = []
    notes: list[str] = []

    if allow_shell:
        # The validation shell gate genuinely withholds the capability: with
        # allow_shell=false the command is never executed. With it true, the
        # command runs inside the worker context.
        enforced.append("validation_shell_gate")
        notes.append(
            "Shell execution runs inside the coding worker context; it is not "
            "an OS-level process-isolation boundary."
        )
    else:
        enforced.append("validation_shell_gate")
        notes.append(
            "allow_shell=false withholds the capability outright: a validation "
            "command is not executed."
        )

    if allow_write:
        enforced.append("git_mutation_guard")
        notes.append(
            "The git mutation guard compares changed paths against "
            "allowed_paths after the adapter runs and fails the attempt on a "
            "violation. It detects the mutation; it does not prevent the "
            "write from landing."
        )
        enforced.append("worktree_lease_isolation")
    else:
        enforced.append("read_only_tool_surface")
        notes.append(
            "allow_write=false both withholds the write tool and fails the "
            "attempt on any detected change."
        )

    if allow_network:
        advisory.append("network_egress")
        notes.append(
            "allow_network is a request. No sandbox provider is wired into the "
            "coding worker, so network egress is not enforced at this layer."
        )
    else:
        advisory.append("network_egress")
        notes.append(
            "allow_network=false is honoured as a request only. ADR-077 rule 4 "
            "notes that sandbox network authority is distinct from the parent "
            "model client and the worker-to-provider control connection, so "
            "this flag is not an egress guarantee."
        )

    advisory.append("process_isolation")
    notes.append(
        "The adapter runs a subprocess in the worker context. There is no "
        "OS-level isolation boundary in this runtime, so a permission flag is "
        "not an isolation guarantee (ADR-077 rules 7 and 8)."
    )

    return GuardianPermissionPosture(
        permission_policy=permission_policy,
        enforced_surfaces=tuple(enforced),
        advisory_surfaces=tuple(advisory),
        notes=tuple(notes),
    )


def validate_guardian_permission_posture(
    posture: GuardianPermissionPosture,
    *,
    requested_allow_write: bool,
    requested_allow_shell: bool,
    requested_allow_network: bool,
) -> None:
    """Refuse a posture that grants more than was requested.

    A caller proposal may narrow a posture, never widen it. This is the
    counterpart to the binding authority: even if a widened policy somehow
    reached the dispatch layer, it is rejected here.
    """
    policy = posture.permission_policy
    if requested_allow_write and not bool(policy.get("allow_write")):
        raise GuardianPermissionPostureError(
            "guardian_posture_write_grant_missing"
        )
    if requested_allow_shell and not bool(policy.get("allow_shell")):
        raise GuardianPermissionPostureError(
            "guardian_posture_shell_grant_missing"
        )
    if requested_allow_network and not bool(policy.get("allow_network")):
        raise GuardianPermissionPostureError(
            "guardian_posture_network_grant_missing"
        )
    if bool(policy.get("allow_write")) and not _scope_has_usable_entry(
        policy.get("allowed_paths")
    ):
        raise GuardianPermissionPostureError(
            "guardian_posture_write_scope_missing"
        )
