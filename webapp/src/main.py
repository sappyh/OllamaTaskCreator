from fastapi import FastAPI, HTTPException, Query, Body, Path as APIPath
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import os
import json
# Add the project root to sys.path to allow running directly via `python src/webapp/main.py`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import asyncio
import zmq
import zmq.asyncio
from typing import List
from common.src import messages_pb2

from webapp.src.comms import WebappCommsClient
from webapp.src.vault_manager import LocalVaultManager
from webapp.src.interfaces import BaseVaultManager

# Initialize the Webapp ZMQ Client
comms_client = WebappCommsClient()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Spawn background listener
    await comms_client.start_listening()
    yield
    # Shutdown: Clean up listening task
    await comms_client.stop_listening()

app = FastAPI(
    title="Vault Notes API", 
    description="API for managing Markdown notes in local directories (vaults)",
    lifespan=lifespan
)



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

@app.delete("/vault")
def delete_vault(vault_path: str = Query(...)):
    try:
        return vault_manager.delete_vault(vault_path)
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

# --- Task API Endpoints ---
@app.get("/vaults/tasks")
def get_vault_tasks(vault_path: str = Query(...)):
    try:
        return vault_manager.get_tasks(vault_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vaults/tasks")
def upsert_vault_task(vault_path: str = Query(...), task: dict = Body(...)):
    try:
        return vault_manager.upsert_task(vault_path, task)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/vaults/tasks/{task_id}")
def delete_vault_task(task_id: str, vault_path: str = Query(...)):
    try:
        return vault_manager.delete_task(vault_path, task_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orchestrator/status")
def get_orchestrator_status():
    return comms_client.get_status()

class GenerateTasksRequest(BaseModel):
    vault_path: str

@app.post("/orchestrator/generate")
async def generate_tasks(request: GenerateTasksRequest):
    """Pushes a GENERATE_TASKS command to the orchestrator via ZMQ."""
    if not comms_client.get_status().get("is_connected"):
        raise HTTPException(status_code=503, detail="Orchestrator is not connected")
        
    try:
        await comms_client.send_generate_tasks(request.vault_path)
        return {"status": "success", "message": "Task generation initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
