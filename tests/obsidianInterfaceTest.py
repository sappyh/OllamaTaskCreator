import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.obsidianInterface import ObsidianInterface
import pytest 
from pathlib import Path

def helperSetup():
    vault_path = Path("/tmp/TestVault")
    vault_path.mkdir()
    file = (vault_path / "test_note.md")
    file.touch()
    with open(file, 'a') as f:
        f.write("# A Heading")
        f.close()

def helperTearDown():
    if (os.path.exists("/tmp/TestVault/test_note.md")):
        os.remove("/tmp/TestVault/test_note.md")
    if os.path.exists("/tmp/TestVault"):
        os.rmdir("/tmp/TestVault")
   

## A simple test that takes initializes the Obsidian tool with a path and prints the files found
def test_listAllFiles():
    helperSetup()
    vault_path = Path("/tmp/TestVault")
    tool = ObsidianInterface(str(vault_path))
    files = tool.listAllFiles()

    ## Clean Up
    helperTearDown()

    assert "test_note.md" in files


## A test to keep we are able to read the content of a file stored in the Vault
def test_retrieveContentFromFile():
    helperSetup()
    vault_path = Path("/tmp/TestVault")
    tool = ObsidianInterface(str(vault_path))
    content = tool.retrieveContentFromFile("test_note1.md")
    assert content is NameError

    content = tool.retrieveContentFromFile("test_note.md")

    ## Clean Up
    helperTearDown()

    assert content is not None


if __name__ == "__main__":
    pytest.main()