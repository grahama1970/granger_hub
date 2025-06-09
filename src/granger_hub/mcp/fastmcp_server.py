"""
Enhanced MCP server using FastMCP for Granger Hub.
Module: fastmcp_server.py
Description: Functions for fastmcp server operations

This server provides a FastMCP-based implementation with:
- Full prompt support
- Module orchestration tools
- Analytics and monitoring
- Hot-reload capability
"""

from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime
from pathlib import Path
import json

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = None

from ..core.module_communicator import ModuleCommunicator
from ..core.modules import module_registry
from .prompts import get_prompt_registry
from .hub_prompts import get_hub_prompt_examples


def create_hub_mcp_server(
    name: str = "granger_hub",
    communicator: Optional[ModuleCommunicator] = None,
    enable_analytics: bool = True
) -> 'FastMCP':
    """Create an enhanced MCP server for the module hub.
    
    Args:
        name: Server name
        communicator: Optional ModuleCommunicator instance
        enable_analytics: Enable usage analytics
        
    Returns:
        Configured FastMCP instance
    """
    if FastMCP is None:
        raise ImportError("FastMCP not installed. Install with: uv add fastmcp")
    
    # Create server instance
    mcp = FastMCP(name)
    
    # Initialize communicator if not provided
    if communicator is None:
        communicator = ModuleCommunicator()
    
    # Get prompt registry
    prompt_registry = get_prompt_registry()
    
    # Add metadata
    mcp.meta.update({
        "version": "2.0.0",
        "description": "Enhanced MCP server for Granger Hub",
        "features": ["prompts", "tools", "analytics", "orchestration"],
        "author": "Granger Hub Team"
    })
    
    # ===== Module Communication Tools =====
    
    @mcp.tool(
        description="List all registered modules with their capabilities"
    )
    async def list_modules() -> Dict[str, Any]:
        """List all available modules in the system."""
        try:
            modules = await communicator.discover_modules()
            
            # Enhance with additional metadata
            enhanced_modules = []
            for module in modules:
                enhanced = {
                    **module,
                    "status": "active",  # Could check actual status
                    "last_seen": datetime.utcnow().isoformat()
                }
                enhanced_modules.append(enhanced)
            
            return {
                "modules": enhanced_modules,
                "total": len(enhanced_modules),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "modules": [],
                "total": 0
            }
    
    @mcp.tool(
        description="Send a message to a specific module"
    )
    async def send_message(
        target: str,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = 30
    ) -> Dict[str, Any]:
        """Send a message to a target module."""
        try:
            result = await communicator.send_message(
                target=target,
                action=action,
                data=data or {},
                timeout=timeout
            )
            
            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "metadata": {
                    "target": target,
                    "action": action,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    @mcp.tool(
        description="Execute a natural language instruction using the best module"
    )
    async def execute_instruction(
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_modules: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute a natural language instruction."""
        try:
            # Use communicator's intelligent routing
            result = await communicator.execute_instruction(
                instruction=instruction,
                parameters=context or {},
                preferred_modules=preferred_modules
            )
            
            return {
                "success": result.get("success", False),
                "result": result.get("result"),
                "module_used": result.get("module"),
                "execution_time": result.get("execution_time"),
                "metadata": {
                    "instruction": instruction,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    @mcp.tool(
        description="Check compatibility between two modules"
    )
    async def check_module_compatibility(
        source: str,
        target: str,
        integration_type: Optional[str] = "direct"
    ) -> Dict[str, Any]:
        """Check if two modules can communicate effectively."""
        try:
            compat = await communicator.check_compatibility(source, target)
            
            # Enhance with integration recommendations
            recommendations = []
            if not compat.get("compatible"):
                recommendations.append("Consider using an adapter module")
                recommendations.append("Check schema alignment")
            
            return {
                "compatible": compat.get("compatible", False),
                "reason": compat.get("reason"),
                "details": compat.get("details", {}),
                "recommendations": recommendations,
                "integration_type": integration_type
            }
        except Exception as e:
            return {
                "compatible": False,
                "reason": str(e),
                "details": {},
                "recommendations": []
            }
    
    @mcp.tool(
        description="Get the module dependency graph"
    )
    async def get_dependency_graph() -> Dict[str, Any]:
        """Get the dependency relationships between modules."""
        try:
            graph = await communicator.get_dependency_graph()
            
            # Calculate graph metrics
            node_count = len(graph)
            edge_count = sum(len(deps) for deps in graph.values())
            
            return {
                "graph": graph,
                "metrics": {
                    "nodes": node_count,
                    "edges": edge_count,
                    "average_degree": edge_count / node_count if node_count > 0 else 0
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "graph": {},
                "metrics": {},
                "error": str(e)
            }
    
    # ===== Orchestration Tools =====
    
    @mcp.tool(
        description="Create and execute a module pipeline"
    )
    async def execute_pipeline(
        steps: List[Dict[str, Any]],
        input_data: Optional[Dict[str, Any]] = None,
        parallel: bool = False
    ) -> Dict[str, Any]:
        """Execute a pipeline of module operations."""
        try:
            results = []
            current_data = input_data or {}
            
            if parallel:
                # Execute steps in parallel where possible
                tasks = []
                for step in steps:
                    task = communicator.send_message(
                        target=step["module"],
                        action=step["action"],
                        data=step.get("data", current_data)
                    )
                    tasks.append(task)
                
                step_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, result in enumerate(step_results):
                    if isinstance(result, Exception):
                        results.append({
                            "step": i,
                            "error": str(result),
                            "success": False
                        })
                    else:
                        results.append({
                            "step": i,
                            "success": result.success,
                            "data": result.data,
                            "error": result.error
                        })
            else:
                # Execute steps sequentially
                for i, step in enumerate(steps):
                    # Use output from previous step as input
                    step_data = step.get("data", current_data)
                    
                    result = await communicator.send_message(
                        target=step["module"],
                        action=step["action"],
                        data=step_data
                    )
                    
                    results.append({
                        "step": i,
                        "module": step["module"],
                        "action": step["action"],
                        "success": result.success,
                        "data": result.data,
                        "error": result.error
                    })
                    
                    # Update current_data for next step
                    if result.success and result.data:
                        current_data = result.data
            
            # Determine overall success
            all_success = all(r["success"] for r in results)
            
            return {
                "success": all_success,
                "steps": results,
                "final_output": current_data if all_success else None,
                "execution_mode": "parallel" if parallel else "sequential"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "steps": [],
                "final_output": None
            }
    
    # ===== Prompt Tools =====
    
    @mcp.tool(
        description="List all available prompts with filtering"
    )
    async def list_prompts(
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """List available prompts in the system."""
        try:
            prompts = prompt_registry.list_prompts(category=category, tags=tags)
            
            return {
                "prompts": [
                    {
                        "name": p.name,
                        "description": p.description,
                        "category": p.category,
                        "tags": p.tags,
                        "parameters": list(p.parameters.keys()),
                        "required": p.required_params
                    }
                    for p in prompts
                ],
                "total": len(prompts),
                "filters": {
                    "category": category,
                    "tags": tags
                }
            }
        except Exception as e:
            return {
                "prompts": [],
                "total": 0,
                "error": str(e)
            }
    
    @mcp.tool(
        description="Execute a prompt with given parameters"
    )
    async def execute_prompt(
        prompt_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific prompt with parameters."""
        try:
            prompt = prompt_registry.get_prompt(prompt_name)
            if not prompt:
                return {
                    "success": False,
                    "error": f"Prompt '{prompt_name}' not found"
                }
            
            # Render the prompt
            rendered = prompt.render(**parameters)
            
            return {
                "success": True,
                "prompt": prompt_name,
                "rendered": rendered,
                "metadata": {
                    "category": prompt.category,
                    "tags": prompt.tags,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "prompt": prompt_name
            }
    
    # ===== Analytics Tools =====
    
    if enable_analytics:
        # In-memory analytics storage (would be persistent in production)
        analytics_data = {
            "tool_usage": {},
            "module_usage": {},
            "prompt_usage": {},
            "errors": []
        }
        
        @mcp.tool(
            description="Get analytics data for system usage"
        )
        async def get_analytics(
            metric_type: str = "all",
            time_range: Optional[str] = "1h"
        ) -> Dict[str, Any]:
            """Get analytics data for the system."""
            return {
                "metric_type": metric_type,
                "time_range": time_range,
                "data": analytics_data.get(metric_type, analytics_data),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # ===== Register Prompts =====
    
    # Register all prompts from the registry
    for prompt in prompt_registry.list_prompts():
        @mcp.prompt(
            name=prompt.name,
            description=prompt.description
        )
        async def prompt_handler(
            **kwargs
        ) -> str:
            """Dynamic prompt handler."""
            # Get the prompt by name from the closure
            current_prompt = prompt_registry.get_prompt(prompt.name)
            if not current_prompt:
                return f"Prompt {prompt.name} not found"
            
            try:
                return current_prompt.render(**kwargs)
            except Exception as e:
                return f"Error rendering prompt: {str(e)}"
    
    # ===== Utility Tools =====
    
    @mcp.tool(
        description="Get server health and status information"
    )
    async def health_check() -> Dict[str, Any]:
        """Check the health of the MCP server and connected modules."""
        try:
            # Check various components
            modules = await communicator.discover_modules()
            
            return {
                "status": "healthy",
                "components": {
                    "mcp_server": "running",
                    "communicator": "active",
                    "modules": len(modules),
                    "prompts": len(prompt_registry.list_prompts())
                },
                "timestamp": datetime.utcnow().isoformat(),
                "version": mcp.meta.get("version", "unknown")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @mcp.tool(
        description="Get examples for using the hub"
    )
    async def get_examples(
        example_type: Optional[str] = "all"
    ) -> Dict[str, Any]:
        """Get usage examples for the hub."""
        examples = {
            "module_communication": [
                {
                    "description": "Send a message to a module",
                    "tool": "send_message",
                    "params": {
                        "target": "pdf_processor",
                        "action": "extract",
                        "data": {"file": "document.pdf"}
                    }
                }
            ],
            "pipeline": [
                {
                    "description": "Create a processing pipeline",
                    "tool": "execute_pipeline",
                    "params": {
                        "steps": [
                            {"module": "pdf_extractor", "action": "extract"},
                            {"module": "nlp_processor", "action": "analyze"},
                            {"module": "database", "action": "store"}
                        ]
                    }
                }
            ],
            "prompts": get_hub_prompt_examples()
        }
        
        if example_type == "all":
            return examples
        else:
            return examples.get(example_type, {})
    
    return mcp


def run_hub_mcp_server(
    host: str = "localhost",
    port: int = 5000,
    reload: bool = False,
    debug: bool = False
):
    """Run the hub MCP server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload
        debug: Enable debug mode
    """
    # Create server
    mcp = create_hub_mcp_server()
    
    print(f" Starting Granger Hub MCP Server")
    print(f" Endpoint: http://{host}:{port}")
    print(f" Tools: {len(mcp._tools)}")
    print(f" Prompts: {len(mcp._prompts)}")
    
    if reload:
        print(" Auto-reload enabled")
    
    print("\nPress Ctrl+C to stop")
    
    try:
        # Run the server
        mcp.run(
            transport="stdio"  # Use stdio for Claude Desktop
        )
    except KeyboardInterrupt:
        print("\n\n Server stopped")


if __name__ == "__main__":
    # Run the server when executed directly
    run_hub_mcp_server()