# OllamaTaskCreator

OllamaTaskCreator is a self-hosted, privacy-first automation pipeline that leverages large language models (via Ollama) to continuously read your personal notes, extract actionable items using GTD (Getting Things Done) principles, and automatically sync them to a task management target.

## Architecture

The project is designed with a **Decoupled Architecture** to ensure that data sources, AI processing, and task destinations remain cleanly separated. The repository consists of three distinct components that interface via **ZeroMQ (ZMQ)** and **Protocol Buffers**:

### 1. Webapp Component (`webapp/`)
Acts as the primary application server providing a web-based GUI and REST API backend.
- **Backend:** A FastAPI server (`webapp.src.main:app`) managing local file I/O safely via Pydantic schemas. 
- **ZMQ Client:** It runs a persistent `WebappCommsClient` to listen to background Orchestrator status heartbeats and to trigger task generation (`POST /orchestrator/generate`).

### 2. Orchestrator Component (`orchestrator/`)
The background intelligence worker that processes tasks asynchronously. 
- **ZMQ Server:** Sits idle running the `OrchestratorCommsServer` PULL socket, waiting for commands from the Webapp while emitting PUSH heartbeats.
- **AI Processing (`OllamaWrapper`):** Uses Generative AI logic to identify GTD tasks and format output into machine-readable JSON payloads. Uses default local models like `llama3.1:8b`.
- **Target Interface (`VikunjaInterface`):** Syncs structured payloads to the Vikunja Task REST API.

### 3. Common Component (`common/`)
The shared interface schemas ensuring the two components can communicate safely.
- **Protobuf Schemas:** Contains `messages.proto` (and compiled `messages_pb2.py`) which explicitly define `OrchestratorCommand` and `OrchestratorStatus`, leveraging strict Enums like `StatusType.PROCESSING`.
- **Integration Tests:** Houses cross-component testing suites testing the isolated Comms abstraction layers (`test_zmq_interface.py`).

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
