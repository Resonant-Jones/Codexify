from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "backend" / "Dockerfile"
BACKEND_REQUIREMENTS = ROOT / "backend" / "requirements.txt"
CANONICAL_REQUIREMENTS_PATH = "/tmp/backend/requirements.txt"


def _builder_dependency_stage() -> str:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    return dockerfile.split("# Pre-stage scripts and configs for later copy", 1)[0]


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
