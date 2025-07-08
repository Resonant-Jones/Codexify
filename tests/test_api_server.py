from fastapi.testclient import TestClient
import sys
import types
import os

sys.modules.setdefault('pandas', types.ModuleType('pandas'))
notion_stub = types.ModuleType('notion_client')
class FakeClient:
    def __init__(self, **kwargs):
        pass

notion_stub.Client = FakeClient
sys.modules.setdefault('notion_client', notion_stub)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from guardian.api_server import app, export_to_gdrive, import_from_gdrive, import_from_icloud, create_notion_database_from_records

client = TestClient(app)


def test_export_gdrive(monkeypatch):
    called = {}

    def fake_export(records, format="md", folder_id=None):
        called['args'] = (records, format, folder_id)
        return {'id': '123'}

    monkeypatch.setattr('guardian.api_server.export_to_gdrive', fake_export)

    resp = client.post('/guardian/export-gdrive', json={'records': [{'a': 1}]})
    assert resp.status_code == 200
    assert resp.json()['result'] == {'id': '123'}
    assert called['args'][0] == [{'a': 1}]


def test_import_gdrive(monkeypatch):
    monkeypatch.setattr('guardian.api_server.import_from_gdrive', lambda **kw: ['f1'])
    resp = client.post('/guardian/import-gdrive', json={})
    assert resp.status_code == 200
    assert resp.json()['files'] == ['f1']


def test_import_icloud(monkeypatch):
    monkeypatch.setattr('guardian.api_server.import_from_icloud', lambda *a: ['f2'])
    resp = client.post('/guardian/import-icloud', json={})
    assert resp.status_code == 200
    assert resp.json()['files'] == ['f2']


def test_codexify_create(monkeypatch):
    def fake_create(records, parent_id, token, db_title=None, with_template=True):
        return 'db123'

    monkeypatch.setattr('guardian.api_server.create_notion_database_from_records', fake_create)
    resp = client.post('/codexify/create', json={
        'records': [{'t': 1}],
        'parent_id': 'pid',
        'token': 'tok'
    })
    assert resp.status_code == 200
    assert resp.json()['db_id'] == 'db123'
