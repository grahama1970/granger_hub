"""
Test claude_coms module initialization and imports.

Verifies that the claude_coms package structure is correctly set up
and can be imported without errors.
"""
import sys
from pathlib import Path


def test_claude_coms_module_import():
    """Test that claude_coms module can be imported."""
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        import src.claude_coms
        assert src.claude_coms is not None
        print("✅ claude_coms module imports successfully")
    except ImportError as e:
        assert False, f"Failed to import claude_coms: {e}"


def test_claude_coms_submodules():
    """Test that claude_coms submodules are accessible."""
    # Add project root to path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Test cli submodule
    try:
        import src.claude_coms.cli
        assert src.claude_coms.cli is not None
        print("✅ claude_coms.cli submodule imports successfully")
    except ImportError as e:
        assert False, f"Failed to import claude_coms.cli: {e}"
    
    # Test core submodule
    try:
        import src.claude_coms.core
        assert src.claude_coms.core is not None
        print("✅ claude_coms.core submodule imports successfully")
    except ImportError as e:
        assert False, f"Failed to import claude_coms.core: {e}"
    
    # Test mcp submodule
    try:
        import src.claude_coms.mcp
        assert src.claude_coms.mcp is not None
        print("✅ claude_coms.mcp submodule imports successfully")
    except ImportError as e:
        assert False, f"Failed to import claude_coms.mcp: {e}"


def test_package_structure():
    """Verify the claude_coms package structure is correct."""
    project_root = Path(__file__).parent.parent.parent
    claude_coms_path = project_root / "src" / "claude_coms"
    
    # Check directory exists
    assert claude_coms_path.exists(), f"claude_coms directory not found at {claude_coms_path}"
    assert claude_coms_path.is_dir(), f"{claude_coms_path} is not a directory"
    
    # Check __init__.py exists
    init_file = claude_coms_path / "__init__.py"
    assert init_file.exists(), f"__init__.py not found in {claude_coms_path}"
    
    # Check subdirectories
    subdirs = ["cli", "core", "mcp"]
    for subdir in subdirs:
        subdir_path = claude_coms_path / subdir
        assert subdir_path.exists(), f"Subdirectory {subdir} not found"
        assert subdir_path.is_dir(), f"{subdir_path} is not a directory"
        
        # Check subdirectory has __init__.py
        subdir_init = subdir_path / "__init__.py"
        assert subdir_init.exists(), f"__init__.py not found in {subdir_path}"
    
    print("✅ Package structure verified successfully")


def test_module_namespace():
    """Test that the module namespace is properly configured."""
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    import src.claude_coms
    
    # Check module has proper attributes
    assert hasattr(src.claude_coms, "__name__")
    assert src.claude_coms.__name__ == "src.claude_coms"
    
    # Check module path
    assert hasattr(src.claude_coms, "__file__")
    assert "claude_coms" in src.claude_coms.__file__
    
    print("✅ Module namespace is properly configured")


if __name__ == "__main__":
    # Run all module import tests
    print("Running claude_coms module tests...")
    
    test_claude_coms_module_import()
    test_claude_coms_submodules()
    test_package_structure()
    test_module_namespace()
    
    print("\n✅ All claude_coms module tests passed!")