import json
from src.obsidianInterface import ObsidianInterface
from src.ollamaWrapper import OllamaWrapper
from src.vikunjaInterface import VikunjaInterface

class MainOrchestrator:
    def __init__(self, vault_path: str, ollama_model: str, vikunja_url: str, vikunja_token: str, vikunja_pid: int):
        self.obsidian = ObsidianInterface(vault_path)
        self.ollama_wrapper = OllamaWrapper(modelName=ollama_model)
        self.vikunja = VikunjaInterface(base_url=vikunja_url, api_token=vikunja_token)
        self.project_id = vikunja_pid
        
    async def run(self):
        print("[+] Starting Extractor Workflow")
        
        # 1. Init model
        print(f"[*] Ensuring Ollama model '{self.ollama_wrapper.modelName}' is pulled (this may take a while if missing)...")
        await self.ollama_wrapper.initModel()
        
        # 2. Reading Obsidian files
        print(f"[*] Reading files from Obsidian vault at {self.obsidian.path}")
        files = self.obsidian.listAllFiles()
        notes_content = []
        for f in files:
            content = self.obsidian.retrieveContentFromFile(f)
            if content and content != NameError:
                notes_content.append(content)
                
        if not notes_content:
            print("[-] No notes found to process.")
            return

        print(f"[+] Found {len(notes_content)} notes. Sending to Ollama for GTD processing...")
        
        # 3. Process with Ollama
        json_tasks_str = self.ollama_wrapper.generateTasksFromNotes(notes_content)
        
        try:
            tasks_data = json.loads(json_tasks_str)
            tasks_list = tasks_data.get("tasks", [])
            print(f"[+] Extracted {len(tasks_list)} tasks from notes!")
        except json.JSONDecodeError:
            print("[-] Failed to decode JSON from Ollama.")
            return

        # 4. Check Vikunja Connection
        print("[*] Verifying Vikunja connection...")
        if not self.vikunja.test_connection():
            print("[-] Cannot connect to Vikunja using the provided URL and Token.")
            print("[!] Generated tasks but aborted sync. Tasks were:")
            for t in tasks_list:
                print(f"    - {t.get('title')}: {t.get('description', '')}")
            return
            
        # 5. Push to Vikunja
        print(f"[+] Syncing to Vikunja Project ID {self.project_id}...")
        success_count = 0
        for task in tasks_list:
            title = task.get("title", "Untitled Task")
            desc = task.get("description", "")
            # Ensure it is a valid create_task
            if title.strip():
                vt = self.vikunja.create_task(self.project_id, title=title, description=desc)
                if vt.get("id"):
                    success_count += 1
                    print(f"    -> Created: {title}")
                else:
                    print(f"    -> Failed: {title}")
                    
        print(f"[+] Successfully pushed {success_count}/{len(tasks_list)} tasks to Vikunja.")
