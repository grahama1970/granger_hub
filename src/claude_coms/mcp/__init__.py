"""
MCP (Model Context Protocol) Integration with Enhanced Prompt Support.

This module provides MCP integration through multiple approaches:
1. CLI slash commands via granger_slash_mcp_mixin (primary)
2. FastMCP server for advanced use cases
3. Prompt infrastructure for intelligent interactions

The integration now includes:
- Dynamic prompt management
- Hub-specific prompts for module orchestration
- Enhanced MCP server with prompt support
- Backwards compatibility with original architecture

Key Components:
- prompts.py: Core prompt infrastructure
- hub_prompts.py: Hub-specific prompt definitions
- server.py: Enhanced MCP server (when needed)
- ../cli/granger_slash_mcp_mixin.py: Primary integration point
"""

# Import prompt infrastructure
from .prompts import (
    Prompt,
    PromptRegistry,
    get_prompt_registry,
    set_prompt_registry
)

# Import hub-specific prompts (auto-registers on import)
from . import hub_prompts

# Export public API
__all__ = [
    'Prompt',
    'PromptRegistry', 
    'get_prompt_registry',
    'set_prompt_registry',
    'hub_prompts'
]