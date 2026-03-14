import json
import asyncio
import zmq
import zmq.asyncio
import sys
import os
from typing import Optional

# Ensure that the root directory is in the python path to allow direct execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from orchestrator.src.obsidianInterface import ObsidianInterface
from orchestrator.src.ollamaWrapper import OllamaWrapper
from orchestrator.src.vikunjaInterface import VikunjaInterface
from orchestrator.src.comms import OrchestratorCommsServer

class MainOrchestrator:
    def __init__(self, ollama_model: str, vikunja_url: str, vikunja_token: str, vikunja_pid: int, webapp_url: Optional[str] = None):
        self.ollama_wrapper = OllamaWrapper(modelName=ollama_model)
        self.vikunja = VikunjaInterface(base_url=vikunja_url, api_token=vikunja_token)
        self.project_id = vikunja_pid
        self.webapp_url = webapp_url
        
        # Initialize Comms Interface
        self.comms_server = OrchestratorCommsServer()
        self.comms_server.register_command_handler(self._process_vault)

    async def _process_vault(self, vault_path: str):
        self.comms_server.set_processing_state(True)
        try:
            print(f"[*] Processing vault: {vault_path}")
            
            if self.webapp_url:
                from orchestrator.src.webappInterface import WebappNotesSource
                notes_source = WebappNotesSource(base_url=self.webapp_url, vault_path=vault_path)
            else:
                notes_source = ObsidianInterface(vault_path)
                
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
            json_tasks_str = self.ollama_wrapper.generateTasksFromNotes(notes_content)
            
            try:
                tasks_data = json.loads(json_tasks_str)
                tasks_list = tasks_data.get("tasks", [])
                print(f"[+] Extracted {len(tasks_list)} tasks from notes!")
            except json.JSONDecodeError:
                print("[-] Failed to decode JSON from Ollama.")
                return

            print("[*] Verifying Vikunja connection...")
            if not self.vikunja.test_connection():
                print("[-] Cannot connect to Vikunja using the provided URL and Token.")
                return
                
            print(f"[+] Syncing to Vikunja Project ID {self.project_id}...")
            success_count = 0
            for task in tasks_list:
                title = task.get("title", "Untitled Task")
                desc = task.get("description", "")
                if title.strip():
                    vt = self.vikunja.create_task(self.project_id, title=title, description=desc)
                    if vt.get("id"):
                        success_count += 1
                        print(f"    -> Created: {title}")
                        
            print(f"[+] Successfully pushed {success_count}/{len(tasks_list)} tasks to Vikunja.")
        finally:
            self.comms_server.set_processing_state(False)

    async def run(self):
        print("[+] Starting Orchestrator ZMQ Worker Loop")
        self.comms_server.start()
        
        try:
            # Just keep the application alive, the comms background tasks handle everything
            while True:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.comms_server.stop()

if __name__ == "__main__":
    # Example standalone execution footprint
    # In production, these should be loaded from env vars or CLI args
    model = os.environ.get("OLLAMA_MODEL", "llama3")
    vikunja_url = os.environ.get("VIKUNJA_URL", "http://localhost:3456")
    vikunja_token = os.environ.get("VIKUNJA_TOKEN", "test_token")
    vikunja_pid = int(os.environ.get("VIKUNJA_PID", "1"))
    
    orchestrator = MainOrchestrator(
        ollama_model=model,
        vikunja_url=vikunja_url,
        vikunja_token=vikunja_token,
        vikunja_pid=vikunja_pid
    )
    
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\n[-] Shutting down orchestrator...")
