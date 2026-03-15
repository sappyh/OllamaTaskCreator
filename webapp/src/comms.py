import zmq
import zmq.asyncio
import asyncio
from typing import Optional, Dict, Any
from common.src import messages_pb2

class WebappCommsClient:
    """Handles ZMQ outbound commands and inbound status heartbeats for the Webapp."""
    def __init__(self, command_url: str = "tcp://127.0.0.1:5555", status_url: str = "tcp://127.0.0.1:5556"):
        self.command_url = command_url
        self.status_url = status_url
        self.zmq_ctx = zmq.asyncio.Context()
        
        self.pull_socket: Optional[zmq.asyncio.Socket] = None
        self._listen_task: Optional[asyncio.Task] = None
        
        # Centralized state storage
        self.state: Dict[str, Any] = {
            "is_connected": False,
            "current_status": "Unknown"
        }

    async def _status_listener_loop(self):
        """Continuously pulls Orchestrator heartbeats."""
        try:
            while True:
                if not self.pull_socket:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    message = await asyncio.wait_for(self.pull_socket.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.state["is_connected"] = False
                    self.state["current_status"] = "Disconnected"
                    continue

                status_msg = messages_pb2.OrchestratorStatus()
                status_msg.ParseFromString(message)
                
                self.state["is_connected"] = status_msg.is_alive
                
                status_map = {
                    messages_pb2.OrchestratorStatus.UNKNOWN: "Unknown",
                    messages_pb2.OrchestratorStatus.IDLE: "Idle",
                    messages_pb2.OrchestratorStatus.PROCESSING: "Processing"
                }
                self.state["current_status"] = status_map.get(status_msg.current_status, "Unknown")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[!] Error in comms status listener: {e}")
            self.state["is_connected"] = False

    async def start_listening(self):
        """Starts the PULL socket to listen for statuses."""
        self.pull_socket = self.zmq_ctx.socket(zmq.PULL)
        self.pull_socket.bind(self.status_url)
        self._listen_task = asyncio.create_task(self._status_listener_loop())

    async def stop_listening(self):
        """Stops the listening loop and closes the socket."""
        if self._listen_task:
            self._listen_task.cancel()
        if self.pull_socket:
            self.pull_socket.setsockopt(zmq.LINGER, 1000)
            self.pull_socket.close()

    def __del__(self):
        """Ensure the ZMQ context is terminated when the object is destroyed."""
        try:
            if hasattr(self, 'zmq_ctx'):
                self.zmq_ctx.term()
        except Exception:
            pass # Avoid noise during process teardown

    async def send_generate_tasks(self, vault_path: str):
        """Asynchronously pushes a command to the Orchestrator."""
        push_socket = self.zmq_ctx.socket(zmq.PUSH)
        push_socket.bind(self.command_url)
        
        command = messages_pb2.OrchestratorCommand()
        command.type = messages_pb2.OrchestratorCommand.GENERATE_TASKS
        command.vault_path = vault_path
        
        await push_socket.send(command.SerializeToString())
        push_socket.close(linger=100)
        
    def get_status(self) -> Dict[str, Any]:
        return self.state
