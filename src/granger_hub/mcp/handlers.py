"""
MCP request and response handlers for Claude Desktop integration.

These handlers process incoming MCP protocol messages and format
responses according to the MCP specification.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from ..claude_module_communicator import ModuleCommunicator
from ..granger_hub.task_executor import Task

logger = logging.getLogger(__name__)


@dataclass
class MCPRequest:
    """Represents an MCP protocol request."""
    id: str
    method: str
    params: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class MCPResponse:
    """Represents an MCP protocol response."""
    id: str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {"id": self.id}
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        if self.metadata:
            data["metadata"] = self.metadata
        data["timestamp"] = self.timestamp
        return data


class MCPRequestHandler:
    """Handles incoming MCP protocol requests."""
    
    def __init__(self, communicator: ModuleCommunicator):
        """Initialize request handler.
        
        Args:
            communicator: Module communicator instance
        """
        self.communicator = communicator
        self.method_handlers = {
            "modules.list": self._handle_list_modules,
            "modules.register": self._handle_register_module,
            "modules.discover": self._handle_discover_modules,
            "messages.send": self._handle_send_message,
            "messages.broadcast": self._handle_broadcast_message,
            "tasks.execute": self._handle_execute_task,
            "tasks.status": self._handle_task_status,
            "graph.get": self._handle_get_graph,
            "compatibility.check": self._handle_check_compatibility,
            "tools.list": self._handle_list_tools,
            "tools.execute": self._handle_execute_tool
        }
    
    async def handle_request(self, request: Union[MCPRequest, Dict[str, Any]]) -> MCPResponse:
        """Handle an MCP request.
        
        Args:
            request: MCP request to handle
            
        Returns:
            MCP response
        """
        # Convert dict to MCPRequest if needed
        if isinstance(request, dict):
            request = MCPRequest(**request)
        
        logger.debug(f"Handling MCP request: {request.method}")
        
        # Get handler for method
        handler = self.method_handlers.get(request.method)
        
        if not handler:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            )
        
        try:
            # Execute handler
            result = await handler(request)
            return MCPResponse(
                id=request.id,
                result=result,
                metadata={"handler": request.method}
            )
        except Exception as e:
            logger.error(f"Error handling request {request.method}: {e}")
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32603,
                    "message": str(e),
                    "data": {"method": request.method}
                }
            )
    
    async def _handle_list_modules(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle modules.list request."""
        modules = await self.communicator.discover_modules()
        return {
            "modules": [
                {
                    "name": m.get("name"),
                    "info": m.get("info", {}),
                    "source": m.get("source", "registry")
                }
                for m in modules
            ]
        }
    
    async def _handle_register_module(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle modules.register request."""
        params = request.params
        
        # In a real implementation, this would dynamically load the module
        # For now, we'll create a basic module
        from ..granger_hub.base_module import BaseModule
        
        module = BaseModule(
            name=params["name"],
            system_prompt=params.get("system_prompt", ""),
            capabilities=params.get("capabilities", []),
            registry=self.communicator.registry
        )
        
        self.communicator.register_module(params["name"], module)
        
        return {
            "status": "registered",
            "module": params["name"]
        }
    
    async def _handle_discover_modules(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle modules.discover request."""
        pattern = request.params.get("pattern")
        modules = await self.communicator.discover_modules(pattern)
        
        return {
            "modules": modules,
            "count": len(modules)
        }
    
    async def _handle_send_message(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle messages.send request."""
        params = request.params
        
        result = await self.communicator.send_message(
            target=params["target"],
            action=params["action"],
            data=params.get("data", {}),
            timeout=params.get("timeout")
        )
        
        return {
            "status": "sent",
            "result": result
        }
    
    async def _handle_broadcast_message(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle messages.broadcast request."""
        params = request.params
        
        responses = await self.communicator.broadcast_message(
            action=params["action"],
            data=params.get("data", {}),
            pattern=params.get("pattern")
        )
        
        return {
            "status": "broadcast",
            "responses": responses,
            "count": len(responses)
        }
    
    async def _handle_execute_task(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tasks.execute request."""
        params = request.params
        
        result = await self.communicator.execute_task(
            instruction=params["instruction"],
            requester=params.get("requester", "mcp-client"),
            task_type=params.get("task_type"),
            parameters=params.get("parameters")
        )
        
        return {
            "status": "executed",
            "result": result
        }
    
    async def _handle_task_status(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tasks.status request."""
        task_id = request.params.get("task_id")
        
        # Get task status from progress tracker
        stats = await self.communicator.progress_tracker.get_stats()
        
        return {
            "task_id": task_id,
            "stats": stats
        }
    
    async def _handle_get_graph(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle graph.get request."""
        graph = self.communicator.get_module_graph()
        
        return {
            "graph": graph,
            "node_count": len(set(list(graph.keys()) + [n for nodes in graph.values() for n in nodes])),
            "edge_count": sum(len(targets) for targets in graph.values())
        }
    
    async def _handle_check_compatibility(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle compatibility.check request."""
        params = request.params
        
        result = await self.communicator.check_compatibility(
            source=params["source"],
            target=params["target"]
        )
        
        return result
    
    async def _handle_list_tools(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools.list request."""
        # This would integrate with the tool registry
        return {
            "tools": [
                {
                    "name": "send_message",
                    "description": "Send a message to a module"
                },
                {
                    "name": "execute_task",
                    "description": "Execute a task"
                },
                {
                    "name": "discover_modules",
                    "description": "Discover available modules"
                }
            ]
        }
    
    async def _handle_execute_tool(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools.execute request."""
        tool_name = request.params.get("tool")
        tool_params = request.params.get("parameters", {})
        
        # Route to appropriate handler based on tool
        if tool_name == "send_message":
            return await self._handle_send_message(
                MCPRequest(
                    id=request.id,
                    method="messages.send",
                    params=tool_params
                )
            )
        elif tool_name == "execute_task":
            return await self._handle_execute_task(
                MCPRequest(
                    id=request.id,
                    method="tasks.execute",
                    params=tool_params
                )
            )
        else:
            raise ValueError(f"Unknown tool: {tool_name}")


class MCPResponseHandler:
    """Handles formatting of MCP protocol responses."""
    
    def format_success_response(self, 
                               request_id: str,
                               result: Any,
                               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format a successful MCP response.
        
        Args:
            request_id: ID of the original request
            result: Result data
            metadata: Optional metadata
            
        Returns:
            Formatted response
        """
        response = MCPResponse(
            id=request_id,
            result=result,
            metadata=metadata
        )
        return response.to_dict()
    
    def format_error_response(self,
                             request_id: str,
                             code: int,
                             message: str,
                             data: Optional[Any] = None) -> Dict[str, Any]:
        """Format an error MCP response.
        
        Args:
            request_id: ID of the original request
            code: Error code
            message: Error message
            data: Optional error data
            
        Returns:
            Formatted error response
        """
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        
        response = MCPResponse(
            id=request_id,
            error=error
        )
        return response.to_dict()
    
    def format_notification(self,
                           method: str,
                           params: Dict[str, Any]) -> Dict[str, Any]:
        """Format an MCP notification (no response expected).
        
        Args:
            method: Notification method
            params: Notification parameters
            
        Returns:
            Formatted notification
        """
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }


# Export classes
__all__ = ['MCPRequest', 'MCPResponse', 'MCPRequestHandler', 'MCPResponseHandler']