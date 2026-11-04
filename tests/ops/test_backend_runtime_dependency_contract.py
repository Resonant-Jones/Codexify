from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "backend" / "Dockerfile"
BACKEND_REQUIREMENTS = ROOT / "backend" / "requirements.txt"
CANONICAL_REQUIREMENTS_PATH = "/tmp/backend/requirements.txt"


def _builder_dependency_stage() -> str:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    return dockerfile.split("# Pre-stage scripts and configs for later copy", 1)[0]


def _runtime_stage() -> str:
    """The canonical ``runtime`` stage: the common backend image."""
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    _, separator, remainder = dockerfile.partition(
        "FROM python:3.11.14-slim AS runtime"
    )
    assert separator, "the canonical runtime stage must exist"
    return remainder.split("\nFROM ", 1)[0]


def _apt_installed_packages(stage: str) -> list[str]:
    """The packages the stage installs through apt-get."""
    match = re.search(
        r"apt-get install -y --no-install-recommends((?:[^\n]*\\\n)*[^\n]*)",
        stage,
    )
    assert match, "the runtime stage must install packages with apt-get"
    return [
        token
        for token in re.split(r"[\s\\&]+", match.group(1))
        if token
    ]


def test_backend_runtime_installs_the_explicit_canonical_manifest() -> None:
    dockerfile = _builder_dependency_stage()

    assert "COPY backend/requirements.txt /tmp/backend/requirements.txt" in dockerfile
    assert f'req_file = "{CANONICAL_REQUIREMENTS_PATH}"' in dockerfile
    assert "os.path.isfile(req_file)" in dockerfile
    assert "canonical backend requirements missing" in dockerfile
    assert "subprocess.check_call(['pip', 'install', '-r', req_file])" in dockerfile


def test_backend_runtime_has_no_flattening_or_fallback_dependency_selection() -> None:
    dockerfile = _builder_dependency_stage()

    assert "COPY requirements/ backend/requirements.txt* ./" not in dockerfile
    assert '"./all.txt"' not in dockerfile
    assert "candidates =" not in dockerfile


def test_canonical_backend_manifest_retains_current_postgresql_driver_contract() -> None:
    requirements = BACKEND_REQUIREMENTS.read_text(encoding="utf-8")

    assert "psycopg2-binary>=2.9.9" in requirements
    assert "psycopg[binary]>=3.2.10" in requirements


def test_dependency_repair_does_not_add_direct_driver_or_database_url_rewrites() -> None:
    dockerfile = _builder_dependency_stage()

    assert "pip install psycopg2" not in dockerfile
    assert "postgresql+psycopg" not in dockerfile
    assert "DATABASE_URL" not in dockerfile


def test_canonical_runtime_installs_git_for_authorized_repository_operations() -> None:
    """Git is a mandatory prerequisite of the runtime image, not an extra.

    Guardian's repository-binding authority resolves a working-tree root with
    Git, and the coding worker's mutation enforcement inspects porcelain
    state with Git. A runtime without an executable Git CLI cannot perform
    those authorized operations, so the binary belongs in the canonical
    runtime stage next to the other OS packages.
    """
    runtime = _runtime_stage()

    assert "git" in _apt_installed_packages(runtime)
    # The existing package set and the apt-cache cleanup are preserved.
    assert "bubblewrap" in _apt_installed_packages(runtime)
    assert "ffmpeg" in _apt_installed_packages(runtime)
    assert "rm -rf /var/lib/apt/lists/*" in runtime


def test_coding_worker_runtime_inherits_git_from_the_canonical_runtime() -> None:
    """The worker image must not carry a second, divergent Git installation."""
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "FROM runtime AS worker-coding-runtime" in dockerfile
    worker_stage = dockerfile.split("FROM runtime AS worker-coding-runtime", 1)[1]
    worker_stage = worker_stage.split("\nFROM ", 1)[0]
    assert "apt-get install" not in worker_stage
    assert "git" in _apt_installed_packages(_runtime_stage())


def test_runtime_does_not_install_git_at_worker_startup() -> None:
    """Git must be present in the image, not fetched while the worker starts."""
    startup = (
        ROOT / "backend" / "scripts" / "docker" / "run_worker_coding.py"
    ).read_text(encoding="utf-8")

    assert "apt-get" not in startup
    assert "apt install" not in startup
    assert "pip install" not in startup
