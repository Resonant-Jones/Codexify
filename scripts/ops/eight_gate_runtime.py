"""Read-only runtime access for the eight release-readiness gate observations.

This module is the harness's only way of touching the evaluated stack. It never
starts, stops, recreates, or otherwise mutates a container, and it never writes
to PostgreSQL or Redis. Everything it exposes is a read:

* ``PostgresReader``  - direct SQL over psycopg against the stack's database.
* ``RedisReader``     - direct ``LLEN`` / ``GET`` / ``TTL`` over redis-py.
* ``HttpClient``      - plain JSON HTTP calls against the backend.
* ``BrowserDriver``   - a real headless Chromium driven by Playwright.

Credential material is read from the operator's env file by key name and is
never printed: ``Secret`` renders as a SHA-256 fingerprint prefix instead.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]


class RuntimeAccessError(RuntimeError):
    """A read against the evaluated stack could not be completed."""


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Secret:
    """A credential that may be identified but never printed."""

    name: str
    value: str

    def __bool__(self) -> bool:
        return bool(self.value)

    def fingerprint(self) -> str:
        digest = hashlib.sha256(self.value.encode("utf-8")).hexdigest()
        return f"sha256:{digest[:12]}"

    def __repr__(self) -> str:  # pragma: no cover - defensive
        return f"Secret(name={self.name!r}, fingerprint={self.fingerprint()!r})"

    def __str__(self) -> str:  # pragma: no cover - defensive
        return self.fingerprint()


def fingerprint(value: str) -> str:
    """Return a short SHA-256 fingerprint for an arbitrary value."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


_ENV_LINE = re.compile(
    r"""^\s*(?:export\s+)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<rest>.*)$"""
)


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a dotenv-style file into a mapping.

    ``KEY=value``, ``export KEY=value`` and quoted values are supported. A
    value that begins with ``<`` is treated as unset, matching the compose
    convention where ``FOO=<unset>`` means "not provided".
    """
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE.match(line)
        if not match:
            continue
        key = match.group("key")
        rest = match.group("rest").strip()
        if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in {"'", '"'}:
            rest = rest[1:-1]
        if rest.startswith("<") and rest.endswith(">"):
            continue
        values[key] = rest
    return values


def load_env_file(path: Path) -> dict[str, Secret]:
    """Load an env file into named secrets."""
    return {key: Secret(name=key, value=value) for key, value in parse_env_file(path).items()}


def secret_from(env: Mapping[str, Secret], *names: str) -> Secret | None:
    """Return the first present, non-empty secret among ``names``."""
    for name in names:
        candidate = env.get(name)
        if candidate is not None and candidate.value:
            return candidate
    return None


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------


def render_sql_literal(value: Any) -> str:
    """Render one parameter as a PostgreSQL literal.

    Only the parameter types this harness actually passes are supported, and
    anything unrecognised is refused rather than interpolated blindly.
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (bytes, bytearray)):
        return "'\\x" + bytes(value).hex() + "'"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    raise RuntimeAccessError(
        f"a parameter of type {type(value).__name__} cannot be rendered as SQL"
    )


def _render_sql(sql: str, params: Sequence[Any]) -> str:
    """Render ``%s`` placeholders as literals for the container-exec path."""
    if not params:
        return sql
    rendered: list[str] = []
    index = 0
    for chunk in sql.split("%s"):
        if index < len(params):
            rendered.append(chunk)
            rendered.append(render_sql_literal(params[index]))
            index += 1
        else:
            rendered.append(chunk)
    if index != len(params):
        raise RuntimeAccessError(
            "the query has fewer placeholders than it has parameters"
        )
    return "".join(rendered)


@dataclass
class PostgresReader:
    """Read-only SQL access to the evaluated stack's PostgreSQL database.

    The primary path is a direct psycopg connection over the published host
    port. When the stack does not publish PostgreSQL to the host, the reader
    falls back to ``docker exec`` into the project's own ``db`` container and
    runs ``psql`` there. Both paths read the live database; neither writes.
    """

    dsn: Secret
    timeout_seconds: float = 20.0
    compose_project: str | None = None

    def _exec_psql(self, sql: str) -> list[dict[str, Any]]:
        """Read rows through ``psql`` inside the project's db container.

        The container's own ``POSTGRES_USER`` / ``POSTGRES_DB`` are used, which
        is the pattern the repository's other operator scripts follow. Rows are
        returned as JSON objects so that column names survive the transfer.
        """
        container = self._container_name("db")
        if container is None:
            raise RuntimeAccessError(
                "PostgreSQL is not reachable and no db container was found"
            )
        wrapped = (
            "SELECT coalesce(json_agg(_row), '[]'::json) FROM ("
            + sql.strip().rstrip(";")
            + ") AS _row"
        )
        result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                container,
                "sh",
                "-lc",
                'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" '
                '-d "$POSTGRES_DB" -AtX',
            ],
            input=wrapped + "\n",
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeAccessError(
                f"psql read failed: {result.stderr.strip()[:200]}"
            )
        raw = result.stdout.strip()
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeAccessError("psql returned a non-JSON payload") from exc
        if not isinstance(payload, list):
            return []
        return [dict(row) for row in payload if isinstance(row, Mapping)]

    def _container_name(self, service: str) -> str | None:
        if not self.compose_project:
            return None
        services = compose_service_containers(self.compose_project)
        return services.get(service)

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        """Run one read-only query and return rows as dictionaries."""
        try:
            return self._query_direct(sql, params)
        except RuntimeAccessError as direct_error:
            if not self.compose_project:
                raise
            try:
                return self._exec_psql(_render_sql(sql, params))
            except RuntimeAccessError as exec_error:
                raise RuntimeAccessError(
                    f"PostgreSQL read failed via direct connection "
                    f"({direct_error}) and via container exec ({exec_error})"
                ) from exec_error

    def _query_direct(
        self, sql: str, params: Sequence[Any] = ()
    ) -> list[dict[str, Any]]:
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeAccessError("psycopg is not importable") from exc
        try:
            conn = psycopg.connect(
                self.dsn.value,
                connect_timeout=int(self.timeout_seconds),
                autocommit=True,
            )
        except Exception as exc:
            raise RuntimeAccessError(
                f"PostgreSQL connection failed: {type(exc).__name__}"
            ) from exc
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(params))
                    if cur.description is None:
                        return []
                    columns = [column[0] for column in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as exc:
            raise RuntimeAccessError(
                f"PostgreSQL query failed: {type(exc).__name__}"
            ) from exc

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        row = self.query_one(sql, params)
        if row is None:
            return None
        return next(iter(row.values()), None)


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------


@dataclass
class RedisReader:
    """Read-only Redis access for queue depths and worker heartbeats.

    The primary path is a direct redis-py connection. When the stack does not
    publish Redis to the host, the reader falls back to ``docker exec`` into
    the project's own ``redis`` container and runs ``redis-cli`` there. Both
    paths issue the same commands the rubric names - ``LLEN``, ``GET``, ``TTL``.
    """

    url: Secret
    timeout_seconds: float = 10.0
    compose_project: str | None = None

    def _client(self) -> Any:
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeAccessError("redis is not importable") from exc
        try:
            return redis.Redis.from_url(
                self.url.value,
                socket_timeout=self.timeout_seconds,
                socket_connect_timeout=self.timeout_seconds,
                decode_responses=True,
            )
        except Exception as exc:
            raise RuntimeAccessError(
                f"Redis client construction failed: {type(exc).__name__}"
            ) from exc

    def _exec_redis_cli(self, *args: str) -> str:
        """Run one read-only redis-cli command inside the project's redis box."""
        if not self.compose_project:
            raise RuntimeAccessError("no compose project was supplied")
        container = compose_service_containers(self.compose_project).get("redis")
        if container is None:
            raise RuntimeAccessError("no redis container was found for the project")
        result = subprocess.run(
            ["docker", "exec", "-i", container, "redis-cli", *args],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeAccessError(
                f"redis-cli {args[0]} failed: {result.stderr.strip()[:200]}"
            )
        return result.stdout.strip()

    def _read(self, command: str, *args: str) -> str:
        """Run one read command, preferring the direct connection."""
        if self.url.value:
            client = self._client()
            try:
                value = getattr(client, command)(*args)
                if value is None:
                    return ""
                return str(value).strip()
            except Exception as exc:
                if not self.compose_project:
                    raise RuntimeAccessError(
                        f"{command.upper()} {args[0]} failed: {type(exc).__name__}"
                    ) from exc
        if not self.compose_project:
            raise RuntimeAccessError("no compose project was supplied")
        return self._exec_redis_cli(command.upper(), *args)

    def llen(self, key: str) -> int:
        """Read one queue's depth with ``LLEN``."""
        raw = self._read("llen", key)
        try:
            return int(raw)
        except ValueError:
            raise RuntimeAccessError(f"LLEN {key} returned a non-integer")

    def get(self, key: str) -> str | None:
        raw = self._read("get", key)
        return raw or None

    def ttl(self, key: str) -> int:
        raw = self._read("ttl", key)
        try:
            return int(raw)
        except ValueError:
            raise RuntimeAccessError(f"TTL {key} returned a non-integer")

    def ping(self) -> bool:
        try:
            return self._read("ping") in {"PONG", "pong", "1"}
        except RuntimeAccessError:
            return False


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


@dataclass
class HttpResponse:
    status: int
    body: Any
    raw: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


@dataclass
class HttpClient:
    """Small JSON HTTP client for the evaluated backend."""

    base_url: str
    api_key: Secret | None = None
    session_token: Secret | None = None
    timeout_seconds: float = 60.0

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.session_token is not None and self.session_token.value:
            headers["Authorization"] = f"Bearer {self.session_token.value}"
        elif self.api_key is not None and self.api_key.value:
            headers["X-API-Key"] = self.api_key.value
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> HttpResponse:
        url = f"{self.base_url.rstrip('/')}{path}"
        data = None
        request_headers = self._headers()
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            url, data=data, headers=request_headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(
                request, timeout=timeout_seconds or self.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
                status = response.status
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            status = exc.code
        except urllib.error.URLError as exc:
            raise RuntimeAccessError(
                f"{method} {path} could not reach the backend: {type(exc.reason).__name__}"
            ) from exc
        except TimeoutError as exc:
            raise RuntimeAccessError(f"{method} {path} timed out") from exc
        try:
            body = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError:
            body = None
        return HttpResponse(status=status, body=body, raw=raw)

    def get(self, path: str, **kwargs: Any) -> HttpResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> HttpResponse:
        return self.request("POST", path, **kwargs)


# ---------------------------------------------------------------------------
# Browser
# ---------------------------------------------------------------------------

#: Chromium executables the harness will try, in order. The repo's own
#: Playwright browser cache is the primary source; the Chrome-for-Testing
#: bundle that ships with the same cache is the fallback.
_CHROMIUM_GLOBS = (
    "chromium_headless_shell-*/chrome-mac*/headless_shell",
    "chromium_headless_shell-*/chrome-mac*/chrome-headless-shell",
    "chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell",
    "chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
    "chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
)


def discover_chromium(cache_dir: Path | None = None) -> Path | None:
    """Locate a usable Chromium binary in the Playwright browser cache."""
    roots = [cache_dir] if cache_dir else []
    roots.append(Path.home() / "Library" / "Caches" / "ms-playwright")
    roots.append(Path.home() / ".cache" / "ms-playwright")
    for root in roots:
        if root is None or not root.is_dir():
            continue
        for pattern in _CHROMIUM_GLOBS:
            matches = sorted(root.glob(pattern))
            if matches:
                return matches[0]
    return None


@dataclass
class BrowserDriver:
    """A real headless Chromium driven by Playwright."""

    executable_path: Path | None = None
    headless: bool = True
    launch_args: Sequence[str] = field(
        default_factory=lambda: (
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--single-process",
        )
    )
    viewport: Mapping[str, int] = field(
        default_factory=lambda: {"width": 1440, "height": 900}
    )

    def available(self) -> tuple[bool, str]:
        """Report whether a browser can actually be launched."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return False, "playwright is not importable in this interpreter"
        executable = self.executable_path or discover_chromium()
        if executable is None or not Path(executable).exists():
            return False, "no Chromium executable was found in the Playwright cache"
        try:
            with sync_playwright() as driver:
                browser = driver.chromium.launch(
                    headless=self.headless,
                    executable_path=str(executable),
                    args=list(self.launch_args),
                )
                try:
                    version = browser.version
                finally:
                    browser.close()
        except Exception as exc:  # pragma: no cover - environment dependent
            return False, f"Chromium could not be launched: {type(exc).__name__}"
        return True, version

    def open(self, url: str, *, session_token: str | None = None) -> "BrowserPage":
        """Open ``url`` in a real browser and return a page wrapper."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeAccessError("playwright is not importable") from exc
        executable = self.executable_path or discover_chromium()
        if executable is None or not Path(executable).exists():
            raise RuntimeAccessError("no Chromium executable was found")
        return _BrowserSession(
            sync_playwright=sync_playwright,
            executable=str(executable),
            url=url,
            headless=self.headless,
            launch_args=list(self.launch_args),
            viewport=dict(self.viewport),
            session_token=session_token,
        )


class BrowserPage:
    """The subset of Playwright's page API this harness uses."""

    def __init__(self, page: Any, browser: Any, version: str) -> None:
        self._page = page
        self._browser = browser
        self.version = version

    @property
    def page(self) -> Any:
        return self._page

    def goto(self, url: str, *, wait_until: str = "domcontentloaded") -> None:
        self._page.goto(url, wait_until=wait_until)

    def reload(self, *, wait_until: str = "domcontentloaded") -> None:
        self._page.reload(wait_until=wait_until)

    def inner_text(self, selector: str) -> str:
        return self._page.inner_text(selector)

    def text_content(self, selector: str) -> str | None:
        return self._page.text_content(selector)

    def count(self, selector: str) -> int:
        return self._page.locator(selector).count()

    def all_inner_texts(self, selector: str) -> list[str]:
        return self._page.locator(selector).all_inner_texts()

    def evaluate(self, expression: str) -> Any:
        return self._page.evaluate(expression)

    def viewport_info(self) -> dict[str, Any]:
        return {
            "viewport": dict(self._page.viewport_size or {}),
            "device_pixel_ratio": self._page.evaluate("window.devicePixelRatio"),
            "user_agent": self._page.evaluate("window.navigator.userAgent"),
        }

    def close(self) -> None:
        try:
            self._browser.close()
        except Exception:
            pass


class _BrowserSession:
    """Owns the Playwright driver lifetime for one page."""

    def __init__(
        self,
        *,
        sync_playwright: Any,
        executable: str,
        url: str,
        headless: bool,
        launch_args: list[str],
        viewport: dict[str, int],
        session_token: str | None,
    ) -> None:
        self._driver = sync_playwright().start()
        self._browser = self._driver.chromium.launch(
            headless=headless,
            executable_path=executable,
            args=launch_args,
        )
        self._context = self._browser.new_context(viewport=viewport)
        if session_token:
            # The frontend keeps its account session token in sessionStorage
            # under this key (frontend/src/lib/api.ts).
            self._context.add_init_script(
                "token => window.sessionStorage.setItem('guardian.auth.token', token)",
                session_token,
            )
        self._page = self._context.new_page()
        self.version = self._browser.version
        try:
            self._page.goto(url, wait_until="domcontentloaded")
        except Exception:
            pass

    def __enter__(self) -> BrowserPage:
        return BrowserPage(self._page, self._browser, self.version)

    def __exit__(self, *exc: Any) -> None:
        try:
            self._browser.close()
        except Exception:
            pass
        try:
            self._driver.stop()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Compose introspection (read-only)
# ---------------------------------------------------------------------------


def compose_service_containers(compose_project: str) -> dict[str, str]:
    """Map compose service name to container name for one project.

    This reads Docker's own labels and never starts, stops, or recreates a
    container. The compose files are deliberately not parsed, so a stack that
    was launched with extra overlays is still resolved correctly.
    """
    result = subprocess.run(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"label=com.docker.compose.project={compose_project}",
            "--format",
            "{{.Label \"com.docker.compose.service\"}}\t{{.Names}}",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeAccessError(
            f"docker ps failed for project {compose_project!r}: "
            f"{result.stderr.strip()[:200]}"
        )
    services: dict[str, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        service, _, container = line.partition("\t")
        service = service.strip()
        container = container.strip()
        if service and container:
            services[service] = container
    return services


def compose_service_running(compose_project: str) -> dict[str, bool]:
    """Map compose service name to whether its container is currently running."""
    result = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"label=com.docker.compose.project={compose_project}",
            "--format",
            "{{.Label \"com.docker.compose.service\"}}\t{{.Names}}\t{{.State}}",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    running: dict[str, bool] = {}
    if result.returncode != 0:
        return running
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        running[parts[0].strip()] = parts[2].strip().lower() == "running"
    return running


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime | str | None) -> str | None:
    """Normalize one timestamp to a UTC ISO-8601 string.

    Accepts a datetime or the string form, because the container-exec path
    returns JSONB timestamps as text while the direct path returns datetimes.
    """
    if moment is None:
        return None
    if isinstance(moment, str):
        parsed = parse_iso(moment)
        if parsed is None:
            return moment
        return parsed.isoformat()
    if not isinstance(moment, datetime):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat()


def parse_iso(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def redact(value: Any) -> Any:
    """Recursively redact credential-looking keys from a JSON-ish payload."""
    secret_markers = (
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "credential",
        "jwt",
        "password",
        "secret",
        "session_token",
        "token",
    )
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in secret_markers):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact(item)
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


def env_int(env: Mapping[str, Secret], name: str, default: int) -> int:
    candidate = env.get(name)
    if candidate is None or not candidate.value:
        return default
    try:
        return int(candidate.value.strip())
    except ValueError:
        return default


def env_bool(env: Mapping[str, Secret], name: str, default: bool = False) -> bool:
    candidate = env.get(name)
    if candidate is None or not candidate.value:
        return default
    return candidate.value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_base_url(env: Mapping[str, Secret], explicit: str | None) -> str:
    """Resolve the backend base URL from the flag, then the env file."""
    if explicit:
        return explicit.rstrip("/")
    for name in ("CODEXIFY_BASE_URL", "BACKEND_URL", "GUARDIAN_BASE_URL"):
        candidate = env.get(name)
        if candidate is not None and candidate.value:
            return candidate.value.rstrip("/")
    port = env_int(env, "CODEXIFY_BACKEND_PORT", 8888)
    return f"http://127.0.0.1:{port}"


def resolve_frontend_url(env: Mapping[str, Secret], explicit: str | None) -> str:
    """Resolve the frontend base URL from the flag, then the env file."""
    if explicit:
        return explicit.rstrip("/")
    for name in ("CODEXIFY_FRONTEND_URL", "FRONTEND_URL"):
        candidate = env.get(name)
        if candidate is not None and candidate.value:
            return candidate.value.rstrip("/")
    port = env_int(env, "CODEXIFY_FRONTEND_PORT", 5173)
    return f"http://127.0.0.1:{port}"


def resolve_database_dsn(env: Mapping[str, Secret], explicit: str | None) -> Secret:
    """Resolve the PostgreSQL DSN from the flag, then the env file."""
    if explicit:
        return Secret(name="DATABASE_URL", value=explicit)
    for name in ("DATABASE_URL", "GUARDIAN_DATABASE_URL", "GUARDIAN_DB_DSN"):
        candidate = env.get(name)
        if candidate is not None and candidate.value:
            return candidate
    user = env.get("POSTGRES_USER")
    password = env.get("POSTGRES_PASSWORD")
    database = env.get("POSTGRES_DB")
    port = env_int(env, "CODEXIFY_POSTGRES_PORT", 5433)
    if user and password and database:
        return Secret(
            name="DATABASE_URL",
            value=(
                f"postgresql://{user.value}:{password.value}"
                f"@127.0.0.1:{port}/{database.value}"
            ),
        )
    return Secret(name="DATABASE_URL", value="")


def resolve_redis_url(env: Mapping[str, Secret], explicit: str | None) -> Secret:
    """Resolve the Redis URL from the flag, then the env file."""
    if explicit:
        return Secret(name="REDIS_URL", value=explicit)
    for name in ("REDIS_URL", "GUARDIAN_REDIS_URL"):
        candidate = env.get(name)
        if candidate is not None and candidate.value:
            return candidate
    port = env_int(env, "CODEXIFY_REDIS_PORT", 6379)
    return Secret(name="REDIS_URL", value=f"redis://127.0.0.1:{port}/0")


def iter_dicts(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
