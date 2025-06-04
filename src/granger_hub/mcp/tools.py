"""
MCP Tool Registry for Claude Desktop integration.

This module manages tools that can be exposed through the MCP protocol
to Claude Desktop, enabling Claude to use various tools for module communication.
"""

import logging
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
import json
import inspect

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Represents a tool available through MCP."""
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Optional[Callable] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)
    category: str = "general"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP protocol."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples,
            "category": self.category
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters against schema.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if valid, False otherwise
        """
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})
        
        # Check required parameters
        for req in required:
            if req not in params:
                logger.error(f"Missing required parameter: {req}")
                return False
        
        # Validate parameter types
        for key, value in params.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type:
                    if not self._check_type(value, expected_type):
                        logger.error(f"Invalid type for {key}: expected {expected_type}")
                        return False
        
        return True
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type.
        
        Args:
            value: Value to check
            expected_type: Expected type name
            
        Returns:
            True if type matches
        """
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)
        return True


class MCPToolRegistry:
    """Registry for MCP tools."""
    
    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, MCPTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools for module communication."""
        
        # Send message tool
        self.register_tool(
            name="send_message",
            description="Send a message to a specific module",
            parameters={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Target module name"
                    },
                    "action": {
                        "type": "string",
                        "description": "Action to perform"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data to send"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds (optional)"
                    }
                },
                "required": ["target", "action"]
            },
            examples=[
                {
                    "target": "data_processor",
                    "action": "process",
                    "data": {"items": [1, 2, 3]}
                }
            ]
        )
        
        # Execute task tool
        self.register_tool(
            name="execute_task",
            description="Execute a natural language task instruction",
            parameters={
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "Natural language instruction"
                    },
                    "task_type": {
                        "type": "string",
                        "description": "Type of task (execute, research, screenshot, etc.)"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Additional parameters for the task"
                    }
                },
                "required": ["instruction"]
            },
            examples=[
                {
                    "instruction": "Generate 5 data points and analyze them",
                    "task_type": "execute"
                }
            ]
        )
        
        # Discover modules tool
        self.register_tool(
            name="discover_modules",
            description="Discover available modules by pattern or capability",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to match module names"
                    },
                    "capability": {
                        "type": "string",
                        "description": "Required capability"
                    }
                },
                "required": []
            },
            examples=[
                {"pattern": "data"},
                {"capability": "processing"}
            ]
        )
        
        # Check compatibility tool
        self.register_tool(
            name="check_compatibility",
            description="Check if two modules are compatible for communication",
            parameters={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source module name"
                    },
                    "target": {
                        "type": "string",
                        "description": "Target module name"
                    }
                },
                "required": ["source", "target"]
            }
        )
        
        # Get module graph tool
        self.register_tool(
            name="get_module_graph",
            description="Get the module dependency and communication graph",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        
        # Broadcast message tool
        self.register_tool(
            name="broadcast_message",
            description="Broadcast a message to multiple modules",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Action to broadcast"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data to broadcast"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to filter target modules"
                    }
                },
                "required": ["action"]
            }
        )
    
    def register_tool(self,
                     name: str,
                     description: str,
                     parameters: Dict[str, Any],
                     handler: Optional[Callable] = None,
                     examples: Optional[List[Dict[str, Any]]] = None,
                     category: str = "general") -> None:
        """Register a new tool.
        
        Args:
            name: Tool name (must be unique)
            description: Tool description
            parameters: JSON Schema for parameters
            handler: Optional handler function
            examples: Optional list of usage examples
            category: Tool category
        """
        if name in self._tools:
            logger.warning(f"Tool {name} already registered, overwriting")
        
        tool = MCPTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            examples=examples or [],
            category=category
        )
        
        self._tools[name] = tool
        logger.info(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool if found, None otherwise
        """
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all registered tools.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool descriptions
        """
        tools = []
        for tool in self._tools.values():
            if category and tool.category != category:
                continue
            tools.append(tool.to_dict())
        
        return sorted(tools, key=lambda t: t["name"])
    
    def execute_tool(self, 
                    name: str, 
                    params: Dict[str, Any],
                    context: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a tool with given parameters.
        
        Args:
            name: Tool name
            params: Tool parameters
            context: Optional execution context
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool not found or parameters invalid
        """
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        
        # Validate parameters
        if not tool.validate_parameters(params):
            raise ValueError(f"Invalid parameters for tool {name}")
        
        # Execute handler if available
        if tool.handler:
            # Inject context if handler accepts it
            sig = inspect.signature(tool.handler)
            if "context" in sig.parameters:
                return tool.handler(**params, context=context)
            else:
                return tool.handler(**params)
        else:
            # Return parameters for external handling
            return {
                "tool": name,
                "params": params,
                "status": "ready"
            }
    
    def register_handler(self, tool_name: str, handler: Callable) -> None:
        """Register a handler for a tool.
        
        Args:
            tool_name: Name of the tool
            handler: Handler function
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")
        
        tool.handler = handler
        logger.info(f"Registered handler for tool: {tool_name}")
    
    def get_tool_schema(self) -> Dict[str, Any]:
        """Get OpenAPI-style schema for all tools.
        
        Returns:
            Schema describing all available tools
        """
        return {
            "tools": {
                tool.name: {
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "examples": tool.examples,
                    "category": tool.category
                }
                for tool in self._tools.values()
            }
        }


# Export classes
__all__ = ['MCPTool', 'MCPToolRegistry']