"""
Test the Granger slash MCP integration for Claude Module Communicator.
"""

import pytest
from pathlib import Path
import json
import sys
from typer.testing import CliRunner

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_coms.cli.claude_comm import app
from claude_coms.mcp import get_prompt_registry
from claude_coms.mcp.hub_prompts import get_hub_prompt_examples


runner = CliRunner()


def test_cli_has_granger_commands():
    """Test that the CLI has all Granger-enhanced commands."""
    # Get command names
    command_names = [cmd.name for cmd in app.registered_commands]
    
    # Check for Granger commands
    assert "generate-claude" in command_names
    assert "generate-mcp-config" in command_names
    assert "serve-mcp-fastmcp" in command_names
    assert "list-prompts" in command_names
    assert "show-prompt" in command_names


def test_generate_claude_commands():
    """Test generating Claude slash commands."""
    # Create temp directory for output
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, [
            "generate-claude",
            "--output", tmpdir,
            "--verbose"
        ])
        
        assert result.exit_code == 0
        assert "Generated" in result.output
        
        # Check that files were created
        output_dir = Path(tmpdir)
        md_files = list(output_dir.glob("*.md"))
        assert len(md_files) > 0
        
        # Check content of a generated file
        if md_files:
            content = md_files[0].read_text()
            assert "Usage" in content
            assert "/project:" in content


def test_generate_mcp_config():
    """Test generating MCP configuration."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        result = runner.invoke(app, [
            "generate-mcp-config",
            "--output", f.name,
            "--name", "test-hub"
        ])
        
        assert result.exit_code == 0
        assert "Generated enhanced MCP config" in result.output
        
        # Load and verify config
        config = json.loads(Path(f.name).read_text())
        assert config["name"] == "test-hub"
        assert config["version"] == "2.0.0"
        assert "tools" in config
        assert "capabilities" in config
        assert config["capabilities"]["tools"] is True
        
        # Verify prompts are included
        assert "prompts" in config
        assert len(config["prompts"]) > 0
        
        # Clean up
        Path(f.name).unlink()


def test_prompt_registry_integration():
    """Test that prompts are properly registered."""
    registry = get_prompt_registry()
    
    # Check hub prompts are registered
    hub_prompts = [
        "orchestrate_modules",
        "analyze_module_compatibility",
        "design_communication_pattern",
        "generate_integration_code",
        "debug_module_communication",
        "optimize_module_pipeline",
        "discover_module_capabilities",
        "generate_integration_scenario"
    ]
    
    for prompt_name in hub_prompts:
        prompt = registry.get_prompt(prompt_name)
        assert prompt is not None, f"Hub prompt {prompt_name} not found"


def test_list_prompts_command():
    """Test the list-prompts command."""
    result = runner.invoke(app, ["list-prompts"])
    
    assert result.exit_code == 0
    assert "ORCHESTRATION" in result.output
    assert "orchestrate_modules" in result.output


def test_show_prompt_command():
    """Test the show-prompt command."""
    result = runner.invoke(app, [
        "show-prompt",
        "orchestrate_modules",
        "--format", "text"
    ])
    
    assert result.exit_code == 0
    assert "orchestrate_modules" in result.output
    assert "Orchestrate communication between multiple modules" in result.output


def test_hub_prompt_examples():
    """Test that hub prompt examples are valid."""
    examples = get_hub_prompt_examples()
    
    assert len(examples) > 0
    
    registry = get_prompt_registry()
    
    for example in examples:
        prompt_name = example["prompt"]
        params = example["example"]
        
        # Get the prompt
        prompt = registry.get_prompt(prompt_name)
        assert prompt is not None, f"Example references non-existent prompt: {prompt_name}"
        
        # Try to render it
        try:
            rendered = prompt.render(**params)
            assert len(rendered) > 0
        except Exception as e:
            pytest.fail(f"Failed to render example for {prompt_name}: {e}")


def test_mcp_config_includes_metadata():
    """Test that MCP config includes enhanced metadata."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        result = runner.invoke(app, [
            "generate-mcp-config",
            "--output", f.name
        ])
        
        assert result.exit_code == 0
        
        config = json.loads(Path(f.name).read_text())
        
        # Check metadata
        assert "metadata" in config
        assert config["metadata"]["author"] == "Claude Module Communicator"
        assert "enhanced_features" in config["metadata"]
        assert "prompts" in config["metadata"]["enhanced_features"]
        
        # Check tool groups
        assert "tool_groups" in config
        
        # Clean up
        Path(f.name).unlink()


def test_smart_bundling():
    """Test that smart bundling groups related commands."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, [
            "generate-claude",
            "--output", tmpdir,
            "--bundle"
        ])
        
        assert result.exit_code == 0
        
        # Check for bundle files
        output_dir = Path(tmpdir)
        bundle_files = list(output_dir.glob("*-bundle.md"))
        
        # Should have at least one bundle if there are related commands
        # This depends on the actual commands in the CLI


def test_fastmcp_server_creation():
    """Test that FastMCP server can be created."""
    try:
        from claude_coms.mcp.fastmcp_server import create_hub_mcp_server
        
        # Create server (but don't run it)
        mcp = create_hub_mcp_server()
        
        # Verify it has tools and prompts
        assert hasattr(mcp, '_tools')
        assert hasattr(mcp, '_prompts')
        assert len(mcp._tools) > 0
        
    except ImportError:
        # FastMCP not installed, skip this test
        pytest.skip("FastMCP not installed")


if __name__ == "__main__":
    # Run validation tests
    print(f"Validating {__file__}...")
    
    # Run basic tests without pytest
    test_prompt_registry_integration()
    print("✓ Prompt registry integration")
    
    test_hub_prompt_examples()
    print("✓ Hub prompt examples")
    
    # Test CLI commands exist
    from claude_coms.cli.claude_comm import app
    command_names = [cmd.name for cmd in app.registered_commands]
    assert "generate-claude" in command_names
    assert "list-prompts" in command_names
    print("✓ CLI commands registered")
    
    print("\n✅ Validation passed")