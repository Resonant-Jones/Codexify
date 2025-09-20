import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from guardian.retrieve.api import router as retrieve_router
from guardian.server.codexify_api import oauth_status as codexify_oauth_status
from guardian.server.codexify_api import router as codexify_router
from guardian.server.tools_api import router as tools_router
from guardian.sync.api import router as sync_router

app = FastAPI()
app.include_router(tools_router)
app.include_router(codexify_router)
app.include_router(sync_router)
app.include_router(retrieve_router)

# --- Safe, readable pattern: mask sensitive basenames; strip dirs ---
SENSITIVE_BASENAME_RE = re.compile(
    r"""
    (
        (?P<dir>(?:[A-Za-z]:)?[^\s'\"]*[/\\])?   # optional dir (unix or win)
        (?P<base>(?i:
            client_secret[^/\\\s]*\.json   |   # client_secret*.json
            credentials\.json                |   # credentials.json
            token(?:\.[A-Za-z0-9._-]+)?      |   # token, token.json, token.any
            token\.pickle                    |   # legacy pickle tokens
            [^/\\\s]+?\.(?:pem|p12|pfx)         # private key-ish files
        ))
    )
""",
    re.VERBOSE,
)

# --- Logging to file (optional via env) ---
_log_file = os.environ.get("GUARDIAN_LOG_FILE")
_log_level = os.environ.get("GUARDIAN_LOG_LEVEL", "INFO").upper()
_max_mb = int(os.environ.get("GUARDIAN_LOG_MAX_MB", "5"))
_backups = int(os.environ.get("GUARDIAN_LOG_BACKUPS", "3"))

# Scrubber toggle and optional extras
SCRUB_ENABLED = os.getenv("GUARDIAN_SCRUB_LOGS", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
_EXTRA_EXTS = [
    e.strip().lower()
    for e in os.getenv("GUARDIAN_SCRUB_EXTRA_EXTS", "").split(",")
    if e.strip()
]
_EXTRA_NAMES = [
    n.strip()
    for n in os.getenv("GUARDIAN_SCRUB_EXTRA_NAMES", "").split(",")
    if n.strip()
]

# Optional: also scrub plaintext occurrences of "secret" when near cred-like words
SCRUB_PLAINTEXT_SECRETS = os.getenv(
    "GUARDIAN_SCRUB_PLAINTEXT_SECRETS", "0"
).strip().lower() in ("1", "true", "yes", "on")

# Tunables for plaintext secret masking
_SECRET_CONTEXT_CHARS = int(os.getenv("GUARDIAN_SCRUB_SECRET_WINDOW", "64"))
_SECRET_KEYWORDS = [
    k.strip()
    for k in os.getenv(
        "GUARDIAN_SCRUB_SECRET_KEYWORDS",
        # default set – can be extended via env
        "token,credential,credentials,password,key,client,api",
    ).split(",")
    if k.strip()
]


def _build_extra_patterns():
    pats = []
    if _EXTRA_EXTS:
        exts = "|".join(re.escape(x) for x in _EXTRA_EXTS)
        pats.append(
            re.compile(
                r"""
            (
                (?P<dir>(?:[A-Za-z]:)?[^\s'"]*[/\\])?
                (?P<base>[^/\\\s]+?\.(?:%s))
            )
        """
                % exts,
                re.VERBOSE | re.IGNORECASE,
            )
        )
    if _EXTRA_NAMES:
        names = "|".join(re.escape(x) for x in _EXTRA_NAMES)
        pats.append(
            re.compile(
                r"""
            (
                (?P<dir>(?:[A-Za-z]:)?[^\s'"]*[/\\])?
                (?P<base>(?:%s))
            )
        """
                % names,
                re.VERBOSE,
            )
        )
    return pats


class ScrubFormatter(logging.Formatter):
    """Mask sensitive token/secret file *paths* to basename + ' (hidden)'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._patterns = [SENSITIVE_BASENAME_RE] + _build_extra_patterns()

    @staticmethod
    def _repl(m: re.Match) -> str:
        return f"{m.group('base')} (hidden)"

    def _scrub_plaintext(self, text: str) -> str:
        """
        Extra-pass scrub that masks the word 'secret' in credential contexts, without
        over-scrubbing general prose. Enabled by GUARDIAN_SCRUB_PLAINTEXT_SECRETS.
        Rules:
          - Always mask 'client_secret' / 'client-secret' as a term.
          - Mask a standalone word 'secret' only if within N chars (window) of common cred words.
            Window and keywords are configurable via env.
        """
        if not SCRUB_PLAINTEXT_SECRETS:
            return text
        s = text

        # 1) Normalize / mask 'client_secret' term variants
        s = re.sub(r"(?i)\bclient[_-]?secret\b", "client_secret (hidden)", s)

        # 2) Mask 'secret' near cred-like terms to reduce false positives in normal text
        key_words_re = re.compile(
            r"(?i)\b(" + "|".join(re.escape(k) for k in _SECRET_KEYWORDS) + r")\b"
        )

        def mask_if_context(m: re.Match) -> str:
            start, end = m.span()
            win = max(0, _SECRET_CONTEXT_CHARS)
            left = s[max(0, start - win) : start]
            right = s[end : min(len(s), end + win)]
            if key_words_re.search(left) or key_words_re.search(right):
                return m.group(0) + " (hidden)"
            return m.group(0)

        s = re.sub(r"(?i)\bsecret\b", mask_if_context, s)
        return s

    def _scrub(self, text: str) -> str:
        out = text
        for pat in self._patterns:
            out = pat.sub(self._repl, out)
        # Optional plaintext pass for 'secret' in credential contexts
        out = self._scrub_plaintext(out)
        # Collapse any repeated " (hidden)" markers introduced by multiple passes
        out = re.sub(r"(?:\s*\(hidden\))+", " (hidden)", out)
        return out

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        if not SCRUB_ENABLED:
            return rendered
        try:
            return self._scrub(rendered)
        except Exception:
            # never break logging due to scrubbing
            return rendered


root = logging.getLogger()
root.setLevel(getattr(logging, _log_level, logging.INFO))
if _log_file:
    try:
        fh = RotatingFileHandler(
            _log_file, maxBytes=_max_mb * 1024 * 1024, backupCount=_backups
        )
        fh.setLevel(getattr(logging, _log_level, logging.INFO))
        fh.setFormatter(
            ScrubFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(fh)
        root.info(
            "File logging enabled → %s (max %d MB, backups %d)",
            _log_file,
            _max_mb,
            _backups,
        )
    except Exception:
        # Don’t crash server on log setup failure
        pass

root_logger = logging.getLogger()

# If no console handler exists, add one with ScrubFormatter
has_stream = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
if not has_stream:
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(root_logger.level)
    console.setFormatter(ScrubFormatter("%(levelname)s: %(message)s"))
    root_logger.addHandler(console)
else:
    # Convert existing StreamHandlers to use ScrubFormatter (preserve format)
    for h in root_logger.handlers:
        if isinstance(h, logging.StreamHandler):
            existing_fmt = getattr(
                getattr(h, "formatter", None), "_fmt", "%(levelname)s: %(message)s"
            )
            h.setFormatter(ScrubFormatter(existing_fmt))


# Optional tiny health endpoint
@app.get("/healthz")
def healthz():
    # Codexify health (no secrets)
    try:
        status = codexify_oauth_status().get("status")
    except Exception:
        status = "unknown"
    codexify_info = {
        "auth_mode": status,
        "default_folder_set": bool(os.environ.get("CODEXIFY_DEFAULT_FOLDER")),
        "share_anyone_default": os.environ.get("CODEXIFY_SHARE_ANYONE", "")
        .strip()
        .lower()
        in ("1", "true", "yes", "on"),
        "scrub_logs": SCRUB_ENABLED,
        "scrub_plaintext": SCRUB_PLAINTEXT_SECRETS,
    }
    return {"ok": True, "codexify": codexify_info}


# CORS: configurable via GUARDIAN_CORS_ORIGINS (comma-separated) or "*" by default
_origins_env = os.getenv("GUARDIAN_CORS_ORIGINS", "*").strip()
if _origins_env == "*":
    _origins = ["*"]
    _allow_credentials = False  # Star with credentials is not permitted by Starlette
else:
    _origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
    _allow_credentials = True

# Optional explicit override for credentials behavior
_creds_env = os.getenv("GUARDIAN_CORS_ALLOW_CREDENTIALS")
if _creds_env is not None:
    val = _creds_env.strip().lower()
    _allow_credentials = val in ("1", "true", "yes", "on")
    # Guard against invalid combo: credentials with wildcard origins
    if _allow_credentials and _origins == ["*"]:
        _allow_credentials = False

# Methods and headers: configurable via env (comma-separated) or "*" by default
_methods_env = os.getenv("GUARDIAN_CORS_METHODS", "*").strip()
_headers_env = os.getenv("GUARDIAN_CORS_HEADERS", "*").strip()

if _methods_env == "*":
    _methods = ["*"]
else:
    _methods = [m.strip().upper() for m in _methods_env.split(",") if m.strip()]

if _headers_env == "*":
    _headers = ["*"]
else:
    _headers = [h.strip() for h in _headers_env.split(",") if h.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=_methods,
    allow_headers=_headers,
)


@app.get("/")
def root():
    """Simple index showing available routes and methods."""
    routes = []
    for r in app.routes:
        try:
            path = getattr(r, "path", None)
            methods = sorted(list(getattr(r, "methods", []) or []))
            if not path:
                continue
            if path in {"/openapi.json", "/docs", "/redoc"}:
                continue
            if "HEAD" in methods:
                methods.remove("HEAD")
            routes.append({"path": path, "methods": methods})
        except Exception:
            continue
    return {"ok": True, "routes": routes}
