"""
Test MCP module initialization and imports.

Verifies that the MCP (Model Context Protocol) module structure is correctly
set up and can be imported without errors.
"""
import sys
from pathlib import Path


def test_mcp_module_import():
    """Test that MCP module can be imported."""
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        import src.mcp
        assert src.mcp is not None
        print("✅ MCP module imports successfully")
    except ImportError as e:
        assert False, f"Failed to import MCP module: {e}"


def test_mcp_as_submodule():
    """Test that MCP can be imported as a submodule of claude_coms."""
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        # Import through claude_coms
        import src.claude_coms.mcp
        assert src.claude_coms.mcp is not None
        print("✅ MCP imports successfully as claude_coms submodule")
        
        # Also test direct import
        import src.mcp
        assert src.mcp is not None
        print("✅ MCP imports successfully as direct module")
    except ImportError as e:
        assert False, f"Failed to import MCP: {e}"


def test_mcp_package_structure():
    """Verify the MCP package structure is correct."""
    project_root = Path(__file__).parent.parent.parent
    mcp_path = project_root / "src" / "mcp"
    
    # Check directory exists
    assert mcp_path.exists(), f"MCP directory not found at {mcp_path}"
    assert mcp_path.is_dir(), f"{mcp_path} is not a directory"
    
    # Check __init__.py exists
    init_file = mcp_path / "__init__.py"
    assert init_file.exists(), f"__init__.py not found in {mcp_path}"
    
    print("✅ MCP package structure verified successfully")


def test_mcp_module_attributes():
    """Test that the MCP module has proper attributes."""
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    import src.mcp
    
    # Check module has proper attributes
    assert hasattr(src.mcp, "__name__")
    assert src.mcp.__name__ == "src.mcp"
    
    # Check module path
    assert hasattr(src.mcp, "__file__")
    assert "mcp" in src.mcp.__file__
    
    print("✅ MCP module attributes are properly configured")


def test_mcp_ready_for_implementation():
    """Test that MCP module is ready for MCP server implementation."""
    project_root = Path(__file__).parent.parent.parent
    mcp_path = project_root / "src" / "mcp"
    
    # Directory should exist and be empty (except for __init__.py)
    assert mcp_path.exists()
    
    files = list(mcp_path.iterdir())
    init_files = [f for f in files if f.name == "__init__.py"]
    assert len(init_files) == 1, "MCP should have __init__.py"
    
    # Check if ready for MCP server implementation files
    expected_future_files = [
        "server.py",  # MCP server implementation
        "handlers.py",  # Request handlers
        "schemas.py",  # Schema definitions
        "utils.py"  # Utility functions
    ]
    
    for filename in expected_future_files:
        file_path = mcp_path / filename
        if file_path.exists():
            print(f"✅ Found {filename} - MCP implementation started")
        else:
            print(f"ℹ️  {filename} not yet created - ready for implementation")
    
    print("✅ MCP module is ready for server implementation")


if __name__ == "__main__":
    # Run all MCP module tests
    print("Running MCP module tests...")
    
    test_mcp_module_import()
    test_mcp_as_submodule()
    test_mcp_package_structure()
    test_mcp_module_attributes()
    test_mcp_ready_for_implementation()
    
    print("\n✅ All MCP module tests passed!")