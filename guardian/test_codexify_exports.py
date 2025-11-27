from datetime import datetime

import pytest


def test_save_entry_filename_prefix_and_template(monkeypatch):
    from guardian.server import codexify_api as api

    calls = {}

    def fake_export(
        records,
        format="md",
        filename=None,
        folder_id=None,
        credentials=None,
        template=None,
        service=None,
        share_anyone=None,
        content=None,
    ):
        calls["filename"] = filename
        # Return shape similar to export_to_gdrive
        return {
            "id": "fake",
            "name": filename,
            "webViewLink": "https://drive.google.com/file/d/fake/view",
        }

    monkeypatch.setenv("CODEXIFY_FILENAME_TEMPLATE", "{date}_{slug}.{ext}")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setenv(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )  # ensure no OAuth run

    monkeypatch.setattr(api, "export_to_gdrive", fake_export)
    monkeypatch.setattr(
        api, "build_drive_service", lambda logger=None: object()
    )

    today = datetime.now().strftime("%Y-%m-%d")
    req = api.SaveEntryRequest(
        title="Test Title", body="Body", format="md", dry_run=False
    )
    resp = api.save_entry(req)
    assert resp["ok"] is True
    assert calls["filename"].startswith(f"{today}_Test_Title")
    assert calls["filename"].endswith(".md")


def test_export_engine_default_filename_template(monkeypatch):
    # Use template without time for deterministic assertion
    monkeypatch.setenv("CODEXIFY_FILENAME_TEMPLATE", "{date}_{slug}.{ext}")
    from guardian import export_engine as ee

    today = datetime.now().strftime("%Y-%m-%d")

    # Dummy service to capture file metadata
    class _FilesReq:
        def __init__(self, body):
            self.body = body

        def execute(self):
            return {
                "id": "file123",
                "name": self.body["name"],
                "webViewLink": "https://drive.google.com/file/d/file123/view",
            }

    class _Files:
        def create(self, body=None, media_body=None, fields=None):
            return _FilesReq(body)

    class _PermReq:
        def execute(self):
            return {}

    class _Perms:
        def __init__(self, log):
            self.log = log

        def create(self, fileId=None, body=None):
            self.log.append((fileId, body))
            return _PermReq()

    class DummyService:
        def __init__(self):
            self.perm_log = []
            self._files = _Files()
            self._perms = _Perms(self.perm_log)

        def files(self):
            return self._files

        def permissions(self):
            return self._perms

    # Provide fake googleapiclient modules
    import sys
    import types

    class _MFU:
        def __init__(self, *a, **k):
            pass

    sys.modules["googleapiclient.http"] = types.SimpleNamespace(
        MediaFileUpload=_MFU
    )
    sys.modules["googleapiclient.discovery"] = types.SimpleNamespace(
        build=lambda *a, **k: None
    )

    svc = DummyService()
    result = ee.export_to_gdrive(
        [{"title": "X", "body": "Y"}], format="md", service=svc
    )
    assert result["name"].startswith(f"{today}_guardian_export")
    assert result["name"].endswith(".md")


def test_export_engine_share_anyone(monkeypatch):
    from guardian import export_engine as ee

    class _FilesReq:
        def __init__(self, body):
            self.body = body

        def execute(self):
            return {
                "id": "fileABC",
                "name": self.body["name"],
                "webViewLink": "https://drive.google.com/file/d/fileABC/view",
            }

    class _Files:
        def __init__(self, out):
            self.out = out

        def create(self, body=None, media_body=None, fields=None):
            self.out["name"] = body.get("name")
            return _FilesReq(body)

    class _PermReq:
        def execute(self):
            return {}

    class _Perms:
        def __init__(self, log):
            self.log = log

        def create(self, fileId=None, body=None):
            self.log.append((fileId, body))
            return _PermReq()

    class DummyService:
        def __init__(self):
            self.perm_log = []
            self._files_out = {}
            self._files = _Files(self._files_out)
            self._perms = _Perms(self.perm_log)

        def files(self):
            return self._files

        def permissions(self):
            return self._perms

    import sys
    import types

    class _MFU:
        def __init__(self, *a, **k):
            pass

    sys.modules["googleapiclient.http"] = types.SimpleNamespace(
        MediaFileUpload=_MFU
    )
    sys.modules["googleapiclient.discovery"] = types.SimpleNamespace(
        build=lambda *a, **k: None
    )

    svc = DummyService()
    res = ee.export_to_gdrive(
        records=[{"title": "A", "body": "B"}],
        format="md",
        service=svc,
        share_anyone=True,
    )
    # Ensure a permission was created for anyone/reader
    assert any(
        p[1] == {"type": "anyone", "role": "reader"} for p in svc.perm_log
    )


def test_api_error_mapping_permission_denied(monkeypatch):
    # Inject fake googleapiclient.errors.HttpError
    import sys
    import types

    class FakeHttpError(Exception):
        def __init__(self, status):
            self.status_code = status

    sys.modules["googleapiclient.errors"] = types.SimpleNamespace(
        HttpError=FakeHttpError
    )

    from guardian.server import codexify_api as api

    # Patch build service and export to raise 403
    monkeypatch.setattr(
        api, "build_drive_service", lambda logger=None: object()
    )

    def raiser(*a, **k):
        raise FakeHttpError(403)

    monkeypatch.setattr(api, "export_to_gdrive", raiser)

    # Prepare request
    req = api.SaveEntryRequest(title="T", body="B", format="md", dry_run=False)
    with pytest.raises(api.HTTPException) as exc:
        api.save_entry(req)
    assert exc.value.status_code == 400
    assert "Permission denied" in exc.value.detail


def test_api_error_mapping_invalid_folder(monkeypatch):
    import sys
    import types

    class FakeHttpError(Exception):
        def __init__(self, status):
            self.status_code = status

    sys.modules["googleapiclient.errors"] = types.SimpleNamespace(
        HttpError=FakeHttpError
    )

    from guardian.server import codexify_api as api

    monkeypatch.setattr(
        api, "build_drive_service", lambda logger=None: object()
    )

    def raiser(*a, **k):
        raise FakeHttpError(404)

    monkeypatch.setattr(api, "export_to_gdrive", raiser)

    req = api.SaveEntryRequest(title="T", body="B", format="md", dry_run=False)
    with pytest.raises(api.HTTPException) as exc:
        api.save_entry(req)
    assert exc.value.status_code == 400
    assert "Invalid or missing Drive folder" in exc.value.detail
