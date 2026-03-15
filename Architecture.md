# Technical Architecture

This document outlines the design decisions and class relationships that enable OllamaTaskCreator's distributed, local-first operation.

## Architectural Rationale

The project follows a **Decoupled Engine-Hub** pattern to solve specific hardware constraints:
1.  **Distributed Compute**: LLMs require significant GPU resources, while a task dashboard should be "always on" but low-power. By decoupling the **Orchestrator** (Engine) from the **Web App** (Hub), we allow the AI to run on a workstation while the UI stays live on a Raspberry Pi.
2.  **Robust Communication**: We use **ZeroMQ (ZMQ)** and **Protocol Buffers (Protobuf)** instead of REST for internal component sync. This provides:
    -   **Asynchronous Heartbeats**: The Webapp knows if the engine is alive without polling.
    -   **Schema Safety**: Protobuf ensures both components agree on exactly what a "Task" or "Command" looks like.
3.  **Semantic Intelligence**: Unlike simple keyword matching, we use **Vector Embeddings** (`nomic-embed-text`) to identify duplicates. This allows the system to recognize that "Finish the report" and "Complete the quarterly draft" are semantically the same.

## Class Diagram

```mermaid
classDiagram
    namespace Common {
        class OrchestratorCommand {
            +CommandType type
            +string vault_path
        }
        class OrchestratorStatus {
            +bool is_alive
            +StatusType current_status
        }
    }

    namespace WebApp {
        class WebappCommsClient {
            +Dict state
            +start_listening()
            +send_generate_tasks(vault_path)
        }
        class WebappNotesSource {
            +string vault_path
            +listAllFiles()
            +retrieveContentFromFile(file)
        }
    }

    namespace Orchestrator {
        class MainOrchestrator {
            +OllamaWrapper ollama
            +TaskDeduplicator deduplicator
            +WebappTaskTarget target
            -process_vault(path)
        }
        class OllamaWrapper {
            +string modelName
            +generateTasksFromNotes(notes)
            +getEmbedding(text)
        }
        class TaskDeduplicator {
            +float threshold
            +prepare_existing_tasks(tasks)
            +find_duplicate(task)
        }
        class WebappTaskTarget {
            +string base_url
            +fetch_tasks(vault)
            +create_task(task_data)
        }
    }

    WebappCommsClient ..> OrchestratorCommand : Sends
    MainOrchestrator ..> OrchestratorStatus : Pushes heartbeats
    MainOrchestrator --> OllamaWrapper : Uses for AI
    MainOrchestrator --> TaskDeduplicator : Filters duplicates
    MainOrchestrator --> WebappTaskTarget : Pushes tasks
    TaskDeduplicator --> OllamaWrapper : Requests Embeddings
```

## Communication Flow

1.  **Web App** triggers a `GENERATE_TASKS` command via ZMQ PUSH.
2.  **Orchestrator** receives the command and switches status to `PROCESSING`.
3.  **Orchestrator** fetches notes content from the **Web App** REST API.
4.  **Ollama** processes the text into a structured JSON task list.
5.  **TaskDeduplicator** filters the list against currently existing tasks in the Web App.
6.  New tasks are pushed to the **Web App** via REST.
