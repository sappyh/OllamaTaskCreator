import pytest
import os
import shutil
from fastapi.testclient import TestClient
from webapp.src.main import app

client = TestClient(app)

TEST_VAULT_PATH = "./test_dummy_vault"
TEST_BASE_DIR = "./test_dummy_app_dir"

@pytest.fixture(autouse=True)
def setup_teardown_vault():
    # Setup
    os.environ["OLLAMA_CREATOR_BASE_DIR"] = TEST_BASE_DIR
    if os.path.exists(TEST_VAULT_PATH):
        shutil.rmtree(TEST_VAULT_PATH)
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
    
    yield
    
    # Teardown
    if os.path.exists(TEST_VAULT_PATH):
        shutil.rmtree(TEST_VAULT_PATH)
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
    if "OLLAMA_CREATOR_BASE_DIR" in os.environ:
        del os.environ["OLLAMA_CREATOR_BASE_DIR"]

def test_create_vault():
    response = client.post("/vault", json={"vault_path": TEST_VAULT_PATH})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert os.path.exists(TEST_VAULT_PATH)

def test_list_vaults():
    # Make sure vault is tracked first
    client.post("/vault", json={"vault_path": TEST_VAULT_PATH})
    
    response = client.get("/vaults")
    assert response.status_code == 200
    vaults = response.json()
    assert isinstance(vaults, list)
    # The actual path depends on CWD resolution, so check it exists as a substring
    assert any(TEST_VAULT_PATH.replace("./", "") in v for v in vaults)

def test_open_existing_vault():
    os.makedirs(TEST_VAULT_PATH)
    response = client.post("/vault", json={"vault_path": TEST_VAULT_PATH})
    assert response.status_code == 200
    assert response.json()["message"] == "Vault opened successfully"

def test_create_note():
    os.makedirs(TEST_VAULT_PATH)
    response = client.post(
        "/notes", 
        json={
            "vault_path": TEST_VAULT_PATH,
            "filename": "testnote.md",
            "content": "This is a test note."
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    with open(os.path.join(TEST_VAULT_PATH, "testnote.md"), "r") as f:
        assert f.read() == "This is a test note."

def test_list_notes():
    os.makedirs(TEST_VAULT_PATH)
    with open(os.path.join(TEST_VAULT_PATH, "note1.md"), "w") as f: f.write("1")
    with open(os.path.join(TEST_VAULT_PATH, "note2.md"), "w") as f: f.write("2")
    
    response = client.get(f"/notes?vault_path={TEST_VAULT_PATH}")
    assert response.status_code == 200
    notes = response.json()
    assert len(notes) == 2
    assert "note1.md" in notes
    assert "note2.md" in notes

def test_retrieve_note():
    os.makedirs(TEST_VAULT_PATH)
    with open(os.path.join(TEST_VAULT_PATH, "read_note.md"), "w") as f: 
        f.write("Hello World!")
        
    response = client.get(f"/notes/read_note.md?vault_path={TEST_VAULT_PATH}")
    assert response.status_code == 200
    assert response.json() == {"filename": "read_note.md", "content": "Hello World!"}

def test_update_note():
    os.makedirs(TEST_VAULT_PATH)
    with open(os.path.join(TEST_VAULT_PATH, "update_note.md"), "w") as f: 
        f.write("Old Content")
        
    response = client.put(
        f"/notes/update_note.md",
        json={"vault_path": TEST_VAULT_PATH, "content": "New Content"}
    )
    assert response.status_code == 200
    
    with open(os.path.join(TEST_VAULT_PATH, "update_note.md"), "r") as f:
        assert f.read() == "New Content"

def test_delete_note():
    os.makedirs(TEST_VAULT_PATH)
    file_path = os.path.join(TEST_VAULT_PATH, "delete_note.md")
    with open(file_path, "w") as f: 
        f.write("To be deleted")
        
    response = client.delete(f"/notes/delete_note.md?vault_path={TEST_VAULT_PATH}")
    assert response.status_code == 200
    assert not os.path.exists(file_path)

def test_note_not_found():
    os.makedirs(TEST_VAULT_PATH)
    response = client.get(f"/notes/missing.md?vault_path={TEST_VAULT_PATH}")
    assert response.status_code == 404
