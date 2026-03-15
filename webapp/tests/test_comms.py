import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import pytest_asyncio
import asyncio
import zmq
import zmq.asyncio
from common.src import messages_pb2
from webapp.src.comms import WebappCommsClient

@pytest.fixture
def comms_client():
    return WebappCommsClient(command_url="tcp://127.0.0.1:5563", status_url="tcp://127.0.0.1:5564")

@pytest_asyncio.fixture
async def orchestrator_stub():
    ctx = zmq.asyncio.Context()
    cmd_pull = ctx.socket(zmq.PULL)
    status_push = ctx.socket(zmq.PUSH)
    
    # In the webapp:
    # command_socket is PUSH and connects (Wait, WebappCommsClient binds command_socket? 
    # Let me check webapp/src/comms.py again)
    
    # Re-checking webapp/src/comms.py:
    # send_generate_tasks binds command_url.
    # start_listening binds status_url.
    
    # So the stub should connect to these.
    cmd_pull.connect("tcp://127.0.0.1:5563")
    status_push.connect("tcp://127.0.0.1:5564")
    
    yield ctx, cmd_pull, status_push
    
    cmd_pull.close()
    status_push.close()
    ctx.term()

@pytest.mark.asyncio
async def test_command_dispatch(comms_client, orchestrator_stub):
    ctx, cmd_pull, status_push = orchestrator_stub
    
    # We don't need to start_listening for this part
    test_path = "/path/to/vault"
    await comms_client.send_generate_tasks(test_path)
    
    # Receive on stub
    message = await asyncio.wait_for(cmd_pull.recv(), timeout=2)
    command = messages_pb2.OrchestratorCommand()
    command.ParseFromString(message)
    
    assert command.type == messages_pb2.OrchestratorCommand.GENERATE_TASKS
    assert command.vault_path == test_path

@pytest.mark.asyncio
async def test_status_updates(comms_client, orchestrator_stub):
    ctx, cmd_pull, status_push = orchestrator_stub
    
    await comms_client.start_listening()
    
    # 1. Send IDLE status from stub
    status = messages_pb2.OrchestratorStatus()
    status.is_alive = True
    status.current_status = messages_pb2.OrchestratorStatus.IDLE
    await status_push.send(status.SerializeToString())
    
    # Wait for state to update
    await asyncio.sleep(0.2)
    state = comms_client.get_status()
    assert state["is_connected"] is True
    assert state["current_status"] == "Idle"
    
    # 2. Send PROCESSING status
    status.current_status = messages_pb2.OrchestratorStatus.PROCESSING
    await status_push.send(status.SerializeToString())
    
    await asyncio.sleep(0.2)
    state = comms_client.get_status()
    assert state["current_status"] == "Processing"
    
    await comms_client.stop_listening()

@pytest.mark.asyncio
async def test_timeout_behavior(comms_client, orchestrator_stub):
    # We don't need the stub for this, just start listening and wait
    # But wait, wait_for timeout is 5.0s in comms.py. 
    # We can't easily shorten it without modifying code or mocking.
    # I'll modify the code to take a timeout param or just wait for the 5s.
    
    # Let's check webapp/src/comms.py line 32
    # message = await asyncio.wait_for(self.pull_socket.recv(), timeout=5.0)
    
    await comms_client.start_listening()
    
    # Initially connected=False
    assert comms_client.get_status()["is_connected"] is False
    
    # Send a message to make it connected
    ctx, cmd_pull, status_push = orchestrator_stub
    status = messages_pb2.OrchestratorStatus()
    status.is_alive = True
    status.current_status = messages_pb2.OrchestratorStatus.IDLE
    await status_push.send(status.SerializeToString())
    
    await asyncio.sleep(0.2)
    assert comms_client.get_status()["is_connected"] is True
    
    # Now wait for 5.5s to see if it disconnects
    await asyncio.sleep(5.5)
    assert comms_client.get_status()["is_connected"] is False
    assert comms_client.get_status()["current_status"] == "Disconnected"
    
    await comms_client.stop_listening()
