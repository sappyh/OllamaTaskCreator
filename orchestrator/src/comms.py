import zmq
import zmq.asyncio
import asyncio
import os
from typing import Callable, Optional, Awaitable
from common.src import messages_pb2

class OrchestratorCommsServer:
    """Handles ZMQ inbound commands and outbound status heartbeats for the Orchestrator."""
    def __init__(self, command_url: Optional[str] = None, status_url: Optional[str] = None):
        webapp_host = os.environ.get("WEBAPP_HOST", "127.0.0.1")
        self.command_url = command_url or f"tcp://{webapp_host}:5555"
        self.status_url = status_url or f"tcp://{webapp_host}:5556"
        self.zmq_ctx = zmq.asyncio.Context()
        self.is_processing = False
        
        self.pull_socket: Optional[zmq.asyncio.Socket] = None
        self.push_socket: Optional[zmq.asyncio.Socket] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        self.on_generate_tasks_cb: Optional[Callable[[str], Awaitable[None]]] = None

    def set_processing_state(self, is_processing: bool):
        self.is_processing = is_processing

    def register_command_handler(self, on_generate_tasks: Callable[[str], Awaitable[None]]):
        """Register the callback for when a GENERATE_TASKS command is received."""
        self.on_generate_tasks_cb = on_generate_tasks

    async def _heartbeat_loop(self):
        """Continuously push status updates."""
        try:
            while True:
                await asyncio.sleep(2)
                try:
                    status = messages_pb2.OrchestratorStatus()
                    status.is_alive = True
                    status.current_status = (
                        messages_pb2.OrchestratorStatus.PROCESSING if self.is_processing 
                        else messages_pb2.OrchestratorStatus.IDLE
                    )
                    
                    if self.push_socket:
                        await self.push_socket.send(status.SerializeToString())
                except Exception as e:
                    print(f"[!] Comms heartbeat error: {e}")
        except asyncio.CancelledError:
            pass

    async def _listen_loop(self):
        """Continuously pull incoming commands."""
        try:
            while True:
                if not self.pull_socket:
                    await asyncio.sleep(0.1)
                    continue
                    
                message = await self.pull_socket.recv()
                command = messages_pb2.OrchestratorCommand()
                command.ParseFromString(message)
                
                if command.type == messages_pb2.OrchestratorCommand.GENERATE_TASKS:
                    if self.on_generate_tasks_cb:
                        # Schedule the callback without blocking the loop
                        asyncio.create_task(self.on_generate_tasks_cb(command.vault_path))
                elif command.type == messages_pb2.OrchestratorCommand.PING:
                    pass # Just acknowledge
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[!] Error in comms listen loop: {e}")

    async def send_disconnect(self):
        """Sends a disconnect message as a status update to the webapp."""
        status = messages_pb2.OrchestratorStatus()
        status.is_alive = False
        status.current_status = messages_pb2.OrchestratorStatus.UNKNOWN
        if self.push_socket:
            try:
                await self.push_socket.send(status.SerializeToString())
            except Exception as e:
                print(f"[!] Error sending disconnect message: {e}")
    
    async def send_connected(self):
        """Sends a connected message as a status update to the webapp."""
        status = messages_pb2.OrchestratorStatus()
        status.is_alive = True
        status.current_status = messages_pb2.OrchestratorStatus.IDLE
        if self.push_socket:
            try:
                await self.push_socket.send(status.SerializeToString())
            except Exception as e:
                print(f"[!] Error sending connected message: {e}")

    async def start(self):
        """Starts the sockets and background loops."""
        self.push_socket = self.zmq_ctx.socket(zmq.PUSH)
        self.push_socket.connect(self.status_url)
        
        self.pull_socket = self.zmq_ctx.socket(zmq.PULL)
        self.pull_socket.connect(self.command_url)
        
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._listen_task = asyncio.create_task(self._listen_loop())

        ## Send connected message
        await self.send_connected()
        
    async def stop(self):
        """Stops the loops and closes sockets."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._listen_task:
            self._listen_task.cancel()

        ## Send disconnect message
        await self.send_disconnect()
            
        if self.push_socket:
            self.push_socket.setsockopt(zmq.LINGER, 1000)
            self.push_socket.close()
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
