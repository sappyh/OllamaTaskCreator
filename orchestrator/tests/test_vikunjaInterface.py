import os
import sys
import pytest
import requests
import requests_mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from orchestrator.src.vikunjaInterface import VikunjaInterface

@pytest.fixture
def vikunja():
    return VikunjaInterface(base_url="http://localhost:3456", api_token="dummy_token")

def test_test_connection_success(vikunja, requests_mock):
    requests_mock.get('http://localhost:3456/api/v1/info', status_code=200, json={"version": "0.20.0"})
    assert vikunja.test_connection() == True

def test_test_connection_failure(vikunja, requests_mock):
    requests_mock.get('http://localhost:3456/api/v1/info', status_code=401)
    assert vikunja.test_connection() == False

def test_test_connection_exception(vikunja, requests_mock):
    requests_mock.get('http://localhost:3456/api/v1/info', exc=requests.exceptions.ConnectionError)
    assert vikunja.test_connection() == False

def test_get_projects_success(vikunja, requests_mock):
    mock_projects = [{"id": 1, "title": "Inbox"}, {"id": 2, "title": "Work"}]
    requests_mock.get('http://localhost:3456/api/v1/projects', status_code=200, json=mock_projects)
    
    projects = vikunja.get_projects()
    assert len(projects) == 2
    assert projects[0]['title'] == "Inbox"

def test_get_projects_failure(vikunja, requests_mock):
    requests_mock.get('http://localhost:3456/api/v1/projects', status_code=500)
    assert vikunja.get_projects() == []

def test_get_projects_exception(vikunja, requests_mock):
    requests_mock.get('http://localhost:3456/api/v1/projects', exc=requests.exceptions.Timeout)
    assert vikunja.get_projects() == []


def test_create_task_success(vikunja, requests_mock):
    mock_task = {"id": 101, "title": "Buy Milk", "description": "Need milk for coffee"}
    requests_mock.put('http://localhost:3456/api/v1/projects/1/tasks', status_code=201, json=mock_task)
    
    task = vikunja.create_task(project_id=1, title="Buy Milk", description="Need milk for coffee")
    assert task['id'] == 101
    assert task['title'] == "Buy Milk"
    # Ensure headers were sent
    assert requests_mock.last_request.headers['Authorization'] == 'Bearer dummy_token'
    assert requests_mock.last_request.json() == {"title": "Buy Milk", "description": "Need milk for coffee"}

def test_create_task_failure(vikunja, requests_mock):
    requests_mock.put('http://localhost:3456/api/v1/projects/1/tasks', status_code=400)
    task = vikunja.create_task(project_id=1, title="Bad Task")
    assert task == {}

def test_create_task_exception(vikunja, requests_mock):
    requests_mock.put('http://localhost:3456/api/v1/projects/1/tasks', exc=requests.exceptions.ConnectionError)
    task = vikunja.create_task(project_id=1, title="Exception task")
    assert task == {}
