# Ensure package-relative import works when running pytest from the repo root
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Avoid importing the FastAPI app at import-time to keep non-API tests light
import os
from urllib.parse import urlparse
import pytest
from dotenv import load_dotenv

# Import the correct FastAPI app for tests
try:
    from neo4j import GraphDatabase  # type: ignore
except Exception:
    GraphDatabase = None  # type: ignore
import socket
from urllib.parse import urlparse
import os
# Load environment variables for pytest
load_dotenv()
# Hint to config loader that we're in a test context and dummy fallbacks are allowed
os.environ.setdefault("GUARDIAN_ALLOW_DUMMY_SETTINGS", "1")

# ---- Make dotenv safe globally (never override seeded env in tests) ----
try:
    import dotenv as _dotenv

    _ORIG_DOTENV_LOAD = _dotenv.load_dotenv

    def _safe_load_dotenv(*args, **kwargs):
        # Force override=False regardless of callers; do not clobber env set in this file
        kwargs["override"] = False
        return _ORIG_DOTENV_LOAD(*args, **kwargs)

    _dotenv.load_dotenv = _safe_load_dotenv  # type: ignore[attr-defined]
except Exception:
    # If python-dotenv is missing or import fails, continue; our manual seeding still works
    _dotenv = None
    _ORIG_DOTENV_LOAD = None

# --- Early, pre-dotenv env hardening (runs before test collection) ---
# Disable implicit .env auto-loading ASAP so no later call can wipe seeded values.
os.environ.setdefault("PYTHON_DOTENV_DISABLE", "1")

# Seed critical keys BEFORE any module can import Settings and run validation.
for _key in [
    "GENAI_API_KEY",
    "NOTION_API_KEY",
    "ANTHROPIC_API_KEY",
    # Helpful extras so other code paths don't crash during collection
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
]:
    if not os.environ.get(_key):
        os.environ[_key] = "dummy"
    # Always mirror into GUARDIAN_* so pydantic env_prefix variants resolve
    os.environ[f"GUARDIAN_{_key}"] = os.environ[_key]

# Ensure a safe default so code paths don't accidentally construct OpenAI by default
os.environ.setdefault("LLM_PROVIDER", "groq")

print("✅ conftest loaded: dotenv patched (override=False); env seeded")

from dotenv import load_dotenv

# Load .env early, but never override what we just seeded
load_dotenv(override=False)

# Debug print to verify seeding during collection (should appear before Settings is built)
print(
    "✅ conftest.py(seeding):",
    "GENAI_API_KEY=",
    bool(os.environ.get("GENAI_API_KEY")),
    "NOTION_API_KEY=",
    bool(os.environ.get("NOTION_API_KEY")),
    "ANTHROPIC_API_KEY=",
    bool(os.environ.get("ANTHROPIC_API_KEY")),
)

# --- Belt & suspenders: prevent later dotenv calls from clobbering our seeded env ---
# Some modules may call load_dotenv(override=True) internally. If their .env has
# empty values, that can wipe out our dummies and break Settings validation.
# These two env flags are respected by python-dotenv and many integrations; they
# make extra dotenv loads non-destructive in tests.
# (Explicit load_dotenv(...) still runs, but we never *override* seeded values.)
# We also defensively ensure our keys are still populated right before Settings is built.
try:
    import guardian.config.core as _core

    _orig_get_settings = _core.get_settings

    def _patched_get_settings(*args, **kwargs):
        # Re-seed required keys in case anything clobbered them
        for _k in [
            "GENAI_API_KEY",
            "NOTION_API_KEY",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GROQ_API_KEY",
        ]:
            if not os.environ.get(_k):
                os.environ[_k] = "dummy"
            os.environ[f"GUARDIAN_{_k}"] = os.environ[_k]
        # Prefer safe default provider during tests
        os.environ.setdefault("LLM_PROVIDER", "groq")
        return _orig_get_settings(*args, **kwargs)

    # Swap in our patched getter
    _core.get_settings = _patched_get_settings  # type: ignore[attr-defined]
except Exception:
    # If the module path changes or import fails during collection, no problem.
    # Tests will still have the early seeding above.
    pass


# Ensure re-seeding happens before any test begins, even if some import called dotenv
def pytest_sessionstart(session):
    # Re-assert required envs in case earlier imports clobbered them
    for _k in [
        "GENAI_API_KEY",
        "NOTION_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
    ]:
        if not os.environ.get(_k):
            os.environ[_k] = "dummy"
        os.environ[f"GUARDIAN_{_k}"] = os.environ[_k]
    os.environ.setdefault("LLM_PROVIDER", "groq")


# Second line of defense: pytest_configure hook
def pytest_configure(config):
    """Guarantee env seeding happens before collection across the entire session."""
    # Nothing to do here because we seeded at import-time, but leave this hook
    # in case future changes move seeding here.
    pass


# Env vars that some settings validators expect; seed dummies during tests
REQUIRED_ENV_VARS = [
    "GENAI_API_KEY",
    "NOTION_API_KEY",
    "ANTHROPIC_API_KEY",
    # Helpful extras so other code paths don't crash during collection
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
]


def _internet():
    try:
        socket.create_connection(("1.1.1.1", 53), 1)
        return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    config.addinivalue_line("markers", "net: test requires external network access")
    config.addinivalue_line(
        "markers", "skip(reason): mark test to be skipped with a reason"
    )

    # Robustly interpret ALLOW_NET_TESTS env var (accept "1", "true", "yes")
    env_val = os.getenv("ALLOW_NET_TESTS", "").strip().lower()
    opt_in_net = env_val in ("1", "true", "yes")

    # Only probe external connectivity if the user explicitly opted in.
    allow_net = opt_in_net and _internet()

    # Always detect whether any graph tests were collected so seeding can be decided later.
    need_graph_seed = False
    for item in items:
        # Path-based heuristic for known network-heavy tests
        if "export_notion" in str(item.fspath):
            # will be skipped only if allow_net is False (handled below)
            pass
        # Detect graph tests by path
        if "/tests/graph/" in str(item.fspath).replace("\\", "/"):
            need_graph_seed = True

    # Store decision on config object for session fixtures to read
    setattr(config, "_need_neo4j_seed", need_graph_seed)

    # If network access is NOT allowed, add skip markers where appropriate.
    if not allow_net:
        net_skip = pytest.mark.skip(
            reason="requires network (set ALLOW_NET_TESTS=1 or true to enable)"
        )
        for item in items:
            # If the test opts-in to network via marker, skip when not allowed
            if item.get_closest_marker("net"):
                item.add_marker(net_skip)
            # Path-based heuristic for known network-heavy tests
            if "export_notion" in str(item.fspath):
                item.add_marker(net_skip)


# Ensure .env is loaded for all tests
@pytest.fixture(scope="session", autouse=True)
def load_dotenv_for_tests():
    """Ensure .env is loaded for all tests."""
    load_dotenv(override=False)
    print(
        f"✅ conftest.py: OPENAI_API_KEY loaded? {os.getenv('OPENAI_API_KEY') is not None}"
    )


# Seed required env vars with dummy values so Settings validation doesn't fail during tests
@pytest.fixture(scope="session", autouse=True)
def _seed_dummy_env_for_settings():
    """Seed required env vars with dummy values during tests to satisfy Settings validation.

    If ALLOW_NET_TESTS is set in the environment, we still only populate *missing*
    variables to avoid clobbering real credentials on CI or local runs.
    """
    _ = bool(
        os.getenv("ALLOW_NET_TESTS")
    )  # not used currently; keep for future behavior
    for key in REQUIRED_ENV_VARS:
        if not os.environ.get(key):
            os.environ[key] = "dummy"
        os.environ[f"GUARDIAN_{key}"] = os.environ[key]
    # Choose a safe default provider so client factory doesn't default to OpenAI unexpectedly
    os.environ.setdefault("LLM_PROVIDER", "groq")
    print("✅ conftest.py(fixtures): seeded keys for Settings")


# --- Session-scoped Neo4j seed for deterministic graph tests ---------------
@pytest.fixture(scope="session", autouse=True)
def seed_neo4j_graph(request):
    """Seed a minimal Message->User graph if Neo4j is reachable.

    Uses guardian.db.neo.get_session() which reads env (NEO4J_BOLT_URL/BOLT_URL,
    NEO4J_USER/NEO4J_PASS). Best-effort: failures are logged but do not fail
    the session to keep non-graph tests running without Neo4j.
    """
    # Only seed when graph tests are present
    if not getattr(request.config, "_need_neo4j_seed", False):
        return

    try:
        from guardian.db.neo import get_session  # type: ignore
    except Exception as e:  # pragma: no cover
        print(f"⚠️ seed_neo4j_graph: neo4j helper unavailable: {e}")
        return

    try:
        with get_session() as s:
            # quick ping
            s.run("RETURN 1 AS ok").single()
            # constraints + deterministic seed
            s.run(
                "CREATE CONSTRAINT user_uid IF NOT EXISTS FOR (u:UserNode) REQUIRE u.uid IS UNIQUE"
            )
            s.run(
                "CREATE CONSTRAINT message_id IF NOT EXISTS FOR (m:MessageNode) REQUIRE m.message_id IS UNIQUE"
            )
            s.run(
                """
                MERGE (m:MessageNode {message_id:'seed-msg-1'})
                  ON CREATE SET m.content='hello seed'
                MERGE (u:UserNode {uid:'seed-uid-1'})
                  ON CREATE SET u.name='seed-user-1'
                MERGE (m)-[:SENT_BY]->(u)
                """
            )
            print("✅ Neo4j seed applied (Message->User SENT_BY)")
    except Exception as e:
        print(f"⚠️ seed_neo4j_graph: skipping (Neo4j not reachable): {e}")


@pytest.fixture(scope="module")
def neo4j_driver():
    """Provide a neo4j GraphDatabase driver for tests.

    This helper is tolerant of BOLT URLs that embed credentials (e.g.
    bolt://user:pass@host:7687). The neo4j Python driver does not accept
    username in the URI, so we strip credentials from the URL and pass them
    via the auth tuple instead.
    """
    bolt = os.getenv("BOLT_URL") or os.getenv("NEO4J_BOLT_URL") or os.getenv("NEO4J_URI") or "bolt://localhost:7687"
    parsed = urlparse(bolt)

    # Default creds from env if not embedded in URL
    env_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME") or "neo4j"
    env_pass = os.getenv("NEO4J_PASS") or os.getenv("NEO4J_PASSWORD") or ""

    # If URL contains credentials, extract and rebuild host-only URL
    if parsed.username:
        user = parsed.username
        pwd = parsed.password or env_pass
        host_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port or 7687}"
        auth = (user, pwd)
    else:
        host_url = bolt
        auth = (env_user, env_pass)

    if GraphDatabase is None:
        pytest.skip("neo4j driver not installed; set it up to run graph tests")
    driver = GraphDatabase.driver(host_url, auth=auth)
    try:
        yield driver
    finally:
        try:
            driver.close()
        except Exception:
            pass


class DummyClient:
    def chat_completion(self, *, model, messages, temperature=0.7, max_tokens=1500):
        return "ok"

    def tokenize(self, text: str):
        return list(range(len(text.split())))


@pytest.fixture
def dummy_client():
    return DummyClient()


# Ensure all code paths use a dummy LLM client unless ALLOW_NET_TESTS is set
@pytest.fixture(autouse=True)
def _force_dummy_llm(monkeypatch, dummy_client):
    """Ensure all code paths use a dummy LLM client during tests unless explicitly allowed.

    If ALLOW_NET_TESTS is set, this fixture does nothing and real clients may be constructed.
    """
    if os.getenv("ALLOW_NET_TESTS"):
        return

    # Prefer to override the builder used by CLI + Memoryos
    try:
        import memoryos.memoryos as mem

        if hasattr(mem, "_build_llm_client_from_env"):
            monkeypatch.setattr(
                mem, "_build_llm_client_from_env", lambda: dummy_client, raising=False
            )
    except Exception:
        pass

    # Ensure the shared builder used by the backend returns a dummy client
    try:
        import memoryos.utils as mem_utils

        if hasattr(mem_utils, "build_llm_client"):
            monkeypatch.setattr(
                mem_utils,
                "build_llm_client",
                lambda *args, **kwargs: dummy_client,
                raising=False,
            )
    except Exception:
        pass

    # Fallback: after Memoryos.__init__, ensure a client exists and is dummy
    try:
        from memoryos.memoryos import Memoryos

        original_init = Memoryos.__init__

        def patched_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            if not getattr(self, "client", None):
                self.client = dummy_client

        monkeypatch.setattr(Memoryos, "__init__", patched_init, raising=False)
    except Exception:
        pass
