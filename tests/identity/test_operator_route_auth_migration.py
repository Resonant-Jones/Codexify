"""Frozen ADR-092 operator-route migration and credential boundary."""

from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import importlib
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import fastapi.routing as fastapi_routing
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from guardian.core.auth import (
    ACCOUNT_SESSION_PURPOSE,
    OPERATOR_SESSION_PURPOSE,
    issue_session_token,
)
from guardian.core.dependencies import (
    require_account_session,
    require_api_key,
    require_operator_auth,
    require_task_event_read_principal,
)
from guardian.core.hosted_room_session import issue_guest_session_token
from guardian.core.supported_profile import load_supported_profile


# Explicit route-level manifest from the committed classification receipt.
# Each tuple is (HTTP method, full path, handler name).
EXPECTED: dict[str, tuple[tuple[str, str, str], ...]] = {
    "guardian.guardian_api": (
        ("GET", "/api/events", "stream_events"),
        ("GET", "/graph", "get_graph"),
    ),
    "guardian.routes.configuration_inspector": (
        ("GET", "/api/operator/configuration", "get_configuration_snapshot"),
    ),
    "guardian.routes.agent_orchestration": (
        ("POST", "/api/agents/plans", "create_plan"),
        ("POST", "/api/agents/deployments", "create_deployment"),
        ("POST", "/api/agents/deployments/{deployment_id}/runs", "start_run"),
        ("POST", "/api/agents/pi-invocation/dry-run", "pi_invocation_dry_run"),
    ),
    "guardian.routes.backfill": (
        ("GET", "/backfill/status", "backfill_status"),
    ),
    "guardian.routes.coding_work_orders": (
        ("POST", "/api/coding/campaign-runner/goals", "create_campaign_goal"),
        ("GET", "/api/coding/campaign-runner/goals/{goal_id}", "get_campaign_goal"),
        ("POST", "/api/coding/campaign-runner/campaigns", "create_campaign"),
        ("GET", "/api/coding/campaign-runner/campaigns/{campaign_id}", "get_campaign_detail"),
        ("POST", "/api/coding/work-orders", "create_work_order"),
        ("GET", "/api/coding/work-orders", "list_work_orders"),
        ("GET", "/api/coding/work-orders/{work_order_id}", "get_work_order"),
        ("POST", "/api/coding/work-orders/{work_order_id}/cancel", "cancel_work_order"),
        ("GET", "/api/coding/work-orders/{work_order_id}/latest-run", "get_work_order_latest_run"),
        ("POST", "/api/coding/work-orders/{work_order_id}/receipts", "create_work_order_receipt"),
        ("GET", "/api/coding/work-orders/{work_order_id}/receipts", "list_work_order_receipts"),
        ("GET", "/api/coding/work-orders/{work_order_id}/receipts/{receipt_id}", "get_work_order_receipt"),
        ("GET", "/api/coding/orchestrator/next", "get_next_work_order_recommendations"),
    ),
    "guardian.routes.cron": (
        ("POST", "/api/cron/jobs", "create_cron_job"),
        ("GET", "/api/cron/jobs", "list_cron_jobs"),
        ("GET", "/api/cron/jobs/{job_id}", "get_cron_job"),
        ("PATCH", "/api/cron/jobs/{job_id}", "update_cron_job"),
        ("DELETE", "/api/cron/jobs/{job_id}", "delete_cron_job"),
        ("POST", "/api/cron/jobs/{job_id}/trigger", "trigger_cron_job"),
        ("GET", "/api/cron/jobs/{job_id}/runs", "list_cron_runs"),
    ),
    "guardian.routes.delegations": (
        ("POST", "/api/delegations/draft", "create_delegation_draft"),
        ("POST", "/api/delegations/{packet_id}/approve", "approve_delegation_packet"),
        ("GET", "/api/delegations/{delegation_id}/events", "stream_delegation_events"),
        ("POST", "/api/delegations/{delegation_id}/cancel", "cancel_delegation"),
    ),
    "guardian.routes.flows": (
        ("POST", "/api/flows", "create_flow"),
        ("GET", "/api/flows", "list_flows"),
        ("GET", "/api/flows/{flow_id}", "get_flow"),
        ("POST", "/api/flows/import", "import_flow"),
        ("PATCH", "/api/flows/{flow_id}", "patch_flow"),
        ("POST", "/api/flows/{flow_id}/validate", "validate_flow"),
        ("POST", "/api/flows/{flow_id}/run", "run_flow_now"),
        ("GET", "/api/flows/{flow_id}/runs", "list_flow_runs"),
        ("GET", "/api/flows/runs/{run_id}", "get_flow_run"),
    ),
    "guardian.routes.graph": (
        ("GET", "/graph", "get_graph"),
    ),
    "guardian.routes.guardian_delegations": (
        ("GET", "/api/guardian/delegations", "list_guardian_delegations"),
        ("POST", "/api/guardian/delegations", "create_guardian_delegation"),
        ("POST", "/api/guardian/delegations/{intent_id}/approve", "approve_guardian_delegation"),
        ("POST", "/api/guardian/delegations/{intent_id}/cancel", "cancel_guardian_delegation"),
        ("GET", "/api/guardian/delegations/{intent_id}", "get_guardian_delegation"),
        ("GET", "/api/guardian/delegations/{intent_id}/transcript", "get_guardian_delegation_transcript"),
    ),
    "guardian.routes.llm_overrides": (
        ("GET", "/api/llm/model-overrides", "list_model_overrides"),
        ("GET", "/api/llm/model-overrides/{provider_id}/{model_id}", "get_model_override"),
        ("PUT", "/api/llm/model-overrides/{provider_id}/{model_id}", "upsert_model_override"),
        ("DELETE", "/api/llm/model-overrides/{provider_id}/{model_id}", "delete_model_override"),
    ),
    "guardian.routes.obsidian": (
        ("GET", "/api/obsidian/config", "get_config"),
        ("PUT", "/api/obsidian/config", "put_config"),
        ("POST", "/api/obsidian/preview", "preview"),
        ("POST", "/api/obsidian/index", "index"),
    ),
    "guardian.routes.worktrees": (
        ("GET", "/api/worktrees/lanes", "list_worktree_lanes"),
        ("POST", "/api/worktrees/refresh", "refresh_worktree_lanes"),
    ),
}

ENABLED_MODULES = {
    "guardian.guardian_api",
    "guardian.routes.agent_orchestration",
    "guardian.routes.coding_work_orders",
    "guardian.routes.configuration_inspector",
    "guardian.routes.obsidian",
}
DEFAULT_OFF_MODULES = {
    "guardian.routes.backfill",
    "guardian.routes.cron",
    "guardian.routes.delegations",
    "guardian.routes.flows",
    "guardian.routes.guardian_delegations",
    "guardian.routes.worktrees",
}
PROFILE_NAMES = (
    "v1-local-core-web-mcp",
    "v1-user-profile-accent-proof",
    "test-continuity",
    "v1-friends-family-web",
    "v1-whooshd-deepseek-web",
)


def _routes(module_name: str) -> list[APIRoute]:
    module = importlib.import_module(module_name)
    if module_name == "guardian.guardian_api":
        return [
            route for route in module.app.routes
            if isinstance(route, APIRoute) and route.endpoint.__module__ == module_name
        ]
    router_names = (
        ("router", "campaign_runner_router", "orchestrator_router")
        if module_name == "guardian.routes.coding_work_orders"
        else ("router",)
    )
    return [
        route
        for name in router_names
        for route in getattr(module, name).routes
        if isinstance(route, APIRoute)
    ]


def _effective_app_routes(app: FastAPI) -> list:
    # FastAPI 0.142+ keeps included routers nested until request/schema use.
    # Its public iterator exposes the effective path and original endpoint.
    iter_contexts = getattr(fastapi_routing, "iter_route_contexts", None)
    return list(iter_contexts(app.routes) if iter_contexts else app.routes)


def _calls(route: APIRoute) -> Iterator[object]:
    def visit(dependant) -> Iterator[object]:
        for child in dependant.dependencies:
            yield child.call
            yield from visit(child)

    return visit(route.dependant)


def _find(module_name: str, method: str, path: str) -> APIRoute:
    matches = [
        route for route in _routes(module_name)
        if route.path == path and method in route.methods
    ]
    assert len(matches) == 1, (module_name, method, path, len(matches))
    return matches[0]


def _sign_legacy(secret: str) -> str:
    payload = json.dumps(
        {"subject": "legacy", "nonce": "legacy", "exp": 4_000_000_000},
        sort_keys=True, separators=(",", ":"),
    ).encode()
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    encode = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return f"{encode(payload)}.{encode(signature)}"


def test_frozen_operator_manifest_has_exactly_58_registrations_in_13_files():
    assert len(EXPECTED) == 13
    assert sum(map(len, EXPECTED.values())) == 58

    for module_name, registrations in EXPECTED.items():
        for method, path, handler in registrations:
            route = _find(module_name, method, path)
            assert route.endpoint.__name__ == handler
            calls = set(_calls(route))
            assert require_operator_auth in calls, (module_name, method, path)
            assert require_api_key not in calls, (module_name, method, path)

        expected = {(method, path) for method, path, _ in registrations}
        actual = {
            (method, route.path)
            for route in _routes(module_name)
            if require_operator_auth in set(_calls(route))
            for method in route.methods
        }
        assert actual == expected, module_name


def test_frozen_activation_ledger_and_supported_profile_posture():
    assert sum(len(EXPECTED[name]) for name in ENABLED_MODULES) == 24
    assert sum(len(EXPECTED[name]) for name in DEFAULT_OFF_MODULES) == 29
    assert len(EXPECTED["guardian.routes.graph"]) == 1
    assert len(EXPECTED["guardian.routes.llm_overrides"]) == 4

    for profile_name in PROFILE_NAMES:
        profile = load_supported_profile(profile_name)
        agent_status = (
            "enabled"
            if profile_name in {
                "v1-local-core-web-mcp", "v1-user-profile-accent-proof"
            }
            else "quarantined"
        )
        assert profile.route_status("agent_orchestration") == agent_status
        assert profile.route_status("coding_work_orders") == "internal_only"
        assert profile.route_status("obsidian") == "enabled"
        for label in (
            "backfill", "cron", "delegations", "flows",
            "guardian_delegations", "worktrees", "llm_overrides",
        ):
            assert profile.route_status(label) == "quarantined"

    source = Path("guardian/guardian_api.py").read_text()
    tree = ast.parse(source)
    default_off_flags = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "_include_router":
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords}
        label = kwargs.get("label")
        if isinstance(label, ast.Constant) and label.value in {
            "guardian_delegations", "worktrees",
        }:
            default_off_flags[label.value] = ast.literal_eval(kwargs["default_enabled"])
    assert default_off_flags == {"guardian_delegations": False, "worktrees": False}


def test_local_supported_topology_mounts_24_and_excludes_disabled_routes(monkeypatch):
    from tests.core.test_supported_profile_quarantine import (
        _build_supported_profile_client,
    )

    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", "operator-route-qualification")
    account, _ = issue_session_token(
        subject="account", purpose=ACCOUNT_SESSION_PURPOSE
    )
    with _build_supported_profile_client(monkeypatch) as client:
        app_routes = _effective_app_routes(client.app)
        mounted = {
            (method, route.path, route.endpoint.__module__, route.endpoint.__name__)
            for route in app_routes
            if isinstance(getattr(route, "original_route", route), APIRoute)
            for method in route.methods
        }
        enabled = [
            (module, method, path, handler)
            for module in ENABLED_MODULES
            for method, path, handler in EXPECTED[module]
        ]
        assert len(enabled) == 24
        for module, method, path, handler in enabled:
            expected_route = (method, path, module, handler)
            assert expected_route in mounted, {
                "expected": expected_route,
                "same_path": sorted(route for route in mounted if route[1] == path),
                "same_module": sorted(route for route in mounted if route[2] == module),
                "enabled_labels": sorted(
                    client.app.state.supported_profile_enabled_labels
                ),
            }
            concrete_path = path
            for segment in path.split("/"):
                if segment.startswith("{") and segment.endswith("}"):
                    concrete_path = concrete_path.replace(segment, "1")
            response = client.request(
                method,
                concrete_path,
                headers={"Authorization": f"Bearer {account}"},
            )
            assert response.status_code == 401, (method, path, response.status_code)

        for module in DEFAULT_OFF_MODULES | {
            "guardian.routes.graph", "guardian.routes.llm_overrides",
        }:
            for method, path, handler in EXPECTED[module]:
                assert (method, path, module, handler) not in mounted
        assert not any(
            route.endpoint.__module__ == "guardian.routes.graph"
            for route in app_routes
            if isinstance(getattr(route, "original_route", route), APIRoute)
        )


@pytest.mark.parametrize("module_name", tuple(EXPECTED))
def test_each_operator_file_uses_exact_purpose_gate(module_name, monkeypatch):
    secret = "operator-migration-secret"
    raw_key = "operator-migration-key"
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", secret)
    monkeypatch.setenv("GUARDIAN_API_KEY", raw_key)
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")

    method, path, _ = EXPECTED[module_name][0]
    route = _find(module_name, method, path)
    gate = next(call for call in _calls(route) if call is require_operator_auth)
    app = FastAPI()

    @app.get("/gate", dependencies=[Depends(gate)])
    def check_gate():
        return {"ok": True}

    # The repository TestClient seeds X-API-Key globally; remove it so each
    # credential case exercises only its named authentication lane.
    client = TestClient(app, headers={"X-API-Key": ""})
    operator, _ = issue_session_token(subject="web", purpose=OPERATOR_SESSION_PURPOSE)
    account, _ = issue_session_token(subject="account", purpose=ACCOUNT_SESSION_PURPOSE)
    guest, _ = issue_guest_session_token(
        room_id="room", room_slug="room", participant_id="guest", invitation_id="invite"
    )
    wrong, _ = issue_session_token(subject="wrong", purpose="other_purpose")
    expired, _ = issue_session_token(
        subject="web", purpose=OPERATOR_SESSION_PURPOSE, ttl_seconds=-60
    )

    assert client.get("/gate", headers={"X-API-Key": raw_key}).status_code == 200
    assert client.get("/gate", headers={"Authorization": f"Bearer {operator}"}).status_code == 200
    for token in (account, guest, _sign_legacy(secret), wrong, expired, "malformed"):
        assert client.get(
            "/gate", headers={"Authorization": f"Bearer {token}"}
        ).status_code == 401


def test_non_operator_sentinels_keep_distinct_auth_dependencies():
    from guardian.routes import account_observability, channels, connectors

    assert require_account_session in set(_calls(_find("guardian.routes.channels", "GET", "/api/channels/configs")))
    assert require_operator_auth not in set(_calls(_find("guardian.routes.channels", "GET", "/api/channels/configs")))

    service_route = next(
        route for route in account_observability.router.routes
        if isinstance(route, APIRoute) and route.endpoint.__name__ == "create_operator_invite"
    )
    from guardian.core.dependencies import require_service_capability

    assert require_service_capability in set(_calls(service_route))
    assert require_api_key not in set(_calls(service_route))
    assert require_operator_auth not in set(_calls(service_route))

    account_route = _find("guardian.routes.agent_orchestration", "POST", "/api/agents/coding/execute")
    assert require_account_session in set(_calls(account_route))
    assert require_operator_auth not in set(_calls(account_route))

    local_route = next(
        route for route in connectors.router.routes
        if isinstance(route, APIRoute) and route.endpoint.__name__ == "list_connectors"
    )
    assert require_api_key in set(_calls(local_route))
    assert require_operator_auth not in set(_calls(local_route))

    sse_route = _find("guardian.guardian_api", "GET", "/api/tasks/{task_id}/events")
    assert require_task_event_read_principal in set(_calls(sse_route))
    assert require_api_key not in set(_calls(sse_route))
    assert require_operator_auth not in set(_calls(sse_route))
