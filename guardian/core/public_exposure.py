"""Public endpoint exposure middleware with declarative allowlist profiles."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

DEFAULT_ROUTES_FILE = "config/public_routes.yaml"
DEFAULT_PROFILE = "minimal_health"
DEFAULT_EXPOSURE_MODE = "local_safe"
PUBLIC_ALLOWLIST_MODE = "public_allowlist"


@dataclass(frozen=True)
class AllowRule:
    method: str
    path: str | None = None
    prefix: str | None = None


class PublicAllowlist:
    """Method/path allowlist loaded from profile YAML."""

    def __init__(self, rules: list[AllowRule]) -> None:
        self._rules = rules

    @classmethod
    def deny_all(cls) -> PublicAllowlist:
        return cls(rules=[])

    @classmethod
    def load(cls, routes_file: str, profile: str) -> PublicAllowlist:
        try:
            data = _load_yaml(routes_file)
            rules = _validate_and_parse_rules(data, profile)
            return cls(rules=rules)
        except Exception as exc:
            logger.warning(
                "[public_exposure] Invalid allowlist config (deny-all): %s",
                exc,
            )
            return cls.deny_all()

    def is_allowed(self, method: str, path: str) -> bool:
        method_upper = (method or "").upper()
        normalized_path = _normalize_path(path)

        for rule in self._rules:
            if rule.method != method_upper:
                continue
            if rule.path is not None and normalized_path == rule.path:
                return True
            if rule.prefix is not None and normalized_path.startswith(
                rule.prefix
            ):
                return True
        return False


class PublicExposureMiddleware:
    """Default-deny gate for public_allowlist exposure mode."""

    def __init__(
        self,
        app: ASGIApp,
        exposure_mode: str = DEFAULT_EXPOSURE_MODE,
        routes_file: str = DEFAULT_ROUTES_FILE,
        profile: str = DEFAULT_PROFILE,
    ) -> None:
        self.app = app
        self.exposure_mode = (exposure_mode or DEFAULT_EXPOSURE_MODE).strip()
        self.routes_file = routes_file or DEFAULT_ROUTES_FILE
        self.profile = profile or DEFAULT_PROFILE
        self._allowlist = PublicAllowlist.deny_all()
        if self.exposure_mode == PUBLIC_ALLOWLIST_MODE:
            self._allowlist = PublicAllowlist.load(
                routes_file=self.routes_file,
                profile=self.profile,
            )

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        if self.exposure_mode != PUBLIC_ALLOWLIST_MODE:
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "GET"))
        path = str(scope.get("path", "/"))
        if self._allowlist.is_allowed(method=method, path=path):
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            status_code=403,
            content={"ok": False, "error": "forbidden"},
        )
        await response(scope, receive, send)


def _load_yaml(routes_file: str) -> dict[str, Any]:
    path = _resolve_routes_file(routes_file)
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("allowlist root must be a mapping")
    return loaded


def _validate_and_parse_rules(
    payload: dict[str, Any], profile: str
) -> list[AllowRule]:
    version = payload.get("version")
    if version != 1:
        raise ValueError("version must be 1")

    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("profiles must be a mapping")

    profile_payload = profiles.get(profile)
    if not isinstance(profile_payload, dict):
        raise ValueError(f"profile not found: {profile}")

    allow = profile_payload.get("allow")
    if not isinstance(allow, list):
        raise ValueError("profile allow must be a list")

    rules: list[AllowRule] = []
    for entry in allow:
        if not isinstance(entry, dict):
            raise ValueError("allow entries must be mappings")

        method = entry.get("method")
        if not isinstance(method, str) or not method.strip():
            raise ValueError("allow entry method must be a non-empty string")
        method = method.upper()

        has_path = "path" in entry
        has_prefix = "prefix" in entry
        if has_path == has_prefix:
            raise ValueError(
                "allow entry must include exactly one of path or prefix"
            )

        if has_path:
            path_value = entry.get("path")
            if not isinstance(path_value, str) or not path_value:
                raise ValueError("path must be a non-empty string")
            rules.append(
                AllowRule(method=method, path=_normalize_path(path_value))
            )
            continue

        prefix_value = entry.get("prefix")
        if not isinstance(prefix_value, str) or not prefix_value:
            raise ValueError("prefix must be a non-empty string")
        rules.append(
            AllowRule(method=method, prefix=_normalize_path(prefix_value))
        )

    return rules


def _normalize_path(path: str) -> str:
    value = (path or "").strip()
    if not value:
        return "/"
    if not value.startswith("/"):
        return f"/{value}"
    return value


def _resolve_routes_file(routes_file: str) -> Path:
    raw = (routes_file or DEFAULT_ROUTES_FILE).strip()
    path = Path(raw)
    if path.is_absolute():
        if not path.exists():
            raise FileNotFoundError(path)
        return path

    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path

    repo_root = Path(__file__).resolve().parents[2]
    repo_path = repo_root / path
    if repo_path.exists():
        return repo_path

    raise FileNotFoundError(raw)
