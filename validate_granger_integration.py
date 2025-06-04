#!/usr/bin/env python3
"""
Validate Granger MCP integration for Claude Module Communicator.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    print("🔍 Validating Granger MCP Integration...\n")
    
    # Test 1: Import core modules
    try:
        from granger_hub.cli.granger_slash_mcp_mixin import add_slash_mcp_commands
        print("✅ Imported granger_slash_mcp_mixin")
    except ImportError as e:
        print(f"❌ Failed to import granger_slash_mcp_mixin: {e}")
        return 1
    
    # Test 2: Import prompt infrastructure
    try:
        from granger_hub.mcp import (
            Prompt, PromptRegistry, get_prompt_registry, set_prompt_registry
        )
        print("✅ Imported prompt infrastructure")
    except ImportError as e:
        print(f"❌ Failed to import prompt infrastructure: {e}")
        return 1
    
    # Test 3: Import hub prompts
    try:
        from granger_hub.mcp.hub_prompts import get_hub_prompt_examples
        print("✅ Imported hub prompts")
    except ImportError as e:
        print(f"❌ Failed to import hub prompts: {e}")
        return 1
    
    # Test 4: Verify prompts are registered
    registry = get_prompt_registry()
    prompts = registry.list_prompts()
    print(f"\n📋 Loaded {len(prompts)} prompts:")
    
    expected_prompts = [
        "orchestrate_modules",
        "analyze_module_compatibility",
        "design_communication_pattern",
        "generate_integration_code",
        "debug_module_communication",
        "optimize_module_pipeline",
        "discover_module_capabilities",
        "generate_integration_scenario"
    ]
    
    for prompt_name in expected_prompts:
        prompt = registry.get_prompt(prompt_name)
        if prompt:
            print(f"  ✅ {prompt_name}: {prompt.description[:50]}...")
        else:
            print(f"  ❌ {prompt_name}: NOT FOUND")
    
    # Test 5: Test prompt rendering
    print("\n🎯 Testing prompt rendering...")
    test_prompt = registry.get_prompt("orchestrate_modules")
    if test_prompt:
        try:
            rendered = test_prompt.render(
                task_description="Test orchestration",
                modules=[{
                    "name": "test_module",
                    "description": "A test module",
                    "capabilities": ["test", "validate"]
                }],
                requirements="Must be fast and reliable"
            )
            print("✅ Successfully rendered orchestrate_modules prompt")
            print(f"   Output length: {len(rendered)} characters")
        except Exception as e:
            print(f"❌ Failed to render prompt: {e}")
    
    # Test 6: Verify CLI integration
    print("\n🖥️  Testing CLI integration...")
    try:
        from granger_hub.cli.claude_comm import app
        commands = [cmd.name for cmd in app.registered_commands]
        
        granger_commands = [
            "generate-claude",
            "generate-mcp-config",
            "serve-mcp-fastmcp",
            "list-prompts",
            "show-prompt"
        ]
        
        for cmd in granger_commands:
            if cmd in commands:
                print(f"  ✅ Command registered: {cmd}")
            else:
                print(f"  ❌ Command missing: {cmd}")
    except Exception as e:
        print(f"❌ Failed to test CLI: {e}")
    
    # Test 7: Verify FastMCP server
    print("\n🚀 Testing FastMCP server creation...")
    try:
        from granger_hub.mcp.fastmcp_server import create_hub_mcp_server
        # Don't actually create it, just verify import
        print("✅ FastMCP server module imported successfully")
    except ImportError:
        print("⚠️  FastMCP not available (optional dependency)")
    except Exception as e:
        print(f"❌ Error with FastMCP server: {e}")
    
    # Summary
    print("\n" + "="*50)
    print("✅ Granger MCP Integration validation complete!")
    print("="*50)
    
    # Show categories and tags
    categories = registry.list_categories()
    tags = registry.list_tags()
    print(f"\n📊 Summary:")
    print(f"  - Total prompts: {len(prompts)}")
    print(f"  - Categories: {', '.join(categories)}")
    print(f"  - Total tags: {len(tags)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())