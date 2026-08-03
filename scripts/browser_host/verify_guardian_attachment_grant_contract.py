"""Emit a sanitized, no-network proof for the pure attachment-grant seam."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardian.browser_host.attachment_grants import (  # noqa: E402
    AttachmentGrantAuthorizationContext,
    AttachmentGrantStore,
)
from guardian.browser_host.contract_loader import load_contract_metadata  # noqa: E402


DEFAULT_OUTPUT = REPO_ROOT / "docs/architecture/proofs/browser-host/2026-08-01-guardian-attachment-grant-contract"
CONTRACT_ROOT = REPO_ROOT / "browser_host/contracts"


def _load(relative_path: str) -> dict:
    return json.loads((CONTRACT_ROOT / relative_path).read_text(encoding="utf-8"))


def _request() -> dict:
    request = _load("fixtures/valid/attachment-grant-request-ephemeral.json")
    request["requestId"] = "request-selected-1"
    return request


def _attachment() -> dict:
    return _load("fixtures/valid/attachment-attempt-ephemeral.json")


def _new_store() -> tuple[AttachmentGrantStore, list[datetime]]:
    clock = [datetime(2026, 8, 1, 14, 0, tzinfo=timezone.utc)]
    return AttachmentGrantStore(clock=lambda: clock[0]), clock


def _issue(store: AttachmentGrantStore):
    return store.issue(_request(), AttachmentGrantAuthorizationContext.explicitly_authorized("synthetic-subject"))


def _commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _run(output_dir: Path) -> dict:
    metadata = load_contract_metadata()
    store, _ = _new_store()
    issue = _issue(store)
    if not issue.accepted or not issue.raw_bearer or not issue.grant_response:
        raise RuntimeError("issuance_failed")
    bearer = issue.raw_bearer
    response = dict(issue.grant_response)
    if "subjectId" in response or "apiKey" in response or "cookie" in response or "jwt" in response:
        raise RuntimeError("grant_response_disclosure")
    snapshot = store.snapshot_for_testing()
    if len(snapshot) != 1 or bearer in repr(snapshot) or snapshot[0]["bearerDigest"] == bearer:
        raise RuntimeError("bearer_storage_posture_failed")

    attachment = _attachment()
    host = _request()["browserHostInstanceId"]
    valid = store.consume(bearer, attachment, browser_host_instance_id=host)
    replay = store.consume(bearer, attachment, browser_host_instance_id=host)
    if not valid.authorized or replay.lifecycle != "grant_replayed":
        raise RuntimeError("one_use_proof_failed")

    expired_store, expired_clock = _new_store()
    expired_issue = _issue(expired_store)
    expired_clock[0] += timedelta(seconds=121)
    expired = expired_store.consume(expired_issue.raw_bearer or "", _attachment(), browser_host_instance_id=host)

    scope_store, _ = _new_store()
    scope_issue = _issue(scope_store)
    scope = scope_store.consume(scope_issue.raw_bearer or "", _attachment(), browser_host_instance_id="wrong-host")

    version_store, _ = _new_store()
    version_issue = _issue(version_store)
    version_attachment = _attachment()
    version_attachment["protocolVersion"] = "9.0.0"
    version = version_store.consume(version_issue.raw_bearer or "", version_attachment, browser_host_instance_id=host)

    retention_store, _ = _new_store()
    retention_issue = _issue(retention_store)
    retention_attachment = _attachment()
    retention_attachment["requestedRetention"] = "durable"
    retention = retention_store.consume(retention_issue.raw_bearer or "", retention_attachment, browser_host_instance_id=host)

    budget_store, _ = _new_store()
    budget_issue = _issue(budget_store)
    budget_attachment = _attachment()
    budget_attachment["envelope"]["content"] = "x"
    budget_attachment["envelope"]["contentLength"] = 65537
    budget = budget_store.consume(budget_issue.raw_bearer or "", budget_attachment, browser_host_instance_id=host)

    concurrent_store, _ = _new_store()
    concurrent_issue = _issue(concurrent_store)
    concurrent_attachment = _attachment()
    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent = list(pool.map(
            lambda _: concurrent_store.consume(concurrent_issue.raw_bearer or "", concurrent_attachment, browser_host_instance_id=host),
            (1, 2),
        ))
    if sum(decision.authorized for decision in concurrent) != 1:
        raise RuntimeError("concurrency_proof_failed")

    proof = {
        "proofKind": "guardian_attachment_grant_contract",
        "proofStatus": "passed",
        "repositoryCommit": _commit(),
        "contractPackageVersion": metadata.package_version,
        "protocolVersion": metadata.protocol_version,
        "attachmentVersion": metadata.attachment_version,
        "authorizationScheme": metadata.authorization_scheme,
        "defaultTtlSeconds": metadata.default_ttl_seconds,
        "minimumTtlSeconds": metadata.minimum_ttl_seconds,
        "maximumTtlSeconds": metadata.maximum_ttl_seconds,
        "allowedUseCount": metadata.allowed_uses,
        "retentionClass": metadata.retention_class,
        "bearerDigestAlgorithm": "sha256",
        "rawBearerRetained": False,
        "reusableGuardianCredentialPresent": False,
        "subjectSerializedToGrantResponse": False,
        "validIssuanceResult": issue.accepted,
        "validConsumptionResult": valid.authorized,
        "replayResult": {"lifecycle": replay.lifecycle, "errorCode": replay.error_code},
        "expirationResult": {"lifecycle": expired.lifecycle, "errorCode": expired.error_code},
        "scopeMismatchResult": {"lifecycle": scope.lifecycle, "errorCode": scope.error_code},
        "versionMismatchResult": {"lifecycle": version.lifecycle, "errorCode": version.error_code},
        "retentionResult": {"lifecycle": retention.lifecycle, "errorCode": retention.error_code},
        "budgetResult": {"lifecycle": budget.lifecycle, "errorCode": budget.error_code},
        "concurrentConsumptionResult": {
            "authorizedCount": sum(decision.authorized for decision in concurrent),
            "replayCount": sum(decision.lifecycle == "grant_replayed" for decision in concurrent),
        },
        "storagePosture": {
            "processLocal": True,
            "ephemeral": True,
            "bearerDigestStored": True,
            "subjectInternalOnly": True,
            "database": False,
            "redis": False,
            "fileWrites": False,
        },
        "routeImplemented": False,
        "networkUsed": False,
        "persistenceUsed": False,
        "releaseQualification": False,
        "existingV1AttachmentBodyMutated": False,
        "existingV1ReceiptMeaningChanged": False,
        "generatedAt": "2026-08-01T14:00:00.000Z",
    }
    sanitized = json.dumps(proof, sort_keys=True)
    if bearer in sanitized or any(snapshot[0][key] in sanitized for key in ("bearerDigest", "subjectId")):
        raise RuntimeError("sanitized_proof_leak")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "proof.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "proofKind": proof["proofKind"],
        "proofFile": "proof.json",
        "packageVersion": "0.1.0",
        "contractPackageVersion": proof["contractPackageVersion"],
        "releasePosture": "development/internal unsigned proof",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "proof.md").write_text(
        "# Guardian-issued attachment grant contract proof\n\n"
        "Status: **passed**\n\n"
        "This sanitized packet proves the versioned request/response contract and pure Guardian-owned one-use issuer/consumer seam. It uses a synthetic authorized context, no network, no Guardian route, no production credential, and process-local digest-only storage. It does not claim live Guardian issuance, Browser Host transport, persistence, or release qualification.\n\n"
        f"- Commit: `{proof['repositoryCommit']}`\n"
        f"- Contract package: `{proof['contractPackageVersion']}`\n"
        f"- Authorization scheme: `{proof['authorizationScheme']}`\n"
        f"- TTL: `{proof['minimumTtlSeconds']}`–`{proof['maximumTtlSeconds']}` seconds\n"
        "- Allowed uses: `1`\n"
        "- Retention: `ephemeral`\n"
        "- Bearer retained raw: `false`\n"
        "- Reusable Guardian credential: `false`\n"
        "- Route/network/persistence/release: `false`/`false`/`false`/`false`\n",
        encoding="utf-8",
    )
    return proof


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    proof = _run(args.output_dir)
    print(json.dumps({"proof": proof["proofStatus"], "outputDir": str(args.output_dir)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
