"""
Provider-neutral sandbox execution contracts.

This module defines the versioned request/result schemas that
``docs/architecture/adr/077-sandbox-execution-authority-and-provider-boundary.md``
asks a later implementation to define. ADR-077 is deliberately descriptive --
it names no classes, methods, or tokens -- so everything here is a new
canonical contract rather than a transcription of the ADR.

Design rules carried from ADR-077:

* A request names the posture it requires. A provider either establishes that
  posture or the request is **denied before allocation**; a provider never
  silently substitutes a wider posture.
* "Provider accepted" is never translated into "process completed". A result
  distinguishes boundary-establishment failure from execution failure.
* Command text and secret material are never bounded telemetry. Bounded output
  carries stdout/stderr and the artifact manifest only.
* Artifacts are returned by manifest and are never auto-published.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

#: Version of the sandbox execution contract. Bump the minor version when
#: fields are added, the major version when an existing field changes meaning.
SANDBOX_CONTRACT_VERSION = "sandbox.execution.v1"

# --- Postures a request may require ---------------------------------------

POSTURE_READ_ONLY_WORKSPACE = "read_only_workspace"
POSTURE_EGRESS_DENY = "egress_deny"
POSTURE_EGRESS_ALLOWLIST = "egress_allowlist"
POSTURE_CPU_LIMIT = "cpu_limit"
POSTURE_MEMORY_LIMIT = "memory_limit"
POSTURE_STORAGE_CEILING = "storage_ceiling"
POSTURE_TIMEOUT = "timeout"
POSTURE_TEARDOWN = "teardown"
POSTURE_SECRET_ISOLATION = "secret_isolation"

#: Every posture a provider may declare support for.
KNOWN_POSTURES = (
    POSTURE_READ_ONLY_WORKSPACE,
    POSTURE_EGRESS_DENY,
    POSTURE_EGRESS_ALLOWLIST,
    POSTURE_CPU_LIMIT,
    POSTURE_MEMORY_LIMIT,
    POSTURE_STORAGE_CEILING,
    POSTURE_TIMEOUT,
    POSTURE_TEARDOWN,
    POSTURE_SECRET_ISOLATION,
)

# --- Network modes ---------------------------------------------------------

NETWORK_MODE_DENY = "deny"
NETWORK_MODE_ALLOWLIST = "allowlist"

# --- Result statuses --------------------------------------------------------

STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_TIMEOUT = "timeout"
STATUS_CANCELLED = "cancelled"
STATUS_DENIED = "denied"
STATUS_BOUNDARY_FAILED = "boundary_failed"

#: Failure classes. ``boundary`` means the provider could not establish a
#: required posture; ``execution`` means the boundary held but the command did
#: not succeed. These are never interchangeable.
FAILURE_CLASS_BOUNDARY = "boundary"
FAILURE_CLASS_EXECUTION = "execution"


class SandboxError(RuntimeError):
    """Base error for the sandbox execution contract."""


class SandboxPolicyDenied(SandboxError):
    """
    A requested posture is not supported, so execution was refused.

    Raised **before** allocation. The provider that denied the request is
    recorded on :attr:`provider` so the caller can report the reason.
    """

    def __init__(self, message: str, *, provider: str | None = None,
                 unsupported: Sequence[str] = ()):
        super().__init__(message)
        self.provider = provider
        self.unsupported = tuple(unsupported)


class SandboxBoundaryError(SandboxError):
    """A required boundary could not be established in the allocated sandbox."""


class SandboxExecutionError(SandboxError):
    """The command failed inside an established boundary."""


class SandboxTimeout(SandboxError):
    """The execution exceeded its deadline and was terminated."""


# --- Request shapes ---------------------------------------------------------


@dataclass(frozen=True)
class WorkspaceMaterialization:
    """
    How the sandbox obtains its workspace.

    ``source`` must be an integrity-bound reference (a repository URL plus
    digest, or an archive with a digest). A bare host path is not portable
    authority and is not accepted as a workspace identity.
    """

    identity: str
    source: str
    digest: str | None = None
    read_only: bool = True
    scratch_path: str = "/scratch"
    #: Working directory relative to the workspace root. ``""`` means the
    #: workspace root. Traversal outside the workspace is rejected.
    working_directory: str = ""

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("workspace identity is required")
        if not self.source.strip():
            raise ValueError("workspace materialization source is required")
        relative = (self.working_directory or "").strip()
        if relative.startswith("/") or ".." in relative.split("/"):
            raise ValueError(
                "working_directory must be relative to the workspace root"
            )


@dataclass(frozen=True)
class ResourcePosture:
    """Bounded time, CPU, memory, storage, and output posture."""

    timeout_seconds: int
    cpu_millis: int | None = None
    memory_mb: int | None = None
    storage_bytes: int | None = None
    output_max_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        for name in ("cpu_millis", "memory_mb", "storage_bytes"):
            value = getattr(self, name)
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive when set")


@dataclass(frozen=True)
class NetworkPosture:
    """Outbound network posture for command execution."""

    mode: str = NETWORK_MODE_DENY
    allowlist: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in (NETWORK_MODE_DENY, NETWORK_MODE_ALLOWLIST):
            raise ValueError(f"unsupported network mode: {self.mode}")
        if self.mode == NETWORK_MODE_ALLOWLIST and not self.allowlist:
            raise ValueError("allowlist network mode requires at least one host")


@dataclass(frozen=True)
class SecretPosture:
    """
    Secret references passed to the sandbox.

    Only references are carried. Secret material is resolved by the worker
    that owns the credential and is never placed in a request, a result, or
    telemetry.
    """

    refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArtifactPolicy:
    """What the sandbox may leave behind, and whether it may be published."""

    max_artifacts: int = 32
    max_artifact_bytes: int = 32 * 1024 * 1024
    publish: bool = False

    def __post_init__(self) -> None:
        if self.publish:
            raise ValueError(
                "artifacts are never auto-published; publication is an explicit "
                "operator action outside the sandbox contract"
            )


@dataclass(frozen=True)
class SandboxRequest:
    """A single bounded sandbox invocation."""

    contract_version: str
    request_id: str
    idempotency_key: str
    attempt_id: str
    deadline_epoch: float
    principal: str
    lineage: Mapping[str, Any]
    workspace: WorkspaceMaterialization
    command: str
    resources: ResourcePosture
    network: NetworkPosture = field(default_factory=NetworkPosture)
    secrets: SecretPosture = field(default_factory=SecretPosture)
    artifacts: ArtifactPolicy = field(default_factory=ArtifactPolicy)
    env: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.contract_version != SANDBOX_CONTRACT_VERSION:
            raise ValueError(
                f"unsupported sandbox contract version: {self.contract_version}"
            )
        for name in ("request_id", "idempotency_key", "attempt_id", "principal"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")
        if not self.command.strip():
            raise ValueError("command is required")

    def required_postures(self) -> tuple[str, ...]:
        """Postures this request depends on, derived from its own fields."""
        postures = [
            POSTURE_READ_ONLY_WORKSPACE,
            POSTURE_TIMEOUT,
            POSTURE_TEARDOWN,
        ]
        if self.secrets.refs:
            postures.append(POSTURE_SECRET_ISOLATION)
        if self.resources.cpu_millis is not None:
            postures.append(POSTURE_CPU_LIMIT)
        if self.resources.memory_mb is not None:
            postures.append(POSTURE_MEMORY_LIMIT)
        if self.resources.storage_bytes is not None:
            postures.append(POSTURE_STORAGE_CEILING)
        if self.network.mode == NETWORK_MODE_ALLOWLIST:
            postures.append(POSTURE_EGRESS_ALLOWLIST)
        else:
            postures.append(POSTURE_EGRESS_DENY)
        return tuple(postures)


# --- Result shapes ----------------------------------------------------------


@dataclass(frozen=True)
class ArtifactEntry:
    """One artifact produced inside the sandbox. Never published."""

    path: str
    size_bytes: int
    digest: str | None = None


@dataclass(frozen=True)
class MutationEntry:
    """A mutation the command attempted against a protected path."""

    path: str
    effect: str


@dataclass(frozen=True)
class AttestedPosture:
    """
    The posture the provider actually established.

    ``requested`` is what the caller asked for; ``established`` is what the
    provider could attest. A provider that could not establish a requested
    posture reports it in ``unestablished`` instead of silently widening.
    """

    requested: tuple[str, ...]
    established: tuple[str, ...]
    unestablished: tuple[str, ...] = ()

    @property
    def conformant(self) -> bool:
        return not self.unestablished


@dataclass(frozen=True)
class SandboxProvenance:
    """Where the sandbox ran."""

    provider: str
    adapter: str
    template: str | None = None
    region: str | None = None
    sandbox_id: str | None = None


@dataclass(frozen=True)
class SandboxResult:
    """The outcome of one sandbox invocation."""

    contract_version: str
    request_id: str
    attempt_id: str
    status: str
    provenance: SandboxProvenance
    attested_posture: AttestedPosture
    exit_code: int | None = None
    reason: str | None = None
    failure_class: str | None = None
    stdout: bytes = b""
    stderr: bytes = b""
    output_truncated: bool = False
    artifact_manifest: tuple[ArtifactEntry, ...] = ()
    mutation_manifest: tuple[MutationEntry, ...] = ()
    resource_usage: Mapping[str, Any] = field(default_factory=dict)
    teardown_status: str = "unknown"
    teardown_warning: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == STATUS_COMPLETED

    @property
    def boundary_failed(self) -> bool:
        return self.status == STATUS_BOUNDARY_FAILED


@runtime_checkable
class SandboxProvider(Protocol):
    """
    A provider that can execute a bounded request.

    Implementations must:

    * declare the postures they can establish before allocating anything;
    * refuse (not downgrade) a request naming an unsupported posture;
    * attest the posture they established in the result;
    * tear the sandbox down on every path, including failure and timeout.
    """

    name: str

    def supported_postures(self) -> tuple[str, ...]:
        """Postures this provider can establish."""

    def execute(self, request: SandboxRequest) -> SandboxResult:
        """Execute one request and return its result."""


__all__ = [
    "ArtifactEntry",
    "ArtifactPolicy",
    "AttestedPosture",
    "FAILURE_CLASS_BOUNDARY",
    "FAILURE_CLASS_EXECUTION",
    "KNOWN_POSTURES",
    "NETWORK_MODE_ALLOWLIST",
    "NETWORK_MODE_DENY",
    "POSTURE_CPU_LIMIT",
    "POSTURE_EGRESS_ALLOWLIST",
    "POSTURE_EGRESS_DENY",
    "POSTURE_MEMORY_LIMIT",
    "POSTURE_READ_ONLY_WORKSPACE",
    "POSTURE_SECRET_ISOLATION",
    "POSTURE_STORAGE_CEILING",
    "POSTURE_TEARDOWN",
    "POSTURE_TIMEOUT",
    "SANDBOX_CONTRACT_VERSION",
    "STATUS_BOUNDARY_FAILED",
    "STATUS_CANCELLED",
    "STATUS_COMPLETED",
    "STATUS_DENIED",
    "STATUS_FAILED",
    "STATUS_TIMEOUT",
    "SandboxBoundaryError",
    "SandboxError",
    "SandboxExecutionError",
    "SandboxPolicyDenied",
    "SandboxProvenance",
    "SandboxProvider",
    "SandboxRequest",
    "SandboxResult",
    "SandboxTimeout",
    "MutationEntry",
    "NetworkPosture",
    "ResourcePosture",
    "SecretPosture",
    "WorkspaceMaterialization",
]
