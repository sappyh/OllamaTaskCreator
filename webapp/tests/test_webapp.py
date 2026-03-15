import pytest
import os
import shutil
from fastapi.testclient import TestClient
import webapp.src.main as main_module
from webapp.src.vault_manager import LocalVaultManager

app = main_module.app
client = TestClient(app)

TEST_BASE_DIR = os.path.join(os.path.dirname(__file__), "_test_app_dir")
TEST_VAULT_NAME = "test_vault"

@pytest.fixture(autouse=True)
def setup_teardown_vault():
    # Setup: create a fresh test base dir and swap the vault_manager
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
    os.makedirs(TEST_BASE_DIR, exist_ok=True)
    
    original_manager = main_module.vault_manager
    main_module.vault_manager = LocalVaultManager(base_dir=TEST_BASE_DIR)
    
    yield
    
    # Teardown: restore original manager and clean up
    main_module.vault_manager = original_manager
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)

def _vault_path():
    """Returns the resolved absolute vault path for assertions on the filesystem."""
    return os.path.join(TEST_BASE_DIR, TEST_VAULT_NAME)

def test_create_vault():
    response = client.post("/vault", json={"vault_path": TEST_VAULT_NAME})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert os.path.exists(_vault_path())

def test_list_vaults():
    # Make sure vault is tracked first
    client.post("/vault", json={"vault_path": TEST_VAULT_NAME})
    
    response = client.get("/vaults")
    assert response.status_code == 200
    vaults = response.json()
    assert isinstance(vaults, list)
    assert any(TEST_VAULT_NAME in v for v in vaults)

def test_open_existing_vault():
    os.makedirs(_vault_path())
    response = client.post("/vault", json={"vault_path": TEST_VAULT_NAME})
    assert response.status_code == 200
    assert response.json()["message"] == "Vault opened successfully"

def test_create_note():
    # Create the vault first via the API
    client.post("/vault", json={"vault_path": TEST_VAULT_NAME})
    response = client.post(
        "/notes", 
        json={
            "vault_path": _vault_path(),
            "filename": "testnote.md",
            "content": "This is a test note."
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    with open(os.path.join(_vault_path(), "testnote.md"), "r") as f:
        assert f.read() == "This is a test note."

def test_list_notes():
    os.makedirs(_vault_path(), exist_ok=True)
    with open(os.path.join(_vault_path(), "note1.md"), "w") as f: f.write("1")
    with open(os.path.join(_vault_path(), "note2.md"), "w") as f: f.write("2")
    
    response = client.get(f"/notes?vault_path={_vault_path()}")
    assert response.status_code == 200
    notes = response.json()
    assert len(notes) == 2
    assert "note1.md" in notes
    assert "note2.md" in notes

def test_retrieve_note():
    os.makedirs(_vault_path(), exist_ok=True)
    with open(os.path.join(_vault_path(), "read_note.md"), "w") as f: 
        f.write("Hello World!")
        
    response = client.get(f"/notes/read_note.md?vault_path={_vault_path()}")
    assert response.status_code == 200
    assert response.json() == {"filename": "read_note.md", "content": "Hello World!"}

def test_update_note():
    os.makedirs(_vault_path(), exist_ok=True)
    with open(os.path.join(_vault_path(), "update_note.md"), "w") as f: 
        f.write("Old Content")
        
    response = client.put(
        f"/notes/update_note.md",
        json={"vault_path": _vault_path(), "content": "New Content"}
    )
    assert response.status_code == 200
    
    with open(os.path.join(_vault_path(), "update_note.md"), "r") as f:
        assert f.read() == "New Content"

def test_delete_note():
    os.makedirs(_vault_path(), exist_ok=True)
    file_path = os.path.join(_vault_path(), "delete_note.md")
    with open(file_path, "w") as f: 
        f.write("To be deleted")
        
    response = client.delete(f"/notes/delete_note.md?vault_path={_vault_path()}")
    assert response.status_code == 200
    assert not os.path.exists(file_path)

def test_note_not_found():
    os.makedirs(_vault_path(), exist_ok=True)
    response = client.get(f"/notes/missing.md?vault_path={_vault_path()}")
    assert response.status_code == 404
