from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ops/private_preview_backup_restore_proof.sh"


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def _restore_run_block(script: str) -> str:
    start = script.index('docker run -d \\\n  --name "${RESTORE_CONTAINER}"')
    end = script.index('wait_for_postgres "${RESTORE_CONTAINER}"', start)
    return script[start:end]


def test_disposable_restore_identity_is_explicit_and_nonempty() -> None:
    script = _script_text()

    user_match = re.search(r'^RESTORE_POSTGRES_USER="([^"]+)"$', script, re.MULTILINE)
    database_match = re.search(
        r'^RESTORE_POSTGRES_DB="([^"]+)"$', script, re.MULTILINE
    )

    assert user_match is not None
    assert database_match is not None
    assert user_match.group(1) not in {"root", "postgres"}
    assert database_match.group(1)


def test_restore_identity_is_validated_before_container_start() -> None:
    script = _script_text()
    restore_start = script.index('RESTORE_SUFFIX=')
    run_start = script.index("docker run -d", restore_start)

    assert (
        script.index('[[ -n "${RESTORE_POSTGRES_USER}" ]]', restore_start)
        < run_start
    )
    assert (
        script.index('[[ -n "${RESTORE_POSTGRES_DB}" ]]', restore_start)
        < run_start
    )


def test_restore_container_initializes_both_identity_values_and_trust_auth() -> None:
    block = _restore_run_block(_script_text())

    assert '-e "POSTGRES_USER=${RESTORE_POSTGRES_USER}" \\' in block
    assert '-e "POSTGRES_DB=${RESTORE_POSTGRES_DB}" \\' in block
    assert "-e POSTGRES_HOST_AUTH_METHOD=trust" in block


def test_restore_clients_use_container_identity_environment() -> None:
    script = _script_text()

    assert 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' in script
    assert 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' in script
    assert (
        'pg_restore --exit-on-error --no-owner --no-acl -U "$POSTGRES_USER" '
        '-d "$POSTGRES_DB"'
    ) in script


def test_restore_has_no_root_role_fallback() -> None:
    script = _script_text()

    assert '-U root' not in script
    assert 'RESTORE_POSTGRES_USER="root"' not in script


def test_restore_isolation_contract_remains_intact() -> None:
    script = _script_text()
    block = _restore_run_block(script)

    assert "--network none" in block
    assert "codexify.proof=private-preview-backup-restore" in block
    assert 'source=${RESTORE_VOLUME}' in block
    assert '[[ "${RESTORE_DB_MOUNT}" != "${SOURCE_VOLUME}|true" ]]' in script
    assert '[[ "${RESTORE_PORTS}" == "{}" || "${RESTORE_PORTS}" == "null" ]]' in script
