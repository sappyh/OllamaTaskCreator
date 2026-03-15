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
    class OrchestratorCommand {
        +type
        +vault_path
    }
    class OrchestratorStatus {
        +is_alive
        +current_status
    }

    namespace WebApp_RaspberryPi {
        class BaseVaultManager {
            <<Interface>>
            +create_vault()
            +list_vaults()
            +get_tasks()
        }
        class LocalVaultManager {
            +base_dir
            +upsert_task()
        }
        class WebappCommsClient {
            +state
            +send_generate_tasks()
        }
    }

    namespace Orchestrator_PC {
        class MainOrchestrator {
            +ollama
            +deduplicator
            +target
            -process_vault()
        }
        class WebappNotesSource {
            +base_url
            +listAllFiles()
            +retrieveContent()
        }
        class OllamaWrapper {
            +generateTasks()
            +getEmbedding()
        }
        class TaskDeduplicator {
            +threshold
            +find_duplicate()
        }
        class WebappTaskTarget {
            +fetch_tasks()
            +create_task()
        }
    }

    %% Control Channel (ZMQ/Protobuf)
    WebappCommsClient ..> OrchestratorCommand : ZMQ PUSH (Generate)
    MainOrchestrator ..> OrchestratorStatus : ZMQ PUSH (Heartbeat)

    %% Data Flow
    MainOrchestrator --> WebappNotesSource : Reads Notes
    MainOrchestrator --> OllamaWrapper : AI Extraction
    MainOrchestrator --> TaskDeduplicator : Semantic Filter
    MainOrchestrator --> WebappTaskTarget : Sync Tasks
    
    LocalVaultManager --|> BaseVaultManager : Implements
    WebappNotesSource --|> BaseNotesSource : Implements (Proxy)
    TaskDeduplicator --> OllamaWrapper : Requests Embeds
```

## Communication Flow

1.  **Web App** triggers a `GENERATE_TASKS` command via ZMQ PUSH.
2.  **Orchestrator** receives the command and switches status to `PROCESSING`.
3.  **Orchestrator** (via `WebappNotesSource`) fetches notes content from the **Web App** REST API.
4.  **Ollama** processes the text into a structured JSON task list.
5.  **TaskDeduplicator** filters the list against currently existing tasks in the Web App.
6.  New tasks are pushed to the **Web App** via REST.
