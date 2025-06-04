"""
Execute test workflows with monitoring and instrumentation
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable
import time
from datetime import datetime
import json
from dataclasses import dataclass, field


@dataclass
class WorkflowMetrics:
    """Metrics collected during workflow execution"""
    start_time: float = 0
    end_time: float = 0
    total_duration: float = 0
    step_count: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    step_durations: List[Dict[str, Any]] = field(default_factory=list)
    message_sizes: List[Dict[str, Any]] = field(default_factory=list)
    error_details: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration": self.total_duration,
            "step_count": self.step_count,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "average_step_duration": sum(s["duration"] for s in self.step_durations) / len(self.step_durations) if self.step_durations else 0,
            "total_message_size": sum(s["size"] for s in self.message_sizes),
            "error_rate": self.failed_steps / self.step_count if self.step_count > 0 else 0
        }


class WorkflowRunner:
    """Run workflows with instrumentation and monitoring"""
    
    def __init__(self, module_registry: Dict[str, Any]):
        self.module_registry = module_registry
        self.message_log: List[Dict[str, Any]] = []
        self.metrics = WorkflowMetrics()
        self.hooks: Dict[str, List[Callable]] = {
            "pre_step": [],
            "post_step": [],
            "on_error": [],
            "on_complete": []
        }
        self.context: Dict[str, Any] = {}  # Shared context between steps
    
    def add_hook(self, event: str, hook: Callable) -> None:
        """
        Add a hook for workflow events
        
        Args:
            event: Event name (pre_step, post_step, on_error, on_complete)
            hook: Callback function
        """
        if event in self.hooks:
            self.hooks[event].append(hook)
    
    async def execute_workflow(
        self, 
        workflow: List[Any],  # List of TestMessage objects
        timeout: int = 30,
        fail_fast: bool = True,
        retry_on_error: bool = False,
        max_retries: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Execute a test workflow with full instrumentation
        
        Args:
            workflow: List of TestMessage objects defining the workflow
            timeout: Timeout for each step in seconds
            fail_fast: Stop on first error if True
            retry_on_error: Retry failed steps
            max_retries: Maximum number of retries per step
            
        Returns:
            List of execution results
        """
        results = []
        self.metrics.start_time = time.time()
        self.metrics.step_count = len(workflow)
        
        # Execute pre-workflow hooks
        await self._run_hooks("pre_workflow", workflow=workflow)
        
        for step_index, message in enumerate(workflow):
            step_start = time.time()
            retry_count = 0
            step_succeeded = False
            
            while retry_count <= (max_retries if retry_on_error else 0) and not step_succeeded:
                try:
                    # Pre-step hooks
                    await self._run_hooks("pre_step", step=step_index, message=message)
                    
                    # Log message
                    message_data = {
                        "step": step_index,
                        "from": message.from_module,
                        "to": message.to_module,
                        "content": message.content,
                        "metadata": message.metadata,
                        "timestamp": datetime.now().isoformat(),
                        "retry": retry_count
                    }
                    self.message_log.append(message_data)
                    
                    # Record message size
                    message_size = len(json.dumps(message.content))
                    self.metrics.message_sizes.append({
                        "step": step_index,
                        "size": message_size
                    })
                    
                    # Get target module
                    module = self.module_registry.get(message.to_module)
                    if not module:
                        raise ValueError(f"Module '{message.to_module}' not registered")
                    
                    # Prepare enriched message with context
                    enriched_content = {
                        **message.content,
                        "_context": self.context,
                        "_step": step_index,
                        "_workflow_id": id(workflow)
                    }
                    
                    # Process message with timeout
                    if asyncio.iscoroutinefunction(getattr(module, 'process', None)):
                        result = await asyncio.wait_for(
                            module.process(enriched_content),
                            timeout=timeout
                        )
                    else:
                        # Handle sync modules
                        result = await asyncio.wait_for(
                            asyncio.to_thread(module.process, enriched_content),
                            timeout=timeout
                        )
                    
                    # Update context with result if it contains context updates
                    if isinstance(result, dict) and "_context_update" in result:
                        self.context.update(result["_context_update"])
                    
                    # Record successful result
                    duration = time.time() - step_start
                    step_result = {
                        "step": step_index,
                        "from": message.from_module,
                        "to": message.to_module,
                        "content": message.content,
                        "result": result,
                        "duration": duration,
                        "metadata": message.metadata,
                        "retry_count": retry_count
                    }
                    results.append(step_result)
                    
                    # Record metrics
                    self.metrics.step_durations.append({
                        "step": step_index,
                        "module": message.to_module,
                        "duration": duration
                    })
                    self.metrics.successful_steps += 1
                    
                    # Post-step hooks
                    await self._run_hooks("post_step", step=step_index, result=step_result)
                    
                    step_succeeded = True
                    
                except asyncio.TimeoutError:
                    error_info = {
                        "step": step_index,
                        "module": message.to_module,
                        "error": f"Timeout after {timeout}s",
                        "error_type": "TimeoutError",
                        "duration": time.time() - step_start,
                        "retry_count": retry_count
                    }
                    
                    if retry_count < max_retries and retry_on_error:
                        retry_count += 1
                        await asyncio.sleep(0.5 * retry_count)  # Exponential backoff
                        continue
                    
                    results.append(error_info)
                    self.metrics.failed_steps += 1
                    self.metrics.error_details.append(error_info)
                    
                    # Error hooks
                    await self._run_hooks("on_error", step=step_index, error=error_info)
                    
                    if fail_fast:
                        break
                        
                except Exception as e:
                    error_info = {
                        "step": step_index,
                        "module": message.to_module,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "duration": time.time() - step_start,
                        "retry_count": retry_count
                    }
                    
                    if retry_count < max_retries and retry_on_error:
                        retry_count += 1
                        await asyncio.sleep(0.5 * retry_count)
                        continue
                    
                    results.append(error_info)
                    self.metrics.failed_steps += 1
                    self.metrics.error_details.append(error_info)
                    
                    # Error hooks
                    await self._run_hooks("on_error", step=step_index, error=error_info)
                    
                    if fail_fast:
                        break
        
        # Calculate final metrics
        self.metrics.end_time = time.time()
        self.metrics.total_duration = self.metrics.end_time - self.metrics.start_time
        
        # Execute completion hooks
        await self._run_hooks("on_complete", results=results, metrics=self.metrics)
        
        return results
    
    async def _run_hooks(self, event: str, **kwargs) -> None:
        """Run hooks for a specific event"""
        for hook in self.hooks.get(event, []):
            if asyncio.iscoroutinefunction(hook):
                await hook(**kwargs)
            else:
                hook(**kwargs)
    
    def get_metrics(self) -> WorkflowMetrics:
        """Get execution metrics"""
        return self.metrics
    
    def get_message_log(self) -> List[Dict[str, Any]]:
        """Get complete message log"""
        return self.message_log
    
    def get_execution_trace(self) -> Dict[str, Any]:
        """Get complete execution trace for debugging"""
        return {
            "workflow_id": id(self),
            "metrics": self.metrics.to_dict(),
            "message_log": self.message_log,
            "context": self.context,
            "module_registry": list(self.module_registry.keys())
        }
    
    def print_execution_summary(self) -> None:
        """Print a summary of the workflow execution"""
        print(f"\n{'='*60}")
        print("Workflow Execution Summary")
        print(f"{'='*60}")
        print(f"Total Steps: {self.metrics.step_count}")
        print(f"Successful: {self.metrics.successful_steps}")
        print(f"Failed: {self.metrics.failed_steps}")
        print(f"Total Duration: {self.metrics.total_duration:.2f}s")
        
        if self.metrics.step_durations:
            avg_duration = sum(s["duration"] for s in self.metrics.step_durations) / len(self.metrics.step_durations)
            print(f"Average Step Duration: {avg_duration:.3f}s")
        
        if self.metrics.error_details:
            print(f"\nErrors:")
            for error in self.metrics.error_details:
                print(f"  Step {error['step']} ({error['module']}): {error['error']}")
        
        print(f"{'='*60}\n")
    
    def reset(self) -> None:
        """Reset runner state for reuse"""
        self.message_log = []
        self.metrics = WorkflowMetrics()
        self.context = {}


class ParallelWorkflowRunner(WorkflowRunner):
    """Execute workflow steps in parallel where possible"""
    
    async def execute_workflow(
        self, 
        workflow: List[Any],
        parallel_groups: Optional[List[List[int]]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Execute workflow with parallel step execution
        
        Args:
            workflow: List of workflow steps
            parallel_groups: List of step indices that can run in parallel
            **kwargs: Additional arguments for parent execute_workflow
            
        Returns:
            List of execution results
        """
        if not parallel_groups:
            # No parallel execution specified, use sequential
            return await super().execute_workflow(workflow, **kwargs)
        
        results = [None] * len(workflow)
        self.metrics.start_time = time.time()
        self.metrics.step_count = len(workflow)
        
        for group in parallel_groups:
            # Execute steps in group in parallel
            tasks = []
            for step_index in group:
                if step_index < len(workflow):
                    message = workflow[step_index]
                    task = self._execute_single_step(
                        step_index, 
                        message, 
                        kwargs.get("timeout", 30),
                        kwargs.get("retry_on_error", False),
                        kwargs.get("max_retries", 3)
                    )
                    tasks.append((step_index, task))
            
            # Wait for all tasks in group to complete
            for step_index, task in tasks:
                try:
                    result = await task
                    results[step_index] = result
                    if "error" not in result:
                        self.metrics.successful_steps += 1
                    else:
                        self.metrics.failed_steps += 1
                        if kwargs.get("fail_fast", True):
                            break
                except Exception as e:
                    error_result = {
                        "step": step_index,
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                    results[step_index] = error_result
                    self.metrics.failed_steps += 1
                    if kwargs.get("fail_fast", True):
                        break
        
        self.metrics.end_time = time.time()
        self.metrics.total_duration = self.metrics.end_time - self.metrics.start_time
        
        # Filter out None values and return
        return [r for r in results if r is not None]
    
    async def _execute_single_step(
        self, 
        step_index: int, 
        message: Any,
        timeout: int,
        retry_on_error: bool,
        max_retries: int
    ) -> Dict[str, Any]:
        """Execute a single workflow step"""
        # Implementation similar to parent's execute_workflow but for single step
        # This is a simplified version - in production would have full error handling
        module = self.module_registry.get(message.to_module)
        if not module:
            return {
                "step": step_index,
                "error": f"Module '{message.to_module}' not found",
                "error_type": "ModuleNotFound"
            }
        
        try:
            result = await asyncio.wait_for(
                module.process(message.content),
                timeout=timeout
            )
            return {
                "step": step_index,
                "from": message.from_module,
                "to": message.to_module,
                "result": result,
                "content": message.content
            }
        except Exception as e:
            return {
                "step": step_index,
                "error": str(e),
                "error_type": type(e).__name__
            }