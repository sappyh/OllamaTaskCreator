import json
import asyncio
import zmq
import zmq.asyncio
import sys
import os
from typing import Optional

# Ensure that the root directory is in the python path to allow direct execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from orchestrator.src.ollamaWrapper import OllamaWrapper
from orchestrator.src.comms import OrchestratorCommsServer
from orchestrator.src.webappTarget import WebappTaskTarget
from orchestrator.src.webappInterface import WebappNotesSource
from orchestrator.src.deduplicator import TaskDeduplicator

class MainOrchestrator:
    def __init__(self, ollama_model: str, webapp_url: str = "http://127.0.0.1:8000"):
        self.ollama_wrapper = OllamaWrapper(modelName=ollama_model)
        self.webapp_url = webapp_url.rstrip("/")
        self.task_target = WebappTaskTarget(webapp_base_url=self.webapp_url)
        self.deduplicator = TaskDeduplicator(self.ollama_wrapper)
        
        # Initialize Comms Interface
        self.comms_server = OrchestratorCommsServer()
        self.comms_server.register_command_handler(self._process_vault)

    async def _process_vault(self, vault_path: str):
        self.comms_server.set_processing_state(True)
        try:
            print(f"[*] Processing vault: {vault_path}")
            
            notes_source = WebappNotesSource(base_url=self.webapp_url, vault_path=vault_path)
                
            print(f"[*] Ensuring Ollama model '{self.ollama_wrapper.modelName}' is pulled...")
            await self.ollama_wrapper.initModel()
            
            files = notes_source.listAllFiles()
            notes_content = []
            for f in files:
                content = notes_source.retrieveContentFromFile(f)
                if content and content != NameError:
                    notes_content.append(content)
                    
            if not notes_content:
                print("[-] No notes found to process.")
                return

            print(f"[+] Found {len(notes_content)} notes. Sending to Ollama for GTD processing...")
            # CALLING ASYNC METHOD
            json_tasks_str = await self.ollama_wrapper.generateTasksFromNotes(notes_content)
            
            # Debug: print the raw output from Ollama
            print(f"DEBUG: Ollama raw response: {json_tasks_str}")
            
            try:
                tasks_data = json.loads(json_tasks_str)
                tasks_list = tasks_data.get("tasks", [])
                print(f"[+] Extracted {len(tasks_list)} tasks from notes!")
            except json.JSONDecodeError:
                print("[-] Failed to decode JSON from Ollama.")
                return

            print("[*] Verifying Webapp connection...")
            if not self.task_target.test_connection():
                print(f"[-] Cannot connect to Webapp at {self.webapp_url}")
                return
            
            # --- DEDUPLICATION STEP ---
            existing_tasks = []
            try:
                print("[*] Fetching existing tasks for deduplication...")
                existing_tasks = self.task_target.fetch_tasks(vault_path=vault_path)
                await self.deduplicator.prepare_existing_tasks(existing_tasks)
            except Exception as e:
                print(f"[!] Warning: Failed to fetch existing tasks ({str(e)}). Skipping deduplication.")
                
            print(f"[+] Feeding tasks directly to Webapp...")
            success_count = 0
            skipped_count = 0
            for task_data in tasks_list:
                name = task_data.get("name") or task_data.get("title", "Untitled Task")
                desc = task_data.get("description", "")
                priority = task_data.get("priority", "Medium")
                status = task_data.get("status", "TODO")
                deadline = task_data.get("deadline")
                scheduled = task_data.get("scheduled")
                tags = task_data.get("tags", [])
                
                if name.strip():
                    # Check for duplicates
                    dup_name, score = await self.deduplicator.find_duplicate(task_data)
                    if dup_name:
                        print(f"    -> Skipped: {name} (Duplicate of '{dup_name}', Score: {score:.2f})")
                        skipped_count += 1
                        continue

                    try:
                        self.task_target.create_task(
                            name=name,
                            description=desc,
                            priority=priority,
                            status=status,
                            deadline=deadline,
                            scheduled=scheduled,
                            tags=tags,
                            vault_path=vault_path
                        )
                        success_count += 1
                        print(f"    -> Pushed: {name}")
                    except Exception as e:
                        print(f"    -> Failed: {name} ({str(e)})")
                        
            print(f"[+] Sync Complete: {success_count} pushed, {skipped_count} skipped (duplicates), {len(tasks_list)} total extracted.")
        finally:
            self.comms_server.set_processing_state(False)

    async def run(self):
        print("[+] Starting Orchestrator ZMQ Worker Loop (v2.0 - With Semantic Deduplication)")
        await self.comms_server.start()
        
        try:
            # Just keep the application alive, the comms background tasks handle everything
            while True:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            await self.comms_server.stop()

if __name__ == "__main__":
    # FORCE LAMA3.1:8B AS DEFAULT
    default_model = "llama3.1:8b"
    model = os.environ.get("OLLAMA_MODEL", default_model)
    if model == "llama3":
        print(f"[!] Warning: 'llama3' detected, switching to default '{default_model}'")
        model = default_model
    
    webapp_host = os.environ.get("WEBAPP_HOST", "127.0.0.1")
    webapp_url = f"http://{webapp_host}:8000"
    
    orchestrator = MainOrchestrator(
        ollama_model=model,
        webapp_url=webapp_url
    )
    
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\n[-] Shutting down orchestrator...")
