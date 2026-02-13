import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ollamaWrapper import OllamaWrapper
import pytest 


def test_ollamaRunning():
    ollamaWrapper =OllamaWrapper()
    assert ollamaWrapper.isRunning() == True



