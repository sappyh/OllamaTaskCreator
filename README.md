# OllamaTaskCreator 🚀

OllamaTaskCreator is a privacy-first, self-hosted AI task automation pipeline. It uses local LLMs (via Ollama) to monitor your personal notes, extract actionable items, and sync them to a beautiful task management interface.

See [Architecture.md](Architecture.md) for detailed technical diagrams and design decisions.

## 🏗 Architecture (Distributed Setup)

The system is split into two main components, designed to run in a distributed environment:

### 1. **Web App (Stabilizer)** 🍓
Designed to run on a **Raspberry Pi** or home server.
- **Frontend**: A modern, glassmorphic UI for managing tasks and notes.
- **Backend**: FastAPI server that serves the UI and acts as the ZMQ central hub.
- **ZMQ Role**: **Binds** to ports 5555 (Commands) and 5556 (Status).

### 2. **Orchestrator (Engine)** 💻
Designed to run on a **PC / Workstation** with a GPU for fast AI processing.
- **AI Extraction**: Uses `llama3.1:8b` to decompose complex notes into atomic, actionable tasks.
- **Semantic Deduplication**: Uses `nomic-embed-text` embeddings to prevent duplicate tasks, even if they are rephrased.
- **ZMQ Role**: **Connects** to the Web App's IP to receive commands and send heartbeats.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.9+**
- **Ollama** (Running on your PC)
- **nomic-embed-text** model (`ollama pull nomic-embed-text`)
- **llama3.1:8b** model (`ollama pull llama3.1:8b`)

### 1. Setup Web App (on Raspberry Pi)
```bash
# On your Rpi
git clone https://github.com/rana/OllamaTaskCreator.git
cd OllamaTaskCreator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python webapp/src/main.py
```
*The Web App will start on `http://0.0.0.0:8000`.*

#### Auto-start on Boot (systemd)
```bash
# Copy the service file and enable it for your user
sudo cp ollama-webapp@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ollama-webapp@$USER
sudo systemctl start ollama-webapp@$USER

# Check status
sudo systemctl status ollama-webapp@$USER
```
> **Note**: The service assumes the repo is at `~/OllamaTaskCreator` with a `venv/` inside it.

### 2. Setup Orchestrator (on PC)
```bash
# On your PC
export WEBAPP_HOST="<RPI_IP>"               # Used for both REST API and ZMQ comms
export OLLAMA_HOST="http://localhost:11434"
python orchestrator/src/main.py
```

---

## ✨ Features

- **Brain-to-Task Pipeline**: Just write a messy note, and the AI extracts specific TODOs.
- **Atomic Decomposition**: Complex goals (e.g., "Build a weather app") are broken into 5-10 technical sub-tasks.
- **Semantic Deduplication**: Smart enough to know that "Buy milk" and "Purchase some milk" are the same task.
- **Sidebar Filtering**: Real-time filtering of tasks by AI-generated tags.
- **Zero Cloud**: Your data never leaves your local network.

## 🛠 Tech Stack
- **Backend**: FastAPI, ZMQ, Protobuf.
- **AI**: Ollama (Llama 3.1, Nomic Embed).
- **Frontend**: Vanilla JS, Modern CSS (Glassmorphism).

## 🧹 Repository Contents
- `webapp/`: UI and API server.
- `orchestrator/`: AI logic and deduplication engine.
- `common/`: Shared Protobuf definitions and models.
- `dummy_vault/`: Example directory for your notes.
