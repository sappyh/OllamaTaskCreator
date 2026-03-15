import os
import json
import shutil
from pathlib import Path
from typing import List, Optional
from webapp.src.interfaces import BaseVaultManager
from common.src.models import Task

class LocalVaultManager(BaseVaultManager):
    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.environ.get("OLLAMA_CREATOR_BASE_DIR", "~/.OllamaCreator")
            
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.tracking_file = self.base_dir / "tracked_vaults.json"
        
        self.tracked_vaults = self._load_tracked_vaults()
        
        # Ensure the default base_dir itself is always registered as a valid vault!
        self._track_vault(str(self.base_dir))

    def _load_tracked_vaults(self) -> List[str]:
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_tracked_vaults(self):
        with open(self.tracking_file, "w") as f:
            json.dump(self.tracked_vaults, f)

    def _track_vault(self, vault_path: str):
        if vault_path not in self.tracked_vaults:
            self.tracked_vaults.append(vault_path)
            self._save_tracked_vaults()

    def _resolve_vault_path(self, vault_path: str) -> Path:
        """Centralized helper to always resolve vault paths relative to base_dir if not absolute."""
        path = Path(vault_path).expanduser()
        if not path.is_absolute():
            path = self.base_dir / vault_path
        return path.resolve()

    def _get_vault_path(self, vault_path: str) -> Path:
        path = self._resolve_vault_path(vault_path)
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(f"Vault not found at {path}")
        return path

    def create_vault(self, vault_path: str) -> dict:
        path = self._resolve_vault_path(vault_path)
        path_str = str(path)
        
        if path.exists():
            if path.is_dir():
                self._track_vault(path_str)
                return {"status": "success", "message": "Vault opened successfully", "path": path_str}
            else:
                raise ValueError(f"Path {path_str} exists but is not a directory")
                
        try:
            path.mkdir(parents=True, exist_ok=True)
            self._track_vault(path_str)
            return {"status": "success", "message": "Vault created successfully", "path": path_str}
        except Exception as e:
            raise RuntimeError(f"Failed to create vault directory at {path_str}: {str(e)}")

    def delete_vault(self, vault_path: str) -> dict:
        path = self._resolve_vault_path(vault_path)
        # Safety check: Don't delete base_dir itself
        if path == self.base_dir:
            raise ValueError("Cannot delete the base directory")

        if path.exists() and path.is_dir():
            try:
                shutil.rmtree(path)
            except Exception as e:
                raise RuntimeError(f"Failed to delete vault directory {path}: {str(e)}")
        
        # Always remove from tracking if exists
        path_str = str(path)
        if path_str in self.tracked_vaults:
            self.tracked_vaults.remove(path_str)
            self._save_tracked_vaults()
            
        return {"status": "success", "message": "Vault deleted successfully"}

    def list_vaults(self) -> List[str]:
        # 1. Automatic Discovery: Scan subdirectories of base_dir
        try:
            for item in self.base_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    path_str = str(item.resolve())
                    if path_str not in self.tracked_vaults:
                        self.tracked_vaults.append(path_str)
        except Exception:
            pass

        # 2. Filter out any that might have been deleted from disk manually
        # OR match the base directory (we don't want to show the root as a vault)
        valid_vaults = []
        changed = False
        base_dir_resolved = self.base_dir.resolve()
        
        for vp in self.tracked_vaults:
            p = Path(vp).expanduser().resolve()
            if p.exists() and p.is_dir() and p != base_dir_resolved:
                valid_vaults.append(str(p))
            else:
                changed = True
        
        if changed:
            self.tracked_vaults = list(set(valid_vaults)) # Remove duplicates
            self._save_tracked_vaults()
            
        return self.tracked_vaults

    def list_notes(self, vault_path: str) -> List[str]:
        path = self._get_vault_path(vault_path)
        notes = []
        try:
            for file in path.iterdir():
                if file.is_file() and file.suffix.lower() == '.md':
                    notes.append(file.name)
            return notes
        except Exception as e:
            raise RuntimeError(f"Failed to list notes: {str(e)}")

    def create_note(self, vault_path: str, filename: str, content: str) -> dict:
        path = self._get_vault_path(vault_path)
        file_path = path / filename
        
        if file_path.exists():
            raise FileExistsError("Note already exists")
            
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "message": "Note created successfully"}
        except Exception as e:
            raise RuntimeError(f"Failed to create note: {str(e)}")

    def retrieve_note(self, vault_path: str, filename: str) -> dict:
        path = self._get_vault_path(vault_path)
        file_path = path / filename
        
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("Note not found")
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"filename": filename, "content": content}
        except Exception as e:
            raise RuntimeError(f"Failed to read note: {str(e)}")

    def update_note(self, vault_path: str, filename: str, content: str) -> dict:
        path = self._get_vault_path(vault_path)
        file_path = path / filename
        
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("Note not found")
            
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "message": "Note updated successfully"}
        except Exception as e:
            raise RuntimeError(f"Failed to update note: {str(e)}")

    def delete_note(self, vault_path: str, filename: str) -> dict:
        path = self._get_vault_path(vault_path)
        file_path = path / filename
        
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("Note not found")
            
        try:
            os.remove(file_path)
            return {"status": "success", "message": "Note deleted successfully"}
        except Exception as e:
            raise RuntimeError(f"Failed to delete note: {str(e)}")

    def _get_tasks_file(self, vault_path: str) -> Path:
        return self._get_vault_path(vault_path) / "tasks.json"

    def get_tasks(self, vault_path: str) -> List[dict]:
        tasks_file = self._get_tasks_file(vault_path)
        if not tasks_file.exists():
            return []
        try:
            with open(tasks_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def upsert_task(self, vault_path: str, task_data: dict) -> dict:
        tasks = self.get_tasks(vault_path)
        new_task = Task.from_dict(task_data)
        
        # Check if task already exists (by ID)
        updated = False
        for i, t in enumerate(tasks):
            if t.get("id") == new_task.id:
                tasks[i] = new_task.to_dict()
                updated = True
                break
        
        if not updated:
            tasks.append(new_task.to_dict())
            
        try:
            with open(self._get_tasks_file(vault_path), "w") as f:
                json.dump(tasks, f, indent=4)
            return {"status": "success", "task": new_task.to_dict()}
        except Exception as e:
            raise RuntimeError(f"Failed to save tasks: {str(e)}")

    def delete_task(self, vault_path: str, task_id: str) -> dict:
        tasks = self.get_tasks(vault_path)
        original_len = len(tasks)
        tasks = [t for t in tasks if t.get("id") != task_id]
        
        if len(tasks) == original_len:
            raise FileNotFoundError("Task not found")
            
        try:
            with open(self._get_tasks_file(vault_path), "w") as f:
                json.dump(tasks, f, indent=4)
            return {"status": "success"}
        except Exception as e:
            raise RuntimeError(f"Failed to delete task: {str(e)}")
