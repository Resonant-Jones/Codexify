from __future__ import annotations

import pytest


def _evaluate_upload_embed_retrieve_proof(
    *,
    upload_ok: bool,
    detail_read_ok: bool,
    embedding_ready: bool,
    sentinel_retrieval_ok: bool,
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if not upload_ok:
        failures.append("upload_failed")
    if not detail_read_ok:
        failures.append("document_detail_readback_missing")
    if not embedding_ready:
        failures.append("embedding_not_ready")
    if not sentinel_retrieval_ok:
        failures.append("sentinel_retrieval_missing")
    return (len(failures) == 0, failures)


def test_upload_success_alone_is_not_full_proof():
    passed, failures = _evaluate_upload_embed_retrieve_proof(
        upload_ok=True,
        detail_read_ok=False,
        embedding_ready=False,
        sentinel_retrieval_ok=False,
    )
    assert passed is False
    assert failures == [
        "document_detail_readback_missing",
        "embedding_not_ready",
        "sentinel_retrieval_missing",
    ]


def test_document_readback_is_required():
    passed, failures = _evaluate_upload_embed_retrieve_proof(
        upload_ok=True,
        detail_read_ok=False,
        embedding_ready=True,
        sentinel_retrieval_ok=True,
    )
    assert passed is False
    assert "document_detail_readback_missing" in failures


def test_embedding_readiness_is_required():
    passed, failures = _evaluate_upload_embed_retrieve_proof(
        upload_ok=True,
        detail_read_ok=True,
        embedding_ready=False,
        sentinel_retrieval_ok=True,
    )
    assert passed is False
    assert "embedding_not_ready" in failures


def test_sentinel_retrieval_is_required():
    passed, failures = _evaluate_upload_embed_retrieve_proof(
        upload_ok=True,
        detail_read_ok=True,
        embedding_ready=True,
        sentinel_retrieval_ok=False,
    )
    assert passed is False
    assert "sentinel_retrieval_missing" in failures


def test_full_upload_embed_retrieve_proof_requires_all_contract_evidence():
    passed, failures = _evaluate_upload_embed_retrieve_proof(
        upload_ok=True,
        detail_read_ok=True,
        embedding_ready=True,
        sentinel_retrieval_ok=True,
    )
    assert passed is True
    assert failures == []
