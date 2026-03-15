import pytest
import json
import os
from pathlib import Path
from webapp.src.main import LocalVaultManager
from common.src.models import Task, TaskPriority

@pytest.fixture
def temp_vault(tmp_path):
    vault_dir = tmp_path / "test_vault"
    vault_dir.mkdir()
    return str(vault_dir)

@pytest.fixture
def vault_manager(tmp_path):
    mgr = LocalVaultManager(base_dir=str(tmp_path))
    return mgr

def test_upsert_task_persistence(vault_manager, temp_vault):
    task_data = {
        "name": "Test Task",
        "description": "Test Description",
        "priority": "High",
        "tags": ["unit-test"]
    }
    
    # 1. Create vault
    vault_manager.create_vault(temp_vault)
    
    # 2. Upsert task
    result = vault_manager.upsert_task(temp_vault, task_data)
    assert result["status"] == "success"
    task_id = result["task"]["id"]
    
    # 3. Verify in memory
    tasks = vault_manager.get_tasks(temp_vault)
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Test Task"
    assert tasks[0]["id"] == task_id
    
    # 4. Verify on disk
    tasks_file = Path(temp_vault) / "tasks.json"
    assert tasks_file.exists()
    with open(tasks_file, "r") as f:
        disk_tasks = json.load(f)
    assert len(disk_tasks) == 1
    assert disk_tasks[0]["id"] == task_id

def test_update_existing_task(vault_manager, temp_vault):
    vault_manager.create_vault(temp_vault)
    
    # Create
    task_data = {"name": "Task 1", "priority": "Low"}
    result = vault_manager.upsert_task(temp_vault, task_data)
    task_id = result["task"]["id"]
    
    # Update
    update_data = {"id": task_id, "name": "Task 1 Updated", "priority": "High"}
    vault_manager.upsert_task(temp_vault, update_data)
    
    tasks = vault_manager.get_tasks(temp_vault)
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Task 1 Updated"
    assert tasks[0]["priority"] == "High"

def test_delete_task(vault_manager, temp_vault):
    vault_manager.create_vault(temp_vault)
    
    # Create
    result = vault_manager.upsert_task(temp_vault, {"name": "To Delete"})
    task_id = result["task"]["id"]
    
    # Delete
    vault_manager.delete_task(temp_vault, task_id)
    
    tasks = vault_manager.get_tasks(temp_vault)
    assert len(tasks) == 0
    
    tasks_file = Path(temp_vault) / "tasks.json"
    with open(tasks_file, "r") as f:
        disk_tasks = json.load(f)
    assert len(disk_tasks) == 0

def test_get_tasks_empty_vault(vault_manager, temp_vault):
    vault_manager.create_vault(temp_vault)
    tasks = vault_manager.get_tasks(temp_vault)
    assert tasks == []
