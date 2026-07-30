#!/usr/bin/env python3
"""Authenticated, provider-specific proof for the private-preview origin."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol


EXPECTED_PROFILE = "v1-whooshd-deepseek-web"
LOCAL_PROVIDER = "local"
DEEPSEEK_PROVIDER = "deepseek"
UNRELATED_CLOUD_PROVIDERS = {
    "openai",
    "groq",
    "minimax",
    "alibaba",
    "anthropic",
    "gemini",
}
TERMINAL_EVENT_TYPES = {
    "task.completed",
    "task.failed",
    "task.cancelled",
}
SECRET_KEY_MARKERS = (
    "api_key",
    "authorization",
    "cookie",
    "jwt",
    "password",
    "secret",
    "session",
    "token",
)


class ProofError(RuntimeError):
    def __init__(self, classification: str, message: str):
        self.classification = classification
        super().__init__(message)


class ProofTransport(Protocol):
    def request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    def stream_task_events(
        self, task_id: str, *, timeout_seconds: float
    ) -> list[dict[str, Any]]: ...


def _safe_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if any(marker in lowered for marker in SECRET_KEY_MARKERS):
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = _safe_json_value(raw_value)
        return sanitized
    if isinstance(value, list):
        return [_safe_json_value(item) for item in value]
    return value


def _json_object(raw: bytes, *, path: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProofError(
            "provider_unavailable", f"{path} returned invalid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise ProofError(
            "provider_unavailable", f"{path} returned a non-object payload"
        )
    return payload


class UrllibProofTransport:
    def __init__(
        self,
        *,
        base_url: str,
        session_token: str,
        request_timeout_seconds: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.request_timeout_seconds = request_timeout_seconds
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json",
            "User-Agent": "codexify-private-preview-provider-proof/1",
        }

    def request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = (
            json.dumps(payload, separators=(",", ":")).encode("utf-8")
            if payload is not None
            else None
        )
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers=self._headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.request_timeout_seconds
            ) as response:
                return _json_object(response.read(), path=path)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace").lower()
            if exc.code in {401, 403}:
                classification = (
                    "egress_denied"
                    if "egress" in body
                    else "provider_unauthorized"
                )
            elif "credential" in body or "api_key" in body:
                classification = "credential_missing"
            elif "worker" in body:
                classification = "worker_unavailable"
            elif "queue" in body or "redis" in body:
                classification = "queue_unhealthy"
            else:
                classification = "provider_unavailable"
            raise ProofError(
                classification,
                f"{method} {path} failed with HTTP {exc.code}",
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProofError(
                "provider_unavailable",
                f"{method} {path} could not reach the preview origin",
            ) from exc

    def stream_task_events(
        self, task_id: str, *, timeout_seconds: float
    ) -> list[dict[str, Any]]:
        request = urllib.request.Request(
            f"{self.base_url}/api/tasks/{task_id}/events?last_id=0-0",
            headers={
                **self._headers,
                "Accept": "text/event-stream",
            },
            method="GET",
        )
        events: list[dict[str, Any]] = []
        event_type = ""
        data_lines: list[str] = []
        deadline = time.monotonic() + timeout_seconds
        try:
            with urllib.request.urlopen(
                request, timeout=timeout_seconds
            ) as response:
                while time.monotonic() < deadline:
                    raw_line = response.readline()
                    if not raw_line:
                        break
                    line = raw_line.decode("utf-8", errors="replace").rstrip(
                        "\r\n"
                    )
                    if not line:
                        if event_type:
                            try:
                                data = json.loads("\n".join(data_lines) or "{}")
                            except json.JSONDecodeError:
                                data = {}
                            event = {
                                "type": event_type,
                                "data": data if isinstance(data, dict) else {},
                            }
                            events.append(event)
                            if event_type in TERMINAL_EVENT_TYPES:
                                return events
                        event_type = ""
                        data_lines = []
                    elif line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line.split(":", 1)[1].lstrip())
        except urllib.error.HTTPError as exc:
            classification = (
                "provider_unauthorized"
                if exc.code in {401, 403}
                else "accepted_but_not_completed"
            )
            raise ProofError(
                classification,
                f"task event stream failed with HTTP {exc.code}",
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ProofError(
                "accepted_but_not_completed",
                "task event stream ended before terminal evidence",
            ) from exc
        return events


def _details(payload: dict[str, Any]) -> dict[str, Any]:
    details = payload.get("details")
    return details if isinstance(details, dict) else payload


def _provider_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    providers = catalog.get("providers")
    if not isinstance(providers, list):
        raise ProofError(
            "provider_unavailable", "catalog did not return a provider list"
        )
    result: dict[str, dict[str, Any]] = {}
    for entry in providers:
        if not isinstance(entry, dict):
            continue
        provider_id = str(entry.get("id") or "").strip().lower()
        if provider_id:
            result[provider_id] = entry
    return result


def _model_ids(provider: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for entry in provider.get("models") or []:
        if isinstance(entry, dict):
            model_id = str(entry.get("id") or "").strip()
            if model_id:
                result.add(model_id)
    return result


def _execution_from_message(message: dict[str, Any]) -> dict[str, Any] | None:
    execution = message.get("execution")
    if isinstance(execution, dict):
        return execution
    for key in ("metadata", "extra_meta"):
        metadata = message.get(key)
        if isinstance(metadata, dict) and isinstance(
            metadata.get("execution"), dict
        ):
            return metadata["execution"]
    return None


def _fallback_triggered(payload: dict[str, Any]) -> bool:
    if bool(payload.get("fallback_triggered")):
        return True
    completion_truth = payload.get("completion_truth")
    return bool(
        isinstance(completion_truth, dict)
        and completion_truth.get("fallback_attempted")
    )


@dataclass(frozen=True)
class TurnProof:
    provider: str
    model: str
    thread_id: int
    task_id: str
    terminal_event: str
    attempted_provider: str
    attempted_model: str
    final_provider: str
    final_model: str
    persisted_assistant_count: int
    fallback_occurred: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "thread_id": self.thread_id,
            "task_id": self.task_id,
            "terminal_event": self.terminal_event,
            "attempted_provider": self.attempted_provider,
            "attempted_model": self.attempted_model,
            "final_provider": self.final_provider,
            "final_model": self.final_model,
            "persisted_assistant_count": self.persisted_assistant_count,
            "fallback_occurred": self.fallback_occurred,
        }


class PrivatePreviewProviderProof:
    def __init__(
        self,
        transport: ProofTransport,
        *,
        local_model: str,
        deepseek_model: str,
        sentinel: str,
        proof_user_id: str | None = None,
        task_timeout_seconds: float = 180.0,
    ):
        self.transport = transport
        self.local_model = local_model
        self.deepseek_model = deepseek_model
        self.sentinel = sentinel
        self.proof_user_id = proof_user_id
        self.task_timeout_seconds = task_timeout_seconds

    def _preflight(self) -> dict[str, Any]:
        health = self.transport.request_json("GET", "/health")
        health_details = _details(health)
        supported_profile = health_details.get("supported_profile")
        profile_name = (
            str(supported_profile.get("name") or "").strip()
            if isinstance(supported_profile, dict)
            else ""
        )
        if profile_name != EXPECTED_PROFILE:
            raise ProofError(
                "profile_mismatch",
                f"active profile is {profile_name or '<missing>'}, expected {EXPECTED_PROFILE}",
            )

        chat_health = self.transport.request_json("GET", "/health/chat")
        if str(chat_health.get("redis") or "").lower() != "ok":
            raise ProofError("queue_unhealthy", "Redis is not healthy")
        worker = chat_health.get("worker")
        worker_status = (
            str(worker.get("status") or "").lower()
            if isinstance(worker, dict)
            else ""
        )
        if worker_status not in {"alive", "healthy", "ok"}:
            raise ProofError(
                "worker_unavailable",
                f"chat worker status is {worker_status or '<missing>'}",
            )

        llm_health = self.transport.request_json("GET", "/api/health/llm")
        llm_details = _details(llm_health)
        if str(llm_details.get("provider") or "").lower() != LOCAL_PROVIDER:
            raise ProofError(
                "profile_mismatch", "active provider is not the local default"
            )
        provider_runtime = llm_details.get("provider_runtime")
        if not (
            isinstance(provider_runtime, dict)
            and provider_runtime.get("enabled") is True
        ):
            raise ProofError(
                "provider_unavailable", "Whoosh'd local provider is unavailable"
            )

        catalog = self.transport.request_json(
            "GET", "/api/llm/catalog?include=all"
        )
        providers = _provider_map(catalog)
        local = providers.get(LOCAL_PROVIDER)
        deepseek = providers.get(DEEPSEEK_PROVIDER)
        if local is None or local.get("authorized") is not True:
            raise ProofError(
                "provider_unauthorized", "Whoosh'd local provider is unauthorized"
            )
        if local.get("available") is not True or local.get("enabled") is not True:
            raise ProofError(
                "provider_unavailable", "Whoosh'd local provider is unavailable"
            )
        if self.local_model not in _model_ids(local):
            raise ProofError(
                "provider_unavailable",
                f"expected local model {self.local_model!r} is absent",
            )
        if deepseek is None or deepseek.get("authorized") is not True:
            reason = (
                str((deepseek or {}).get("disabled_reason") or "").lower()
            )
            classification = (
                "credential_missing"
                if "credential" in reason
                else "provider_unauthorized"
            )
            raise ProofError(classification, "DeepSeek is unauthorized")
        if (
            deepseek.get("available") is not True
            or deepseek.get("enabled") is not True
        ):
            reason = str(deepseek.get("disabled_reason") or "").lower()
            classification = (
                "egress_denied" if "egress" in reason else "provider_unavailable"
            )
            raise ProofError(classification, "DeepSeek is unavailable")
        if self.deepseek_model not in _model_ids(deepseek):
            raise ProofError(
                "provider_unavailable",
                f"expected DeepSeek model {self.deepseek_model!r} is absent",
            )

        unauthorized_violation = sorted(
            provider_id
            for provider_id in UNRELATED_CLOUD_PROVIDERS
            if providers.get(provider_id, {}).get("authorized") is True
        )
        if unauthorized_violation:
            raise ProofError(
                "provider_unauthorized",
                "unrelated cloud providers are authorized: "
                + ", ".join(unauthorized_violation),
            )
        return {
            "profile": profile_name,
            "health": str(health.get("status") or "unknown"),
            "chat": str(chat_health.get("status") or "unknown"),
            "llm": str(llm_health.get("status") or "unknown"),
            "catalog_providers": sorted(providers),
        }

    def _prove_turn(self, *, provider: str, model: str) -> TurnProof:
        body: dict[str, Any] = {
            "title": f"Private preview proof {provider} {self.sentinel}",
            "providerId": provider,
            "modelId": model,
        }
        if self.proof_user_id:
            body["user_id"] = self.proof_user_id
        created = self.transport.request_json(
            "POST", "/api/chat/threads", body
        )
        raw_thread_id = created.get("id")
        try:
            thread_id = int(raw_thread_id)
        except (TypeError, ValueError) as exc:
            raise ProofError(
                "persistence_mismatch", "thread creation returned no valid id"
            ) from exc

        message_body: dict[str, Any] = {
            "role": "user",
            "content": (
                f"Reply with this exact proof sentinel and nothing else: "
                f"{self.sentinel}-{provider}"
            ),
        }
        if self.proof_user_id:
            message_body["user_id"] = self.proof_user_id
        self.transport.request_json(
            "POST", f"/api/chat/{thread_id}/messages", message_body
        )
        completion = self.transport.request_json(
            "POST",
            f"/api/chat/{thread_id}/complete",
            {
                "provider": provider,
                "model": model,
                "turn_id": f"private-preview-proof-{uuid.uuid4()}",
                "depth_mode": "shallow",
            },
        )
        task_id = str(completion.get("task_id") or "").strip()
        if not task_id:
            raise ProofError(
                "accepted_but_not_completed",
                "completion acceptance returned no task id",
            )
        events = self.transport.stream_task_events(
            task_id, timeout_seconds=self.task_timeout_seconds
        )
        terminal = next(
            (
                event
                for event in events
                if str(event.get("type") or "") in TERMINAL_EVENT_TYPES
            ),
            None,
        )
        if terminal is None:
            raise ProofError(
                "accepted_but_not_completed",
                f"task {task_id} produced no terminal event",
            )
        terminal_type = str(terminal.get("type") or "")
        terminal_data = terminal.get("data")
        if terminal_type != "task.completed" or not isinstance(
            terminal_data, dict
        ):
            raise ProofError(
                "provider_unavailable",
                f"task {task_id} terminated as {terminal_type}",
            )

        attempted_provider = str(
            terminal_data.get("attempted_provider") or ""
        ).strip()
        attempted_model = str(
            terminal_data.get("attempted_model") or ""
        ).strip()
        final_provider = str(
            terminal_data.get("final_provider")
            or terminal_data.get("provider")
            or ""
        ).strip()
        final_model = str(
            terminal_data.get("final_model")
            or terminal_data.get("model")
            or ""
        ).strip()
        fallback_occurred = _fallback_triggered(terminal_data)
        if fallback_occurred:
            raise ProofError(
                "provider_fallback_occurred",
                f"{provider} proof completed through fallback",
            )
        if attempted_provider != provider or attempted_model != model:
            raise ProofError(
                "provider_fallback_occurred",
                f"{provider} proof attempted {attempted_provider}/{attempted_model}",
            )
        if final_provider != provider or final_model != model:
            raise ProofError(
                "provider_fallback_occurred",
                f"{provider} proof finalized as {final_provider}/{final_model}",
            )

        persisted = self.transport.request_json(
            "GET", f"/api/chat/{thread_id}/messages?limit=50&offset=0"
        )
        messages = persisted.get("messages")
        if not isinstance(messages, list):
            raise ProofError(
                "persistence_mismatch", "message readback returned no list"
            )
        assistants = [
            item
            for item in messages
            if isinstance(item, dict)
            and str(item.get("role") or "").strip().lower() == "assistant"
        ]
        if len(assistants) != 1:
            classification = (
                "transcript_duplication"
                if len(assistants) > 1
                else "persistence_mismatch"
            )
            raise ProofError(
                classification,
                f"expected one assistant response, found {len(assistants)}",
            )
        assistant = assistants[0]
        terminal_message_id = str(terminal_data.get("message_id") or "").strip()
        persisted_message_id = str(assistant.get("id") or "").strip()
        if (
            terminal_message_id
            and persisted_message_id
            and terminal_message_id != persisted_message_id
        ):
            raise ProofError(
                "persistence_mismatch",
                "terminal and persisted assistant message ids disagree",
            )
        persisted_execution = _execution_from_message(assistant)
        if persisted_execution is not None:
            persisted_attempted_provider = str(
                persisted_execution.get("attempted_provider") or ""
            ).strip()
            persisted_attempted_model = str(
                persisted_execution.get("attempted_model") or ""
            ).strip()
            persisted_final_provider = str(
                persisted_execution.get("final_provider") or ""
            ).strip()
            persisted_final_model = str(
                persisted_execution.get("final_model") or ""
            ).strip()
            if (
                persisted_attempted_provider != attempted_provider
                or persisted_attempted_model != attempted_model
                or persisted_final_provider != final_provider
                or persisted_final_model != final_model
            ):
                raise ProofError(
                    "persistence_mismatch",
                    "terminal and persisted execution metadata disagree",
                )

        return TurnProof(
            provider=provider,
            model=model,
            thread_id=thread_id,
            task_id=task_id,
            terminal_event=terminal_type,
            attempted_provider=attempted_provider,
            attempted_model=attempted_model,
            final_provider=final_provider,
            final_model=final_model,
            persisted_assistant_count=len(assistants),
            fallback_occurred=fallback_occurred,
        )

    def run(self) -> dict[str, Any]:
        preflight = self._preflight()
        local = self._prove_turn(
            provider=LOCAL_PROVIDER, model=self.local_model
        )
        deepseek = self._prove_turn(
            provider=DEEPSEEK_PROVIDER, model=self.deepseek_model
        )
        return {
            "ok": True,
            "classification": "locally_dual_provider_proven",
            "profile": EXPECTED_PROFILE,
            "sentinel": self.sentinel,
            "preflight": preflight,
            "turns": {
                LOCAL_PROVIDER: local.as_dict(),
                DEEPSEEK_PROVIDER: deepseek.as_dict(),
            },
        }


def _read_session_token(path: Path) -> str:
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ProofError(
            "provider_unauthorized", "session token file could not be read"
        ) from exc
    if not token:
        raise ProofError(
            "provider_unauthorized", "session token file is empty"
        )
    return token


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prove one explicit Whoosh'd turn and one explicit DeepSeek turn "
            "through the private-preview origin."
        )
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv(
            "PRIVATE_PREVIEW_BASE_URL", "http://127.0.0.1:8081"
        ),
    )
    parser.add_argument(
        "--session-token-file",
        type=Path,
        default=(
            Path(os.environ["PRIVATE_PREVIEW_SESSION_TOKEN_FILE"])
            if os.getenv("PRIVATE_PREVIEW_SESSION_TOKEN_FILE")
            else None
        ),
        required=not bool(os.getenv("PRIVATE_PREVIEW_SESSION_TOKEN_FILE")),
        help="Protected file containing an existing Guardian session token.",
    )
    parser.add_argument(
        "--local-model",
        default=os.getenv(
            "PRIVATE_PREVIEW_LOCAL_MODEL", "gemma-4-12b-it-qat-4bit"
        ),
    )
    parser.add_argument(
        "--deepseek-model",
        default=os.getenv(
            "PRIVATE_PREVIEW_DEEPSEEK_MODEL", "deepseek-v4-flash"
        ),
    )
    parser.add_argument(
        "--sentinel",
        default=os.getenv(
            "PRIVATE_PREVIEW_PROOF_SENTINEL",
            f"codexify-private-preview-{uuid.uuid4().hex[:12]}",
        ),
    )
    parser.add_argument(
        "--proof-user-id",
        default=os.getenv("PRIVATE_PREVIEW_PROOF_USER_ID") or None,
    )
    parser.add_argument(
        "--task-timeout-seconds",
        type=float,
        default=float(
            os.getenv("PRIVATE_PREVIEW_TASK_TIMEOUT_SECONDS", "180")
        ),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        session_token = _read_session_token(args.session_token_file)
        transport = UrllibProofTransport(
            base_url=args.base_url,
            session_token=session_token,
        )
        proof = PrivatePreviewProviderProof(
            transport,
            local_model=args.local_model,
            deepseek_model=args.deepseek_model,
            sentinel=args.sentinel,
            proof_user_id=args.proof_user_id,
            task_timeout_seconds=args.task_timeout_seconds,
        )
        summary = proof.run()
    except ProofError as exc:
        summary = {
            "ok": False,
            "classification": exc.classification,
            "error": str(exc),
        }
        print(
            json.dumps(
                _safe_json_value(summary), sort_keys=True, separators=(",", ":")
            )
        )
        return 1

    print(
        json.dumps(
            _safe_json_value(summary), sort_keys=True, separators=(",", ":")
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
