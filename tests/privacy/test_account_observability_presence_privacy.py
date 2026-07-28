from __future__ import annotations

from guardian.account_observability.schemas import HeartbeatRequest
from guardian.db.models import AccountObservabilityPresenceSession


def test_presence_model_contains_no_prohibited_dimensions() -> None:
    prohibited = {
        "raw_ip",
        "hashed_ip",
        "ip_address",
        "user_agent",
        "fingerprint",
        "page_path",
        "route_path",
        "message_id",
        "thread_id",
        "project_id",
        "prompt",
        "response_content",
        "referrer_url",
        "latitude",
        "longitude",
        "city",
        "postal_code",
        "asn",
        "isp",
    }
    assert not prohibited & {
        column.name
        for column in AccountObservabilityPresenceSession.__table__.columns
    }


def test_heartbeat_schema_has_no_client_timestamp_or_dimensions() -> None:
    assert set(HeartbeatRequest.model_fields) == set()
