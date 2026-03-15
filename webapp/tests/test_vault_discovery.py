import pytest
import os
import shutil
from pathlib import Path
from webapp.src.main import LocalVaultManager

@pytest.fixture
def temp_base(tmp_path):
    base_dir = tmp_path / "OllamaCreator"
    base_dir.mkdir()
    return str(base_dir)

def test_automatic_vault_discovery(temp_base):
    # 1. Create some subdirectories (vaults)
    v1 = Path(temp_base) / "Project Alpha"
    v2 = Path(temp_base) / "Daily Notes"
    v1.mkdir()
    v2.mkdir()
    # Create a hidden one (should be ignored)
    (Path(temp_base) / ".hidden").mkdir()
    
    # 2. Initialize manager
    mgr = LocalVaultManager(base_dir=temp_base)
    
    # 3. List vaults
    vaults = mgr.list_vaults()
    
    # Needs to include the base_dir itself + v1 + v2
    assert len(vaults) == 3
    assert str(v1) in vaults
    assert str(v2) in vaults
    assert temp_base in vaults
    assert str(Path(temp_base) / ".hidden") not in vaults

def test_delete_vault_physical(temp_base):
    mgr = LocalVaultManager(base_dir=temp_base)
    v1 = Path(temp_base) / "DeleteMe"
    mgr.create_vault(str(v1))
    
    assert v1.exists()
    assert str(v1) in mgr.list_vaults()
    
    # Delete
    mgr.delete_vault(str(v1))
    
    assert not v1.exists()
    assert str(v1) not in mgr.list_vaults()

def test_delete_base_dir_fails(temp_base):
    mgr = LocalVaultManager(base_dir=temp_base)
    with pytest.raises(ValueError, match="Cannot delete the base directory"):
        mgr.delete_vault(temp_base)
