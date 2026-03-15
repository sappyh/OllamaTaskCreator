import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
import pytest_asyncio
import asyncio
import zmq
from pathlib import Path
from common.src import messages_pb2
from orchestrator.src.comms import OrchestratorCommsServer

@pytest.fixture
def comms_interface():
    ## Setup Orchestrator server with specific test ports
    server = OrchestratorCommsServer(command_url="tcp://127.0.0.1:5561", status_url="tcp://127.0.0.1:5562")
    return server


@pytest_asyncio.fixture
async def webapp_stub():
    ## Create a zmq_push and zmq_pull socket pair
    ctx = zmq.asyncio.Context()
    command_socket = ctx.socket(zmq.PUSH)
    status_socket = ctx.socket(zmq.PULL)
    command_socket.bind("tcp://127.0.0.1:5561")
    status_socket.bind("tcp://127.0.0.1:5562")
    
    yield ctx, command_socket, status_socket
    
    command_socket.close()
    status_socket.close()
    ctx.term()


@pytest.mark.asyncio
async def test_start_stop(comms_interface, webapp_stub):
    ctx, command_socket, status_socket = webapp_stub
    await comms_interface.start()
    
    ## Give ZMQ a tiny bit of time to connect and flush the starting message
    await asyncio.sleep(0.2)

    ## Receive the connected message
    message = await asyncio.wait_for(status_socket.recv(), timeout=2)
    status = messages_pb2.OrchestratorStatus()
    status.ParseFromString(message)
    assert status.is_alive == True
    assert status.current_status == messages_pb2.OrchestratorStatus.IDLE

    await comms_interface.stop()
    await asyncio.sleep(0.2)
    
    ## Receive the disconnect message
    message = await asyncio.wait_for(status_socket.recv(), timeout=2)
    status = messages_pb2.OrchestratorStatus()
    status.ParseFromString(message)
    assert status.is_alive == False
    assert status.current_status == messages_pb2.OrchestratorStatus.UNKNOWN


@pytest.mark.asyncio
async def test_command_handling(comms_interface, webapp_stub):
    ctx, command_socket, status_socket = webapp_stub
    
    received_path = None
    async def mock_callback(vault_path: str):
        nonlocal received_path
        received_path = vault_path
        
    comms_interface.register_command_handler(mock_callback)
    await comms_interface.start()
    
    ## Send command from stub
    cmd = messages_pb2.OrchestratorCommand()
    cmd.type = messages_pb2.OrchestratorCommand.GENERATE_TASKS
    cmd.vault_path = "/test/vault"
    await command_socket.send(cmd.SerializeToString())
    
    ## Wait for callback
    await asyncio.sleep(0.5)
    assert received_path == "/test/vault"
    
    await comms_interface.stop()


@pytest.mark.asyncio
async def test_heartbeat_pulse(comms_interface, webapp_stub):
    ctx, command_socket, status_socket = webapp_stub
    await comms_interface.start()
    
    # 1. Check IDLE heartbeat (immediately after connected message)
    # Drain the "Connected" message first
    await status_socket.recv()
    
    # Wait for the first heartbeat loop pulse (every 2s)
    # To speed up test we could mock sleep, but 2s is okay for now or we wait for next recv
    message = await asyncio.wait_for(status_socket.recv(), timeout=3)
    status = messages_pb2.OrchestratorStatus()
    status.ParseFromString(message)
    assert status.current_status == messages_pb2.OrchestratorStatus.IDLE
    
    # 2. Transition to PROCESSING
    comms_interface.set_processing_state(True)
    
    # Wait for next pulse
    message = await asyncio.wait_for(status_socket.recv(), timeout=3)
    status = messages_pb2.OrchestratorStatus()
    status.ParseFromString(message)
    assert status.current_status == messages_pb2.OrchestratorStatus.PROCESSING
    
    await comms_interface.stop()
