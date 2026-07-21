"""Negative tests for Codexify's operational logging boundary."""

from __future__ import annotations

import logging

from guardian.utils.log_safety import install_safe_logging


def _emit_test_log(
    level: int, message: str, *args: object, **kwargs: object
) -> None:
    install_safe_logging()
    logging.getLogger("guardian.cwc.logging.test").log(
        level, message, *args, **kwargs
    )


def test_assistant_and_user_content_are_absent_from_logs(caplog):
    assistant_text = "ASSISTANT_CONTENT_SENTINEL do not log this response"
    user_prompt = "USER_PROMPT_SENTINEL do not log this request"

    with caplog.at_level(logging.DEBUG):
        _emit_test_log(
            logging.DEBUG,
            "[llm] assistant_text=%s prompt=%s",
            assistant_text,
            user_prompt,
        )

    assert assistant_text not in caplog.text
    assert user_prompt not in caplog.text


def test_provider_bodies_and_credentials_are_absent_from_logs(caplog):
    response_body = "PROVIDER_RESPONSE_BODY_SENTINEL"
    api_key = "API_KEY_SENTINEL"
    bearer = "BEARER_TOKEN_SENTINEL"

    with caplog.at_level(logging.DEBUG):
        _emit_test_log(
            logging.ERROR,
            "provider response body=%s headers=%s",
            response_body,
            {"Authorization": f"Bearer {api_key}", "Cookie": bearer},
        )
        _emit_test_log(
            logging.ERROR,
            "Authorization: Bearer %s?api_key=%s",
            bearer,
            api_key,
        )

    assert response_body not in caplog.text
    assert api_key not in caplog.text
    assert bearer not in caplog.text


def test_tool_arguments_and_outputs_are_absent_from_logs(caplog):
    tool_args = "TOOL_ARGUMENTS_SENTINEL"
    tool_output = "TOOL_OUTPUT_BODY_SENTINEL"

    with caplog.at_level(logging.DEBUG):
        _emit_test_log(
            logging.WARNING,
            "tool args=%s output=%s",
            {"query": tool_args},
            {"body": tool_output},
        )

    assert tool_args not in caplog.text
    assert tool_output not in caplog.text


def test_exception_diagnostics_are_useful_but_content_free(caplog):
    exception_secret = "EXCEPTION_CONTENT_SENTINEL"

    with caplog.at_level(logging.DEBUG):
        try:
            raise TimeoutError(exception_secret)
        except TimeoutError:
            _emit_test_log(
                logging.ERROR,
                "provider request failed task_id=%s request_id=%s turn_id=%s",
                "task-cwc-004",
                "request-cwc-004",
                "turn-cwc-004",
                exc_info=True,
            )

    assert exception_secret not in caplog.text
    assert "task-cwc-004" in caplog.text
    assert "request-cwc-004" in caplog.text
    assert "turn-cwc-004" in caplog.text
    assert "exception_type=TimeoutError" in caplog.text
    assert "failure_class=timeout" in caplog.text


def test_terminal_integrity_metadata_keeps_correlation_without_output(caplog):
    terminal_output = "TERMINAL_OUTPUT_SENTINEL"

    with caplog.at_level(logging.DEBUG):
        _emit_test_log(
            logging.ERROR,
            "[task] failed task_id=%s turn_id=%s failure_kind=%s output=%s",
            "task-terminal-cwc-004",
            "turn-terminal-cwc-004",
            "stream_incomplete",
            terminal_output,
        )

    assert terminal_output not in caplog.text
    assert "task-terminal-cwc-004" in caplog.text
    assert "turn-terminal-cwc-004" in caplog.text
    assert "failure_kind=stream_incomplete" in caplog.text


def test_url_query_credentials_are_removed_but_endpoint_identity_remains(
    caplog,
):
    with caplog.at_level(logging.DEBUG):
        _emit_test_log(
            logging.INFO,
            "provider request endpoint=%s provider=%s model=%s",
            "https://provider.example/v1/chat?api_key=URL_SECRET_SENTINEL",
            "local",
            "model-cwc-004",
        )

    assert "URL_SECRET_SENTINEL" not in caplog.text
    assert "https://provider.example/v1" in caplog.text
    assert "provider=local" in caplog.text
    assert "model=model-cwc-004" in caplog.text


def test_freeform_and_credential_fields_fail_closed(caplog):
    freeform_content = "FREEFORM_CONTENT_SENTINEL"
    extra_secret = "EXTRA_SECRET_SENTINEL"

    with caplog.at_level(logging.DEBUG):
        _emit_test_log(
            logging.WARNING,
            f"[provider] {freeform_content}",
        )
        _emit_test_log(
            logging.ERROR,
            "credential token=%s",
            123456789,
            extra={"api_key": extra_secret},
        )

    assert freeform_content not in caplog.text
    assert extra_secret not in caplog.text
    assert "log_event=<redacted>" in caplog.text
