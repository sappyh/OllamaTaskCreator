import pytest
import asyncio
from common.src import messages_pb2
from webapp.src.comms import WebappCommsClient
from orchestrator.src.comms import OrchestratorCommsServer

@pytest.mark.asyncio
async def test_comms_integration():
    """Test that WebappCommsClient and OrchestratorCommsServer can communicate."""
    # Use different ports for testing to avoid conflicts
    cmd_url = "tcp://127.0.0.1:5557"
    status_url = "tcp://127.0.0.1:5558"

    server = OrchestratorCommsServer(command_url=cmd_url, status_url=status_url)
    client = WebappCommsClient(command_url=cmd_url, status_url=status_url)

    # Tracker for received command
    received_vault_path = None
    
    async def mock_generate_tasks(vault_path: str):
        nonlocal received_vault_path
        received_vault_path = vault_path
        server.set_processing_state(True)

    server.register_command_handler(mock_generate_tasks)

    try:
        # Start server and client listener
        server.start()
        client.start_listening()
        
        # Give sockets a moment to bind
        await asyncio.sleep(0.5)
        
        # 1. Test status heartbeat initially (should be IDLE and connected)
        # Wait a moment for first heartbeat to arrive
        await asyncio.sleep(2.5)
        
        state = client.get_status()
        assert state["is_connected"] is True
        assert state["current_status"] == "Idle"
        
        # 2. Test command sending (Webapp -> Orchestrator)
        test_path = "/test/dummy/vault"
        client.send_generate_tasks(test_path)
        
        # Wait for command to be received and processed
        await asyncio.sleep(0.5)
        assert received_vault_path == test_path
        
        # 3. Test status update after command (should be PROCESSING)
        # Wait for next heartbeat
        await asyncio.sleep(2.0)
        state_processing = client.get_status()
        assert state_processing["current_status"] == "Processing"
        
    finally:
        server.stop()
        client.stop_listening()
        await asyncio.sleep(0.1) # allow cleanup
