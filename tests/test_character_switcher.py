from pathlib import Path
import os
import shutil
import tempfile
import zipfile
import pytest
import io
import sys

from guardian.character_switcher import (
    create_identity,
    list_companions,
    delete_companion,
    backup_identities,
    BASE_DIR
)

@pytest.fixture
def temp_identities_dir(monkeypatch):
    """Fixture to use a temporary directory for identities."""
    temp_dir = tempfile.mkdtemp()
    monkeypatch.setattr('guardian.character_switcher.BASE_DIR', Path(temp_dir))
    yield temp_dir
    shutil.rmtree(temp_dir)

def test_create_identity(temp_identities_dir):
    identity_name = "pytest_temp"
    create_identity(identity_name)
    identity_folder = os.path.join(temp_identities_dir, identity_name)
    identity_file = os.path.join(identity_folder, "identity.json")
    assert os.path.isdir(identity_folder), "Identity folder was not created."
    assert os.path.isfile(identity_file), "identity.json file was not created."
    # Cleanup
    shutil.rmtree(identity_folder)
    print("test_create_identity passed.")

def test_list_companions(temp_identities_dir, capsys):
    identity_name = "pytest_temp2"
    create_identity(identity_name)
    # Capture stdout
    list_companions()
    captured = capsys.readouterr()
    assert identity_name in captured.out, "Created identity not listed in companions."
    print("test_list_companions passed.")

def test_delete_companion(temp_identities_dir, monkeypatch):
    identity_name = "pytest_temp3"
    create_identity(identity_name)
    identity_folder = os.path.join(temp_identities_dir, identity_name)
    assert os.path.isdir(identity_folder)
    # Mock input to automatically confirm deletion
    monkeypatch.setattr('builtins.input', lambda _: identity_name)
    delete_companion(identity_name)
    assert not os.path.exists(identity_folder), "Identity folder was not deleted."
    print("test_delete_companion passed.")

def test_backup_identities(temp_identities_dir):
    # Create a dummy identity
    identity_name = "pytest_temp4"
    create_identity(identity_name)

    backup_file = backup_identities()
    assert os.path.isfile(backup_file), "Backup zip file was not created."
    # Check zip contents
    with zipfile.ZipFile(backup_file, 'r') as zf:
        members = zf.namelist()
        assert any(identity_name in m for m in members), "Identity not found in backup zip."
    # Cleanup
    os.remove(backup_file)
    print("test_backup_identities passed.")