from fastapi import FastAPI, HTTPException, Query, Body, Path as APIPath
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os
import json
# Add the project root to sys.path to allow running directly via `python src/webapp/main.py`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pathlib import Path
from typing import List, Optional

app = FastAPI(title="Vault Notes API", description="API for managing Markdown notes in local directories (vaults)")

# Resolve the absolute path to the static directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Mount static files to serve the frontend
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Expose index.html at root
from fastapi.responses import FileResponse
@app.get("/")
def read_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

class VaultRequest(BaseModel):
    vault_path: str

class NoteRequest(BaseModel):
    vault_path: str
    content: str
    
class NoteCreateRequest(BaseModel):
    vault_path: str
    filename: str
    content: str

from webapp.src.interfaces import BaseVaultManager

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

    def _get_vault_path(self, vault_path: str) -> Path:
        path = Path(vault_path).expanduser()
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError("Vault not found or is not a directory")
        return path

    def create_vault(self, vault_path: str) -> dict:
        path = Path(vault_path).expanduser()
        path_str = str(path)
        if path.exists():
            if path.is_dir():
                self._track_vault(path_str)
                return {"status": "success", "message": "Vault opened successfully", "path": path_str}
            else:
                raise ValueError("Path exists but is not a directory")
                
        try:
            os.makedirs(path, exist_ok=True)
            self._track_vault(path_str)
            return {"status": "success", "message": "Vault created successfully", "path": path_str}
        except Exception as e:
            raise RuntimeError(f"Failed to create vault: {str(e)}")

    def list_vaults(self) -> List[str]:
        # Filter out any that might have been deleted from disk manually
        valid_vaults = []
        changed = False
        for vp in self.tracked_vaults:
            if Path(vp).exists() and Path(vp).is_dir():
                valid_vaults.append(vp)
            else:
                changed = True
        
        if changed:
            self.tracked_vaults = valid_vaults
            self._save_tracked_vaults()
            
        return valid_vaults

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

# Instantiate the interface
vault_manager: BaseVaultManager = LocalVaultManager()

@app.post("/vault")
def create_vault(request: VaultRequest):
    try:
        return vault_manager.create_vault(request.vault_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vaults", response_model=List[str])
def list_vaults():
    try:
        return vault_manager.list_vaults()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes", response_model=List[str])
def list_notes(vault_path: str):
    try:
        return vault_manager.list_notes(vault_path)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notes")
def create_note(request: NoteCreateRequest):
    try:
        return vault_manager.create_note(request.vault_path, request.filename, request.content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes/{filename}")
def retrieve_note(filename: str, vault_path: str):
    try:
        return vault_manager.retrieve_note(vault_path, filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/notes/{filename}")
def update_note(filename: str, request: NoteRequest):
    try:
        return vault_manager.update_note(request.vault_path, filename, request.content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/notes/{filename}")
def delete_note(filename: str, vault_path: str):
    try:
        return vault_manager.delete_note(vault_path, filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
