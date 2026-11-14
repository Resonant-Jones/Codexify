"""Synthetic callback sentinels must not enter backend or ingress logs."""

import logging
from pathlib import Path

import pytest
from uvicorn.logging import AccessFormatter

from guardian.utils.log_safety import sanitize_log_text, sanitize_record


@pytest.mark.parametrize("provider", ["notion", "github-knowledge"])
@pytest.mark.parametrize(
    "query",
    [
        "state=SYNTHETIC_STATE&code=SYNTHETIC_CODE",
        "%73tate=SYNTHETIC_STATE&%63ode=SYNTHETIC_CODE",
        "error=denied&error_description=SYNTHETIC_ERROR&extra=SYNTHETIC_EXTRA",
    ],
)
def test_entire_callback_query_is_redacted(provider, query):
    url = f"https://preview.example/api/connect/{provider}/oauth/callback?{query}"
    safe = sanitize_log_text(f"GET {url} HTTP/1.1")
    assert "SYNTHETIC" not in safe
    assert sanitize_log_text(safe) == safe
    assert f"/api/connect/{provider}/oauth/callback" in safe
    for msg, args in [
        ("endpoint=%s", (url,)),
        ("source=%s", (url,)),
        (f"callback={url} status=%d", (400,)),
        (url, ()),
    ]:
        record = logging.LogRecord(
            "guardian.oauth", logging.INFO, __file__, 0, msg, args, None
        )
        for _ in range(2):
            sanitize_record(record, force=True)
            assert "SYNTHETIC" not in record.getMessage()


def test_uvicorn_formatter_preserves_structure_without_callback_values():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        0,
        '%s - "%s %s HTTP/%s" %d',
        (
            "127.0.0.1:1234",
            "GET",
            "/api/connect/notion/oauth/callback?code=SYNTHETIC_CODE&state=SYNTHETIC_STATE",
            "1.1",
            400,
        ),
        None,
    )
    sanitize_record(record)
    rendered = AccessFormatter(
        "%(request_line)s %(status_code)s", use_colors=False
    ).format(record)
    assert "SYNTHETIC" not in rendered
    assert "400" in rendered


def test_standalone_state_query_is_redacted():
    assert "SYNTHETIC" not in sanitize_log_text("GET /other?state=SYNTHETIC_STATE")


def test_preview_nginx_uses_only_query_free_metadata():
    config = Path("docker/private-preview/nginx.conf").read_text()
    declaration = config.split("log_format preview_metadata ", 1)[1].split(";", 1)[0]
    assert "$uri" in declaration
    for forbidden in (
        "$request'",
        "$request ",
        "$request_uri",
        "$args",
        "$query_string",
        "$http_",
        "$upstream_http_",
    ):
        assert forbidden not in declaration
    assert "access_log /var/log/nginx/access.log preview_metadata;" in config
    for diagnostic in (
        "$time_iso8601",
        "$request_id",
        "$upstream_status",
        "$upstream_connect_time",
        "$upstream_header_time",
        "$upstream_response_time",
    ):
        assert diagnostic in declaration
    # The public server is the explicit default: early request parse errors
    # inherit its suppression. Do not suppress unrelated internal/process logs.
    public_start = config.index("server {")
    internal_start = config.rindex("server {")
    public = config[public_start:internal_start]
    internal = config[internal_start:]
    assert "listen 8080 default_server;" in public
    assert "error_log /dev/null;" in public
    assert "error_log" not in config[:public_start]
    assert "error_log" not in internal
    assert config.count("error_log /dev/null;") == 1
    assert "proxy_pass http://guardian_backend;" in config
    assert "proxy_pass http://guardian_backend$uri" not in config
