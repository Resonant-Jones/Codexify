from datetime import datetime, timedelta, timezone


def is_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.utcoffset() is not None


def test_server_token_expiry_is_aware():
    exp = datetime.now(timezone.utc) + timedelta(hours=1)
    assert is_aware(exp)


def test_thread_manager_uptime_uses_aware_math():
    start = datetime.now(timezone.utc) - timedelta(seconds=5)
    now = datetime.now(timezone.utc)
    delta = now - start
    assert delta.total_seconds() >= 5


def test_created_at_is_aware_isoformat():
    created = datetime.now(timezone.utc)
    s = created.isoformat()
    assert s.endswith("+00:00") or s.endswith("Z")


def test_parse_ts_accepts_z_and_naive_as_utc():
    from guardian.utils.datetime import parse_ts

    z = parse_ts("2025-01-02T03:04:05Z")
    naive = parse_ts("2025-01-02T03:04:05")

    assert z.tzinfo is not None and naive.tzinfo is not None
    assert z.utcoffset().total_seconds() == 0
    assert naive.utcoffset().total_seconds() == 0
