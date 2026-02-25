import os
import shutil
import asyncio
import json
import requests_mock
from src.main import MainOrchestrator
from src.vikunjaInterface import VikunjaInterface

async def run_demo():
    print("=======================================")
    print(" Ollama Task Creator End-to-End Demo")
    print("=======================================\n")
    
    # Setup dummy Obsidian directory
    dummy_vault = "./dummy_vault"
    if os.path.exists(dummy_vault):
        shutil.rmtree(dummy_vault)
    os.makedirs(dummy_vault)
    
    with open(os.path.join(dummy_vault, "braindump.md"), "w") as f:
        f.write("I really need to call the plumber tomorrow at 3pm to fix the sink.\nAlso I shouldn't forget to buy milk and eggs for breakfast.\nWhat should I build next for my home lab? Setting up Nextcloud could be cool.")
        
    with open(os.path.join(dummy_vault, "meeting_notes.md"), "w") as f:
        f.write("Sarah mentioned we need to submit the Q3 financial report by Friday.\nI also need to follow up with John about the new API design document.")
    
    print(f"[*] Created Dummy Obsidian vault at {dummy_vault} with 2 notes.")

    # In our demo, we use requests-mock to intercept outgoing requests to the Vikunja API
    # so we don't have to spin up a Docker container just to show it works!
    print("[*] Intercepting all Vikunja requests with requests-mock (Mocking Server)...\n")
    
    with requests_mock.Mocker() as m:
        # Mock connection success
        m.get('http://mock-vikunja.local/api/v1/info', json={"version": "1.0"})
        
        # We need a custom callback to grab the posted tasks and give 'em mock IDs
        posted_tasks = []
        def task_creation_callback(request, context):
            task_data = request.json()
            posted_tasks.append(task_data)
            context.status_code = 201
            # Return a mock representation
            return {"id": len(posted_tasks) + 1000, "title": task_data.get("title")}
            
        m.put('http://mock-vikunja.local/api/v1/projects/42/tasks', json=task_creation_callback)
        
        # Initialize Orchestrator using tinyllama for the demo so it is fast!
        # In production this would use `ministral-3` or `qwen2.5-coder` etc.
        # We will use 'tinyllama' or 'qwen:0.5b' to make the demo run smoothly if not downloaded yet.
        orchestrator = MainOrchestrator(
            vault_path=dummy_vault,
            ollama_model="tinyllama", # Use tinyllama for demo speed
            vikunja_url="http://mock-vikunja.local", 
            vikunja_token="super-secret-demo-token", 
            vikunja_pid=42
        )
        
        # Run orchestrator
        await orchestrator.run()
        
        print("\n=======================================")
        print("          Demo Verification")
        print("=======================================")
        print(f"The LLM analyzed the dummy vault and sent {len(posted_tasks)} payload(s) targeting the Vikunja API.\n")
        print("Here are the raw JSON task payloads intercepted by the mock HTTP server passing over the wire:")
        print(json.dumps(posted_tasks, indent=4))
        print("=======================================")

if __name__ == "__main__":
    asyncio.run(run_demo())
