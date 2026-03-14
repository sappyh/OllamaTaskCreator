# OllamaTaskCreator

OllamaTaskCreator is a self-hosted, privacy-first automation pipeline that leverages large language models (via Ollama) to continuously read your personal notes, extract actionable items using GTD (Getting Things Done) principles, and automatically sync them to a task management target.

## Architecture

The project is designed with a **Decoupled Architecture** to ensure that data sources, AI processing, and task destinations remain cleanly separated. The repository consists of two distinct components that operate independently:

### 1. Webapp Component (`webapp/`)
A standalone directory providing a web-based GUI and REST API backend for managing your Markdown notes locally.
- **Backend:** A FastAPI server (`webapp.src.main:app`) managing local file I/O safely via Pydantic schemas. 
- **Frontend:** A raw Vanilla JS + CSS implementation (`webapp/src/static/`) providing a sleek user experience for editing notes, managing vaults, and visualizing your knowledge graph.
- **Interface:** The webapp implements the `BaseVaultManager` interface to structure its operations consistently.

### 2. Orchestrator Component (`orchestrator/`)
The background intelligence layer that reads your notes, parses actionable items, and syncs them. It operates entirely independently from the web layer.

#### Core Integrations
1. **Source Interface (`BaseNotesSource`)**
   - **Implementations:** `ObsidianInterface` (Local disk reads), `WebappNotesSource` (HTTP calls to the Webapp component APIs).
2. **AI Processing (`OllamaWrapper`)**
   - **Responsibility:** Use Generative AI logic to identify GTD tasks, extract implicit dependencies, and format output into machine-readable JSON payloads. Uses default local models like `llama3.1:8b`.
3. **Target Interface (`BaseTaskTarget`)**
   - **Implementations:** `VikunjaInterface` (Syncing structured payloads to the Vikunja Task REST API).
4. **Orchestrator Control Loop (`MainOrchestrator`)**
   - **Responsibility:** The centralized control loop tying the workflow together. Intakes notes, calls the LLM, parses the JSON payload, and bridges data to the Target API.

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
