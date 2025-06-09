"""
MCP Server implementation for Claude Desktop integration.
Module: server.py

This server provides the bridge between the module communication framework
and Claude Desktop's MCP protocol, enabling seamless integration.'
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from pathlib import Path
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from ..core.module_communicator import ModuleCommunicator
from ..core.modules.base_module import BaseModule
from .handlers import MCPRequestHandler, MCPResponseHandler
from .tools import MCPToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class MCPConfig:
    """Configuration for MCP server."""
    host: str = "localhost"
    port: int = 8080
    module_registry_path: Optional[Path] = None
    progress_db_path: Optional[Path] = None
    allowed_origins: List[str] = None
    enable_cors: bool = True
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["http://localhost:*", "https://claude.ai"]


class MCPServer:
    """
    MCP Server that integrates with Claude Desktop.
    
    This server exposes the module communication framework through
    the MCP protocol, allowing Claude Desktop to interact with modules.
    """
    
    def __init__(self, config: MCPConfig):
        """Initialize MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.app = FastAPI(title="Granger Hub MCP Server")
        self.communicator = ModuleCommunicator(
            registry_path=config.module_registry_path,
            progress_db=config.progress_db_path
        )
        self.tool_registry = MCPToolRegistry()
        self.request_handler = MCPRequestHandler(self.communicator)
        self.response_handler = MCPResponseHandler()
        self._setup_routes()
        self._connected_clients: Dict[str, WebSocket] = {}
    
    def _setup_routes(self):
        """Set up FastAPI routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "service": "mcp-server"}
        
        @self.app.get("/modules")
        async def list_modules():
            """List all registered modules."""
            modules = await self.communicator.discover_modules()
            return {"modules": modules}
        
        @self.app.post("/modules/register")
        async def register_module(module_data: Dict[str, Any]):
            """Register a new module."""
            try:
                # Dynamic module creation from data
                module_class = module_data.get("class", "BaseModule")
                module_name = module_data["name"]
                
                # Create module instance
                # In real implementation, this would dynamically load the module
                module = BaseModule(
                    name=module_name,
                    system_prompt=module_data.get("system_prompt", ""),
                    capabilities=module_data.get("capabilities", []),
                    registry=self.communicator.registry
                )
                
                self.communicator.register_module(module_name, module)
                return {"status": "success", "module": module_name}
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": str(e)}
                )
        
        @self.app.post("/messages/send")
        async def send_message(message_data: Dict[str, Any]):
            """Send a message to a module."""
            try:
                result = await self.communicator.send_message(
                    target=message_data["target"],
                    action=message_data["action"],
                    data=message_data.get("data", {}),
                    timeout=message_data.get("timeout")
                )
                return {"status": "success", "result": result}
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": str(e)}
                )
        
        @self.app.post("/tasks/execute")
        async def execute_task(task_data: Dict[str, Any]):
            """Execute a task."""
            try:
                result = await self.communicator.execute_task(
                    instruction=task_data["instruction"],
                    requester=task_data.get("requester", "mcp-client"),
                    task_type=task_data.get("task_type"),
                    parameters=task_data.get("parameters")
                )
                return {"status": "success", "result": result}
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": str(e)}
                )
        
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            """WebSocket endpoint for real-time communication."""
            await websocket.accept()
            self._connected_clients[client_id] = websocket
            
            try:
                while True:
                    # Receive message
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle different message types
                    response = await self._handle_websocket_message(
                        client_id, message
                    )
                    
                    # Send response
                    await websocket.send_text(json.dumps(response))
            except WebSocketDisconnect:
                del self._connected_clients[client_id]
                logger.info(f"Client {client_id} disconnected")
        
        @self.app.get("/events")
        async def event_stream():
            """Server-sent events for module updates."""
            async def event_generator():
                """Generate events for SSE."""
                # Subscribe to module events
                event_queue = asyncio.Queue()
                
                def event_callback(event_type: str, data: Any):
                    asyncio.create_task(event_queue.put({
                        "type": event_type,
                        "data": data
                    }))
                
                # Subscribe to registry events
                self.communicator.registry.subscribe("module_registered", event_callback)
                self.communicator.registry.subscribe("module_updated", event_callback)
                
                try:
                    while True:
                        event = await event_queue.get()
                        yield {
                            "event": event["type"],
                            "data": json.dumps(event["data"])
                        }
                except asyncio.CancelledError:
                    pass
            
            return EventSourceResponse(event_generator())
        
        @self.app.get("/tools")
        async def list_tools():
            """List available tools."""
            tools = self.tool_registry.list_tools()
            return {"tools": tools}
        
        @self.app.post("/tools/register")
        async def register_tool(tool_data: Dict[str, Any]):
            """Register a new tool."""
            try:
                self.tool_registry.register_tool(
                    name=tool_data["name"],
                    description=tool_data["description"],
                    parameters=tool_data.get("parameters", {}),
                    handler=tool_data.get("handler")  # Would be resolved dynamically
                )
                return {"status": "success", "tool": tool_data["name"]}
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={"error": str(e)}
                )
    
    async def _handle_websocket_message(self, 
                                      client_id: str, 
                                      message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming WebSocket message.
        
        Args:
            client_id: ID of the connected client
            message: Incoming message
            
        Returns:
            Response message
        """
        message_type = message.get("type", "unknown")
        
        if message_type == "ping":
            return {"type": "pong", "client_id": client_id}
        
        elif message_type == "module_message":
            # Forward to module
            result = await self.communicator.send_message(
                target=message["target"],
                action=message["action"],
                data=message.get("data", {})
            )
            return {
                "type": "module_response",
                "result": result,
                "request_id": message.get("request_id")
            }
        
        elif message_type == "execute_task":
            # Execute task
            result = await self.communicator.execute_task(
                instruction=message["instruction"],
                requester=f"ws-client-{client_id}",
                task_type=message.get("task_type"),
                parameters=message.get("parameters")
            )
            return {
                "type": "task_result",
                "result": result,
                "request_id": message.get("request_id")
            }
        
        elif message_type == "subscribe":
            # Subscribe to module events
            # Implementation would add client to subscription list
            return {
                "type": "subscribed",
                "topics": message.get("topics", [])
            }
        
        else:
            return {
                "type": "error",
                "error": f"Unknown message type: {message_type}"
            }
    
    async def broadcast_to_clients(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients.
        
        Args:
            message: Message to broadcast
        """
        disconnected = []
        
        for client_id, websocket in self._connected_clients.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            del self._connected_clients[client_id]
    
    def run(self):
        """Run the MCP server."""
        logger.info(f"Starting MCP server on {self.config.host}:{self.config.port}")
        
        # Configure CORS if enabled
        if self.config.enable_cors:
            from fastapi.middleware.cors import CORSMiddleware
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.allowed_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Run server
        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port
        )
    
    async def shutdown(self):
        """Shutdown the server gracefully."""
        # Close all WebSocket connections
        for client_id, websocket in self._connected_clients.items():
            await websocket.close()
        
        # Shutdown communicator
        await self.communicator.shutdown()


# Export classes
__all__ = ['MCPServer', 'MCPConfig']