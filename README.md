# OllamaTaskCreator

OllamaTaskCreator is a self-hosted, privacy-first automation pipeline that leverages large language models (via Ollama) to continuously read your personal notes, extract actionable items using GTD (Getting Things Done) principles, and automatically sync them to a task management target.

## Architecture

The project is designed with a **Generic Interface Architecture** to ensure that data sources, AI processing, and task destinations remain fully decoupled and horizontally scalable.

### Core Components

1. **Source Interface (`BaseNotesSource`)**
   - **Responsibility:** Ingest text-based notes.
   - **Current Implementation:** `ObsidianInterface`
   - **Description:** A concrete implementation that recursively scans a local directory (e.g., an Obsidian Vault), validates markdown files, and pulls string content. Inheriting the `BaseNotesSource` allows for rapid drop-in replacements like `NotionInterface` or `GoogleDocsInterface` in the future.

2. **AI Processing (`OllamaWrapper`)**
   - **Responsibility:** Use Generative AI logic to identify GTD tasks, extract implicit dependencies, and format output.
   - **Current Implementation:** Native `ollama` library bindings.
   - **Description:** Uses offline LLMs under the 8B parameter threshold (default: `llama3.1:8b`) to securely read brain dumps without transmitting personal data over the internet. The wrapper strictly commands JSON syntax returns to ensure programmatic integrity. It also initializes asynchronously so inference limits are cleanly respected.

3. **Target Interface (`BaseTaskTarget`)**
   - **Responsibility:** Sync structured payload elements to external applications.
   - **Current Implementation:** `VikunjaInterface`
   - **Description:** A concrete implementation hitting the Vikunja REST API `/projects/{id}/tasks` endpoint. Like the source layer, implementing `BaseTaskTarget` allows developers to easily swap out Vikunja for apps like `TodoistInterface` or `JiraInterface` using identical function signatures.

4. **Orchestrator (`MainOrchestrator`)**
   - **Responsibility:** The centralized control loop tying the workflow together.
   - **Description:** Instantiates the source, initializes the selected Ollama model securely, loops through the ingested documents, captures the model's generated JSON payload, evaluates connectivity with the target, and bridges the payload across the pipeline.

## Getting Started

### Prerequisites
- Python 3.9+
- [Ollama](https://ollama.com/) running locally.
- A functional Task Target instance (like Vikunja).

### Installation
```bash
# Clone the repository
git clone https://github.com/example/ollamataskcreator.git
cd OllamaTaskCreator

# Setup a virtual environment
python -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Running the End-to-End Environment
You can safely test the payload structure locally using mocked `requests` before you provision a server:
```bash
python demo.py
```
This script establishes a dummy Obsidian vault, requests `tinyllama` to parse 4 actions out of mock context, and prints the simulated API JSON packages that passed to the mocked Target instance over the HTTP layer!

### Supported Local Models
Based on heavy native logic benchmarking within the repository, processing GTD structures offline yields the strongest efficiency running the 8-Billion scale:
- `llama3.1:8b` (Default)
- `qwen2.5:7b` (Runner up)
- `ministral-3`
*Avoid heavy `<think>` architecture reasoning models (like `deepseek-r1`) for pipeline data bridges unless you have significant offline GPU horsepower.*
