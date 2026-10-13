"""Protect canonical generation and dependency-free source setup boundaries."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / 'scripts/generate-bootstrap-bindings.py'


def _load_generator():
    spec = importlib.util.spec_from_file_location('bootstrap_binding_generator', GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _setup_helpers(monkeypatch, tmp_path):
    # Execute the Python body as a module, without running installer operations.
    # It must initialize using only the standard library and dependency-free files.
    monkeypatch.setattr(sys, 'argv', ['-', str(ROOT / 'scripts/setup'), '--json', '--state-dir', str(tmp_path / 'state')])
    module = types.ModuleType('bootstrap_source_helpers')
    source = (ROOT / 'scripts/setup').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    exec(compile(source, str(ROOT / 'scripts/setup'), 'exec'), module.__dict__)
    module.env_path = tmp_path / '.env'
    monkeypatch.setattr(module, 'run', lambda *args, **kwargs: '')
    return module


def test_generated_bindings_match_canonical_source():
    generator = _load_generator()
    contract = json.loads(generator.SOURCE.read_text())
    for path, expected in generator.render_bindings(contract).items():
        assert path.read_text() == expected
    assert contract['snapshot']['core_ready'] == 'boolean'
    assert contract['snapshot']['inference_ready'] == 'boolean'


def test_stale_binding_fails_drift_check(tmp_path):
    isolated_generator = tmp_path / 'scripts/generate-bootstrap-bindings.py'
    isolated_generator.parent.mkdir()
    shutil.copyfile(GENERATOR, isolated_generator)
    source = tmp_path / 'contracts/bootstrap/readiness.v1.json'
    source.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / 'contracts/bootstrap/readiness.v1.json', source)
    subprocess.run([sys.executable, str(isolated_generator)], check=True)
    stale = tmp_path / 'frontend/src/contracts/bootstrapReadiness.generated.ts'
    stale.write_text(stale.read_text().replace('coreReady: boolean', 'coreReady: string'))
    result = subprocess.run([sys.executable, str(isolated_generator), '--check'], capture_output=True, text=True)
    assert result.returncode == 1
    assert 'bootstrapReadiness.generated.ts' in result.stdout


def test_source_starts_without_site_packages():
    body = (ROOT / 'scripts/setup').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    result = subprocess.run([sys.executable, '-S', '-', str(ROOT / 'scripts/setup'), '--help'], input=body, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '--json' in result.stdout


def test_source_preserves_secrets_choices_and_comments(monkeypatch, tmp_path):
    module = _setup_helpers(monkeypatch, tmp_path)
    original = '# My installation\nGUARDIAN_API_KEY=' + 'a' * 64 + '\nPOSTGRES_PASSWORD=existing-secret\nNEO4J_PASS=existing-storage-secret\nLOCAL_BASE_URL=http://host.docker.internal:8000/v1\nCUSTOM_OPTION=chosen\n'
    module.env_path.write_text(original)
    module.configure('docker')
    first = module.env_path.read_text()
    module.configure('docker')
    assert module.env_path.read_text() == first
    for line in original.splitlines():
        assert line in first
    assert module.values['GUARDIAN_API_KEY'] == 'a' * 64
    assert module.values['POSTGRES_PASSWORD'] == 'existing-secret'


def test_source_does_not_normalize_conflicting_user_choice(monkeypatch, tmp_path, capsys):
    module = _setup_helpers(monkeypatch, tmp_path)
    module.env_path.write_text('LLM_PROVIDER=other\n')
    with pytest.raises(SystemExit) as exc:
        module.configure('docker')
    assert exc.value.code == 2
    assert module.env_path.read_text() == 'LLM_PROVIDER=other\n'
    event = json.loads(capsys.readouterr().out)
    assert event['workflow'] == 'action_required'
    assert event['humanAction'] == 'consent_required'


def test_existing_volumes_without_configuration_require_recovery(monkeypatch, tmp_path, capsys):
    module = _setup_helpers(monkeypatch, tmp_path)
    monkeypatch.setattr(module, 'run', lambda *args, **kwargs: 'codexify_pg_data\n')
    with pytest.raises(SystemExit):
        module.configure('docker')
    assert not module.env_path.exists()
    assert json.loads(capsys.readouterr().out)['humanAction'] == 'credentials_required'


def test_inference_does_not_accept_outer_health_when_model_unavailable(monkeypatch, tmp_path):
    module = _setup_helpers(monkeypatch, tmp_path)
    payload = {'status': 'ok', 'details': {'provider': 'local', 'configured_model_available': False, 'models_available': False}}
    assert module.local_inference_ready(payload) is False
    payload['details'].update(configured_model_available=True, models_available=True)
    assert module.local_inference_ready(payload) is True
    payload['details']['provider_runtime'] = {'available': False}
    assert module.local_inference_ready(payload) is False


def test_network_retry_is_bounded_and_checkpoint_is_resumable(monkeypatch, tmp_path, capsys):
    module = _setup_helpers(monkeypatch, tmp_path)
    # Restore the actual command adapter after isolating helper initialization.
    source = (ROOT / 'scripts/setup').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    tree = __import__('ast').parse(source)
    function = next(node for node in tree.body if isinstance(node, __import__('ast').FunctionDef) and node.name == 'run')
    exec(compile(__import__('ast').Module(body=[function], type_ignores=[]), '<run>', 'exec'), module.__dict__)
    calls = []
    def fail(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, 'network is unreachable')
    monkeypatch.setattr(module.subprocess, 'run', fail)
    monkeypatch.setattr(module.time, 'sleep', lambda *args: None)
    with pytest.raises(SystemExit):
        module.run(['docker', 'compose', 'pull'], retry=True, failure_action=module.Action.NETWORK_UNAVAILABLE)
    assert len(calls) == 3
    checkpoint = json.loads((tmp_path / 'state/checkpoint.json').read_text())
    assert checkpoint['workflow'] == 'paused'
    assert checkpoint['humanAction'] == 'network_unavailable'
    assert checkpoint['coreReady'] is False
    assert checkpoint['resume'] == './scripts/setup'
    assert 'network is unreachable' in (tmp_path / 'state/setup.log').read_text()


def test_source_reports_supported_profile_conflict_before_mutation(monkeypatch, tmp_path, capsys):
    module = _setup_helpers(monkeypatch, tmp_path)
    original = 'LOCAL_RUNTIME_PRESET=ollama\nLOCAL_BASE_URL=http://127.0.0.1:11434/v1\n'
    module.env_path.write_text(original)
    with pytest.raises(SystemExit): module.configure('docker')
    assert module.env_path.read_text() == original
    assert json.loads(capsys.readouterr().out)['humanAction'] == 'consent_required'


def test_new_install_with_existing_preferences_generates_strong_storage_secret(monkeypatch, tmp_path):
    module = _setup_helpers(monkeypatch, tmp_path)
    module.env_path.write_text('CUSTOM_OPTION=chosen\n')
    module.configure('docker')
    first = module.values['POSTGRES_PASSWORD']
    assert len(first) == 48
    assert first != 'codexify'
    module.configure('docker')
    assert module.values['POSTGRES_PASSWORD'] == first


def test_missing_python_reports_canonical_action_without_host_mutation(tmp_path):
    result = subprocess.run(['/bin/sh', str(ROOT / 'scripts/setup'), '--json'], env={'PATH': str(tmp_path)}, capture_output=True, text=True)
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload['workflow'] == 'action_required'
    assert payload['humanAction'] == 'prerequisite_unavailable'
    assert payload['coreReady'] is False
    assert not list(tmp_path.iterdir())


def test_existing_compose_project_identity_is_used_for_data_inventory(monkeypatch, tmp_path):
    module = _setup_helpers(monkeypatch, tmp_path)
    module.env_path.write_text('COMPOSE_PROJECT_NAME=my-personal-install\n')
    module.args.project_name = None
    calls = []
    monkeypatch.setattr(module, 'run', lambda command, **kwargs: calls.append(command) or '')
    module.configure('docker')
    assert module.args.project_name == 'my-personal-install'
    assert 'label=com.docker.compose.project=my-personal-install' in calls[0]
    assert 'COMPOSE_PROJECT_NAME=my-personal-install' in module.env_path.read_text()


def test_source_can_observe_healthy_queue_inside_inference_degraded_chat_health(monkeypatch, tmp_path):
    import io
    import urllib.error
    module = _setup_helpers(monkeypatch, tmp_path)
    def degraded(*args, **kwargs):
        raise urllib.error.HTTPError('http://127.0.0.1/health/chat', 503, 'inference unavailable', {}, io.BytesIO(b'{"status":"degraded","completion_service":{"ok":true,"redis_reachable":true}}'))
    monkeypatch.setattr(module.urllib.request, 'urlopen', degraded)
    assert module.probe('http://127.0.0.1/health/chat', allow_degraded=True)['completion_service']['ok'] is True
    assert module.probe('http://127.0.0.1/health') is None


def test_core_health_requires_real_boolean_signals(monkeypatch, tmp_path):
    module = _setup_helpers(monkeypatch, tmp_path)
    assert module.core_health_ready({'status':'ok'}, {'completion_service':{'ok':True,'redis_reachable':True}})
    assert not module.core_health_ready({'status':'ok'}, {'completion_service':{'ok':'false','redis_reachable':True}})
    assert not module.core_health_ready([], {'completion_service':{'ok':True,'redis_reachable':True}})
    assert not module.core_health_ready({'status':'ok'}, {'completion_service':[]})


def test_source_preserves_existing_model_choice_when_canonical_field_is_missing(monkeypatch, tmp_path):
    module = _setup_helpers(monkeypatch, tmp_path)
    module.env_path.write_text('LOCAL_LLM_MODEL=chosen-existing-model\n')
    module.configure('docker')
    assert module.values['LOCAL_CHAT_MODEL'] == 'chosen-existing-model'
    assert module.values['LOCAL_LLM_MODEL'] == 'chosen-existing-model'


def test_source_redacts_short_existing_credentials(monkeypatch, tmp_path):
    module = _setup_helpers(monkeypatch, tmp_path)
    module.values = {'LOCAL_API_KEY': 'abc', 'POSTGRES_PASSWORD': 'abcd'}
    assert module.redact('abc abcd') == '<redacted> <redacted>'


def test_source_malformed_nested_inference_health_fails_closed(monkeypatch, tmp_path):
    module = _setup_helpers(monkeypatch, tmp_path)
    for key in ('provider_runtime', 'endpoint_resolution'):
        details = {'provider': 'local', 'configured_model_available': True, 'models_available': True, key: 'invalid'}
        assert module.local_inference_ready({'status': 'ok', 'details': details}) is False
