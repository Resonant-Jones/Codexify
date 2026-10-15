import hashlib

import pytest

from guardian.conversation_origin import ConversationOriginSystem as Origin
from guardian.core.dependencies import RequestUserScope
from guardian.services.chronicle_interpretation_authorization import (
    ChronicleInterpretationGrant,
)
from guardian.services.chronicle_model_exposure import (
    ModelExposureError,
    ReviewedEvidenceReference,
    authorize_reviewed_evidence,
    build_local_evidence_messages,
    invoke_local_model,
    validate_preview_output,
)
from guardian.services.imported_history_evidence import (
    EvidenceCoverage,
    ImportedExcerpt,
    ImportedHistoryEvidence,
    InspectionLimits,
)


def excerpt(text="recorded decision"):
    return ImportedExcerpt(
        1,
        10,
        101,
        Origin.OPENAI,
        "source",
        "source-message",
        True,
        "user",
        "user",
        "text",
        "user",
        "text",
        text,
        False,
        "2020-01-01T00:00:00+00:00",
        "raw_message.create_time",
        "2020-01-01T00:00:00+00:00",
        True,
        False,
        "2026-10-09T12:00:00+00:00",
        "2020-01-01T00:00:00+00:00",
        "2020-01-01T00:00:00+00:00",
    )


def bundle(item=None):
    item = item or excerpt()
    return ImportedHistoryEvidence(
        1,
        (10,),
        (Origin.OPENAI,),
        "2026-10-10T00:00:00+00:00",
        (),
        (item,),
        EvidenceCoverage(1, 1, 1, 0, 0, 0, 0, 0, None, True, False),
    )


def grant():
    return ChronicleInterpretationGrant(
        RequestUserScope(user_id="a", account_id="a"),
        "a",
        1,
        (10,),
        (Origin.OPENAI,),
        InspectionLimits(100, 1000, 8192, 262144),
        0,
        "migration_chronicle_preview",
        "recallable_archive",
        ((10, "clear"),) * 4,
    )


def ref(item):
    return ReviewedEvidenceReference(
        item.thread_id,
        item.message_id,
        hashlib.sha256(item.excerpt.encode()).hexdigest(),
        True,
    )


def test_exact_reviewed_digest_builds_lower_authority_envelope():
    item = excerpt()
    admitted = authorize_reviewed_evidence(grant(), bundle(item), [ref(item)])
    messages = build_local_evidence_messages(admitted)
    assert messages[0]["role"] == "system"
    assert "AUTHORIZED HISTORICAL EVIDENCE" in messages[1]["content"]
    assert '"role":"user"' not in messages[1]["content"]


@pytest.mark.parametrize("bad", ["0" * 64, "f" * 64])
def test_digest_and_quote_validation_fail_closed(bad):
    item = excerpt()
    with pytest.raises(ModelExposureError):
        authorize_reviewed_evidence(
            grant(), bundle(item), [ReviewedEvidenceReference(10, 101, bad, True)]
        )
    admitted = authorize_reviewed_evidence(grant(), bundle(item), [ref(item)])
    with pytest.raises(ModelExposureError):
        validate_preview_output(
            {
                "summary": "x",
                "observations": [
                    {
                        "category": "themes",
                        "claim": "x",
                        "citations": [
                            {"thread_id": 10, "message_id": 101, "quote": "fabricated"}
                        ],
                    }
                ],
            },
            admitted,
        )


@pytest.mark.parametrize("approval", [False, "true", 1, None])
def test_missing_or_non_true_message_approval_fails_closed(approval):
    item = excerpt()
    reference = ref(item)
    reference = ReviewedEvidenceReference(
        reference.thread_id, reference.message_id, reference.digest, approval
    )
    with pytest.raises(ModelExposureError, match="approval"):
        authorize_reviewed_evidence(grant(), bundle(item), [reference])


def test_output_citations_are_validated():
    item = excerpt()
    admitted = authorize_reviewed_evidence(grant(), bundle(item), [ref(item)])
    result = validate_preview_output(
        {
            "summary": "A bounded summary",
            "observations": [
                {
                    "category": "decisions",
                    "claim": "A decision was recorded.",
                    "citations": [
                        {"thread_id": 10, "message_id": 101, "quote": item.excerpt}
                    ],
                }
            ],
        },
        admitted,
    )
    assert result["observations"][0]["citations"][0]["origin_system"] == "openai"


def test_local_dispatch_is_strict_and_tool_free():
    captured = {}

    def transport(messages, **kwargs):
        captured["messages"] = messages
        captured["kwargs"] = kwargs
        return {"observations": []}

    invoke_local_model(
        [{"role": "system", "content": "instruction"}], transport=transport
    )
    assert captured["kwargs"] == {
        "provider": "local",
        "tools": [],
        "temperature": 0,
        "max_tokens": 1400,
        "strict_provider_model": True,
        "strict_single_request": True,
    }
