import pytest
import requests_mock
from orchestrator.src.webappTarget import WebappTaskTarget

@pytest.fixture
def webapp_target():
    return WebappTaskTarget(webapp_base_url="http://test-webapp:8000")

def test_webapp_target_connection(webapp_target):
    with requests_mock.Mocker() as m:
        m.get("http://test-webapp:8000/vaults", json=["/vault1"], status_code=200)
        assert webapp_target.test_connection() is True

def test_webapp_target_connection_fail(webapp_target):
    with requests_mock.Mocker() as m:
        m.get("http://test-webapp:8000/vaults", status_code=500)
        assert webapp_target.test_connection() is False

def test_create_task_success(webapp_target):
    vault_path = "/my/vault"
    task_data = {
        "name": "Int Test",
        "description": "Desc",
        "priority": "Low",
        "deadline": None,
        "scheduled": None,
        "tags": ["test"]
    }
    
    with requests_mock.Mocker() as m:
        m.post("http://test-webapp:8000/vaults/tasks?vault_path=%2Fmy%2Fvault", 
               json={"status": "success", "task": {"id": "123", **task_data}}, 
               status_code=200)
        
        result = webapp_target.create_task(
            name="Int Test",
            description="Desc",
            priority="Low",
            tags=["test"],
            vault_path=vault_path
        )
        
        assert result["status"] == "success"
        assert result["task"]["name"] == "Int Test"

def test_create_task_fail_no_vault(webapp_target):
    with pytest.raises(ValueError, match="vault_path is required"):
        webapp_target.create_task(name="Fail")
