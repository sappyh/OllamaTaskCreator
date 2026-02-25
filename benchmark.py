import asyncio
import time
import json
import sys
from src.ollamaWrapper import OllamaWrapper

# List of models < 8B parameters to benchmark
MODELS = [
    "qwen2.5:7b",       # Qwen 2.5 7B (Closest to Qwen-3 8B which does not officially exist yet)
    "deepseek-r1:8b",   # Deepseek R1 8B parameter
    "ministral-3",      # Ministral-3 (User's original default model)
    "llama3.1:8b"       # Added for a solid 8B baseline comparison
]

TEST_NOTES = [
    "I really need to call the plumber tomorrow at 3pm to fix the sink.",
    "Draft the quarterly review report by Friday morning.",
    "My manager said we need to fix the vague 'reporting bug' before the client meeting. I don't know what time the client meeting is, I'll have to ask Sarah.",
    "Need to get groceries. Or maybe I should just use UberEats? Actually, if I cook pasta, I need to check if we have basil first. Not sure what to do yet.",
    "Review PR #452, but I can't start this until John finishes writing the unit tests for it.",
    "Brainstorm ideas for the new marketing campaign with the team next Tuesday. Remind everyone to bring their metrics."
]

async def run_benchmark():
    print("====================================================")
    print("     OllamaTaskCreator Model Benchmark (< 8B)       ")
    print("====================================================\n")
    
    results = []

    for model_name in MODELS:
        print(f"[*] Starting benchmark for model: {model_name}")
        wrapper = OllamaWrapper(modelName=model_name)
        
        # 1. Pull / Initialize model
        print(f"    - Ensuring model is downloaded (this may take time the first run)...")
        pull_start = time.time()
        await wrapper.initModel()
        pull_end = time.time()
        print(f"    - Model ready (init took {pull_end - pull_start:.2f} seconds)")
        
        # 2. Benchmark Task Generation Execution Time
        print(f"    - Generating tasks from {len(TEST_NOTES)} notes...")
        
        exec_start = time.time()
        output_str = wrapper.generateTasksFromNotes(TEST_NOTES)
        exec_end = time.time()
        
        duration = exec_end - exec_start
        print(f"    - Execution Time: {duration:.2f} seconds")
        
        # 3. Validate JSON Output
        is_valid_json = False
        task_count = 0
        try:
            data = json.loads(output_str)
            is_valid_json = True
            tasks = data.get("tasks", [])
            task_count = len(tasks)
            print(f"    - Valid JSON! Parsed {task_count} tasks.")
        except json.JSONDecodeError:
            print(f"    - ERROR: Output was not valid JSON!")
            print(f"    - Raw Output Snippet: {output_str[:200]}...")
            
        results.append({
            "model": model_name,
            "duration": duration,
            "valid_json": is_valid_json,
            "task_count": task_count
        })
        
        print("-" * 50)

    print("\n====================================================")
    print("                 Benchmark Summary                  ")
    print("====================================================")
    print(f"{'Model Name':<15} | {'Time (s)':<10} | {'Valid JSON':<10} | {'Tasks Found'}")
    print("-" * 60)
    for r in results:
        print(f"{r['model']:<15} | {r['duration']:<10.2f} | {str(r['valid_json']):<10} | {r['task_count']}")
    print("====================================================")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
