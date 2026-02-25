import os
import sys
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ollamaWrapper import OllamaWrapper

def test_ollamaRunning_initially_false_when_no_models():
    # If no models are present or ollama is down, this might be false.
    # It checks if the specific model is running/present.
    ollamaWrapper = OllamaWrapper(modelName='this_model_does_not_exist_at_all')
    # Because this model does not exist, it should return False
    assert ollamaWrapper.isRunning() == False

@pytest.mark.asyncio
async def test_initModel_pulls_the_model():
    # We use tinyllama to test pulling because it's small (~600MB)
    ollamaWrapper = OllamaWrapper(modelName='tinyllama')
    await ollamaWrapper.initModel()
    
    # After pulling, the model should be present in the list
    assert ollamaWrapper.isRunning() == True

def test_generateTasksFromNotes():
    ollamaWrapper = OllamaWrapper(modelName='tinyllama')
    # We assume tinyllama is now running due to the previous test
    if not ollamaWrapper.isRunning():
        pytest.skip("Model not running")
        
    notes = [
        "I need to call the plumber tomorrow about the sink.",
        "Buy milk, eggs, bread.",
        "A random thought about the universe being a simulation."
    ]
    tasks_string = ollamaWrapper.generateTasksFromNotes(notes)
    
    # Check that we got a non-empty string back
    assert isinstance(tasks_string, str)
    assert len(tasks_string) > 0
    # There should ideally be "plumber" or "milk" in the generated tasks
    assert "plumber" in tasks_string.lower() or "milk" in tasks_string.lower() or "bread" in tasks_string.lower() or "eggs" in tasks_string.lower()
