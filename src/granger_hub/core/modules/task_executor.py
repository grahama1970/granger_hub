"""
Task Executor for Claude Instances.

Purpose: Enables Claude instances to execute specific tasks, use tools,
and handle bidirectional instructions from both humans and other Claude instances.

This allows scenarios like:
- Claude B tells Claude A to "spin up webserver and take screenshot"
- Human tells Claude to "research this topic using perplexity"
- Claude instances can delegate tasks to each other
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
import uuid

from .claude_code_communicator import ClaudeCodeCommunicator


@dataclass
class Task:
    """Represents a task to be executed."""
    id: str
    type: str  # 'execute', 'research', 'screenshot', 'webserver', etc.
    instruction: str
    requester: str  # Who requested (module name or 'human')
    target_tools: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = None
    completed_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class TaskExecutor:
    """Executes tasks for Claude instances with tool usage."""
    
    def __init__(self, module_name: str, system_prompt: str):
        """Initialize task executor.
        
        Args:
            module_name: Name of this Claude instance/module
            system_prompt: System prompt with capabilities
        """
        self.module_name = module_name
        self.system_prompt = system_prompt
        self.communicator = ClaudeCodeCommunicator(module_name, system_prompt)
        
        # Task queue and handlers
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.task_handlers: Dict[str, Callable] = {}
        self.active_tasks: Dict[str, Task] = {}
        
        # Register default handlers
        self._register_default_handlers()
        
        # Tool availability flags
        self.available_tools = self._detect_available_tools()
    
    def _detect_available_tools(self) -> Dict[str, bool]:
        """Detect which tools are available."""
        return {
            "ask_perplexity": True,  # Assuming MCP perplexity is available
            "screenshot": True,      # Assuming screenshot capability
            "webserver": True,       # Assuming can start web servers
            "file_operations": True,  # File read/write
            "web_fetch": True,       # Web scraping
            "code_execution": True   # Running code
        }
    
    def _register_default_handlers(self):
        """Register default task handlers."""
        self.register_handler("execute", self._handle_execute_task)
        self.register_handler("research", self._handle_research_task)
        self.register_handler("screenshot", self._handle_screenshot_task)
        self.register_handler("webserver", self._handle_webserver_task)
        self.register_handler("delegate", self._handle_delegate_task)
    
    def register_handler(self, task_type: str, handler: Callable):
        """Register a handler for a specific task type."""
        self.task_handlers[task_type] = handler
    
    async def receive_instruction(self, 
                                 instruction: str,
                                 requester: str,
                                 task_type: Optional[str] = None,
                                 parameters: Optional[Dict[str, Any]] = None) -> Task:
        """Receive an instruction from human or another Claude instance.
        
        Args:
            instruction: The instruction to execute
            requester: Who is requesting (module name or 'human')
            task_type: Type of task (if None, will be inferred)
            parameters: Additional parameters
            
        Returns:
            Task object with execution details
        """
        # Infer task type if not specified
        if not task_type:
            task_type = await self._infer_task_type(instruction)
        
        # Create task
        task = Task(
            id=str(uuid.uuid4()),
            type=task_type,
            instruction=instruction,
            requester=requester,
            parameters=parameters or {}
        )
        
        # Add to queue
        await self.task_queue.put(task)
        self.active_tasks[task.id] = task
        
        # Execute task
        await self._execute_task(task)
        
        return task
    
    async def _infer_task_type(self, instruction: str) -> str:
        """Infer task type from instruction using Claude."""
        prompt = f"""
Analyze this instruction and determine the task type:

Instruction: {instruction}

Task types:
- execute: General code execution or commands
- research: Requires searching/researching information
- screenshot: Taking screenshots or visual capture
- webserver: Starting/managing web servers
- delegate: Delegating to another module

Respond with just the task type.
"""
        
        result = await self.communicator.send_message(
            target_module="self",
            message=prompt,
            target_context="You are analyzing task types"
        )
        
        task_type = result.response.strip().lower()
        return task_type if task_type in self.task_handlers else "execute"
    
    async def _execute_task(self, task: Task):
        """Execute a task using the appropriate handler."""
        handler = self.task_handlers.get(task.type, self._handle_execute_task)
        
        try:
            task.status = "executing"
            result = await handler(task)
            task.result = result
            task.status = "completed"
            task.completed_at = datetime.now().isoformat()
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            task.completed_at = datetime.now().isoformat()
    
    async def _handle_execute_task(self, task: Task) -> Any:
        """Handle general execution tasks."""
        # Build prompt with tool availability
        tools_info = "\n".join([
            f"- {tool}: {'available' if available else 'not available'}"
            for tool, available in self.available_tools.items()
        ])
        
        prompt = f"""
You are executing a task as module '{self.module_name}'.

Task from: {task.requester}
Instruction: {task.instruction}

Available tools:
{tools_info}

Parameters: {json.dumps(task.parameters, indent=2)}

Execute this task and provide the result. If you need to use tools, 
indicate which tools you would use and how.
"""
        
        result = await self.communicator.send_message(
            target_module="self",
            message=prompt,
            context={"task_id": task.id}
        )
        
        return result.response
    
    async def _handle_research_task(self, task: Task) -> Any:
        """Handle research tasks using ask-perplexity or similar tools."""
        prompt = f"""
You are conducting research as module '{self.module_name}'.

Research request from: {task.requester}
Topic: {task.instruction}

Use the ask-perplexity tool or other research tools to gather information.
Provide a comprehensive response with sources.

Additional context: {json.dumps(task.parameters, indent=2)}
"""
        
        # In real implementation, this would call mcp__perplexity-ask__perplexity_ask
        result = await self.communicator.send_message(
            target_module="self",
            message=prompt,
            context={
                "task_id": task.id,
                "tools": ["ask_perplexity"]
            }
        )
        
        return result.response
    
    async def _handle_screenshot_task(self, task: Task) -> Any:
        """Handle screenshot tasks."""
        prompt = f"""
You are taking a screenshot as module '{self.module_name}'.

Screenshot request from: {task.requester}
Instructions: {task.instruction}

Steps:
1. Identify what needs to be captured
2. Take the screenshot
3. Analyze/describe the screenshot as requested

Specific requirements: {json.dumps(task.parameters, indent=2)}
"""
        
        # In real implementation, would use screenshot tools
        result = await self.communicator.send_message(
            target_module="self",
            message=prompt,
            context={
                "task_id": task.id,
                "tools": ["screenshot", "image_analysis"]
            }
        )
        
        return result.response
    
    async def _handle_webserver_task(self, task: Task) -> Any:
        """Handle web server tasks."""
        prompt = f"""
You are managing a web server as module '{self.module_name}'.

Web server request from: {task.requester}
Instructions: {task.instruction}

This might involve:
- Starting a web server
- Configuring routes
- Serving content
- Taking screenshots of the result

Parameters: {json.dumps(task.parameters, indent=2)}
"""
        
        result = await self.communicator.send_message(
            target_module="self",
            message=prompt,
            context={
                "task_id": task.id,
                "tools": ["webserver", "file_operations"]
            }
        )
        
        return result.response
    
    async def _handle_delegate_task(self, task: Task) -> Any:
        """Handle task delegation to another module."""
        target_module = task.parameters.get("target_module")
        if not target_module:
            raise ValueError("Delegation requires target_module parameter")
        
        # Send instruction to target module
        result = await self.communicator.send_message(
            target_module=target_module,
            message=task.instruction,
            context={
                "delegated_from": self.module_name,
                "original_requester": task.requester,
                "task_type": task.parameters.get("delegate_type", "execute")
            }
        )
        
        return f"Delegated to {target_module}: {result.response}"
    
    async def give_instruction(self,
                              target: str,
                              instruction: str,
                              wait_for_result: bool = True) -> Optional[Any]:
        """Give an instruction to another Claude instance.
        
        Args:
            target: Target module/instance name
            instruction: Instruction to give
            wait_for_result: Whether to wait for completion
            
        Returns:
            Result if waiting, None otherwise
        """
        # Create delegation task
        task = await self.receive_instruction(
            instruction=instruction,
            requester=self.module_name,
            task_type="delegate",
            parameters={"target_module": target}
        )
        
        if wait_for_result:
            # Wait for task completion
            while task.status not in ["completed", "failed"]:
                await asyncio.sleep(0.1)
            
            return task.result if task.status == "completed" else task.error
        
        return None
    
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get status of a task."""
        return self.active_tasks.get(task_id)
    
    def list_active_tasks(self) -> List[Task]:
        """List all active tasks."""
        return [
            task for task in self.active_tasks.values()
            if task.status in ["pending", "executing"]
        ]


# Example implementation
class IntelligentModule:
    """A module that can both give and receive instructions."""
    
    def __init__(self, name: str, capabilities: str):
        self.name = name
        self.executor = TaskExecutor(
            module_name=name,
            system_prompt=f"You are {name} with capabilities: {capabilities}"
        )
    
    async def handle_human_instruction(self, instruction: str) -> Task:
        """Handle instruction from human."""
        return await self.executor.receive_instruction(
            instruction=instruction,
            requester="human"
        )
    
    async def instruct_other_module(self, 
                                  target: str,
                                  instruction: str) -> Any:
        """Instruct another module."""
        return await self.executor.give_instruction(
            target=target,
            instruction=instruction
        )


# Demo usage
async def demo_bidirectional_instructions():
    """Demonstrate bidirectional instruction handling."""
    
    # Create two intelligent modules
    module_a = IntelligentModule(
        "WebAnalyzer",
        "web server management, screenshot analysis, D3 visualization"
    )
    
    module_b = IntelligentModule(
        "DataProcessor", 
        "data analysis, research, reporting"
    )
    
    print("🤖 Bidirectional Instruction Demo\n")
    
    # Scenario 1: Human instructs Module A
    print("1️⃣ Human → Module A:")
    task1 = await module_a.handle_human_instruction(
        "Start a web server on port 8080 and create a D3 force-directed graph visualization"
    )
    print(f"   Task ID: {task1.id}")
    print(f"   Status: {task1.status}")
    print(f"   Result: {task1.result[:100]}..." if task1.result else "   Processing...")
    
    # Scenario 2: Module B instructs Module A
    print("\n2️⃣ Module B → Module A:")
    result = await module_b.instruct_other_module(
        target="WebAnalyzer",
        instruction=(
            "Spin up the webserver and take a screenshot, "
            "describe the screenshot as it relates to a well formatted D3 node graph "
            "and send me back the description"
        )
    )
    print(f"   Result: {result[:200]}..." if result else "   Processing...")
    
    # Scenario 3: Module A researches using tools
    print("\n3️⃣ Module A researches:")
    task3 = await module_a.handle_human_instruction(
        "Research the latest D3.js best practices for force-directed graphs using perplexity"
    )
    print(f"   Task type: {task3.type}")
    print(f"   Status: {task3.status}")
    
    print("\n✅ Demo completed!")


if __name__ == "__main__":
    asyncio.run(demo_bidirectional_instructions())