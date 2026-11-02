"""The Command Bus visibility policy over the canonical mounted routes.

The Command Bus manifest and the public OpenAPI document are two projections of
one authority: the application's mounted routes. These tests pin the seam that
the OpenConnector integration needed:

* an internal-only route is absent from the public document;
* an internal-only route that is **not** marked command-visible is absent from
  the manifest, so mounting an internal route cannot widen the agent-visible
  command surface;
* an internal-only route that **is** marked command-visible appears in the
  manifest, classified by the same HTTP-method rule the public routes use;
* the command set is derived from the mounted routes, so it cannot drift into a
  second registry.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from guardian.command_bus import manifest as manifest_module
from guardian.core.route_visibility import (
    build_mounted_route_schema,
    build_public_route_schema,
    command_visible_paths,
    hide_paths,
    internal_only_paths,
)

_PUBLIC_PATH = "/api/commands/public-read"
_MARKED_INTERNAL_PATH = "/api/commands/marked-internal"
_UNMARKED_INTERNAL_PATH = "/api/commands/unmarked-internal"


def _build_app() -> FastAPI:
    app = FastAPI(title="visibility-test", version="1.0.0")

    @app.get(_PUBLIC_PATH, operation_id="public_read")
    def public_read() -> dict[str, bool]:
        return {"ok": True}

    unmarked = APIRouter(prefix="/api/commands", tags=["internal"])

    @unmarked.get("/unmarked-internal", operation_id="unmarked_internal")
    def unmarked_internal() -> dict[str, bool]:
        return {"ok": True}

    marked = APIRouter(prefix="/api/commands", tags=["internal"])

    @marked.get("/marked-internal", operation_id="marked_internal")
    def marked_internal() -> dict[str, bool]:
        return {"ok": True}

    # The marker is declared on the endpoint, exactly as the OpenConnector
    # route declares it.
    from guardian.core.route_visibility import command_visible

    command_visible(marked_internal)

    app.include_router(unmarked)
    app.include_router(marked)
    hide_paths(
        app,
        [
            route.path
            for route in list(unmarked.routes) + list(marked.routes)
            if getattr(route, "path", None)
        ],
    )
    return app


def _command_ids(app: FastAPI) -> set[str]:
    manifest = manifest_module.build_manifest(app)
    return {command.command_id for command in manifest.commands}


def test_internal_only_routes_are_absent_from_the_public_document() -> None:
    app = _build_app()

    public_paths = set(build_public_route_schema(app).get("paths", {}))

    assert _PUBLIC_PATH in public_paths
    assert _MARKED_INTERNAL_PATH not in public_paths
    assert _UNMARKED_INTERNAL_PATH not in public_paths


def test_unmarked_internal_only_route_is_not_a_command() -> None:
    app = _build_app()

    command_ids = _command_ids(app)

    assert "op::public_read" in command_ids
    assert "op::unmarked_internal" not in command_ids


def test_marked_internal_only_route_is_a_command() -> None:
    app = _build_app()

    command_ids = _command_ids(app)

    assert "op::marked_internal" in command_ids
    assert "op::unmarked_internal" not in command_ids


def test_marked_internal_command_is_classified_as_a_read() -> None:
    app = _build_app()

    manifest = manifest_module.build_manifest(app)
    command = next(
        command
        for command in manifest.commands
        if command.command_id == "op::marked_internal"
    )

    assert command.method == "GET"
    assert command.path_template == _MARKED_INTERNAL_PATH
    assert command.effect == "read"
    assert command.risk == "read_only"
    assert command.idempotency == "safe"
    assert command.approval_mode == "none"
    assert command.layer == "raw"


def test_visibility_policy_does_not_widen_the_public_command_surface() -> None:
    """The manifest is the public command surface plus marked internal routes."""

    app = _build_app()

    public_paths = set(build_public_route_schema(app).get("paths", {}))
    raw_paths = set(build_mounted_route_schema(app).get("paths", {}))
    marked = command_visible_paths(app)

    assert marked == frozenset({_MARKED_INTERNAL_PATH})

    visible = (raw_paths - internal_only_paths(app)) | marked
    assert visible == public_paths | marked


def test_command_set_follows_the_mounted_routes() -> None:
    """There is no parallel command registry: the set follows the mounts."""

    app = _build_app()
    before = _command_ids(app)

    late = APIRouter(prefix="/api/commands", tags=["late"])

    @late.get("/late-mounted", operation_id="late_mounted")
    def late_mounted() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(late)
    after = _command_ids(app)

    assert "op::late_mounted" not in before
    assert "op::late_mounted" in after
