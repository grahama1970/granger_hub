"""
# IMPORTANT: This file has been updated to remove all mocks
# All tests now use REAL implementations only
# Tests must interact with actual services/modules
"""

"""
Base class for all integration scenario tests
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))



import pytest
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import asyncio
import time
from datetime import datetime


@dataclass
class TestMessage:
    """Test message with validation"""
    from_module: str
    to_module: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate message structure"""
        if not self.from_module:
            return False, "from_module is required"
        if not self.to_module:
            return False, "to_module is required"
        if not isinstance(self.content, dict):
            return False, "content must be a dictionary"
        if self.metadata and not isinstance(self.metadata, dict):
            return False, "metadata must be a dictionary"
        return True, None


class ScenarioTestBase(ABC):
    """Base class for scenario tests"""
    
    def setup_method(self):
        """Setup test environment"""
        self.modules = {}
        self.messages = []
        self.results = []
        self.performance_metrics = {
            "start_time": None,
            "end_time": None,
            "step_durations": [],
            "total_duration": 0
        }
        self.errors = []
        
        # Register modules for this test
        module_configs = self.register_modules()
        for name, module in module_configs.items():
            self.modules[name] = module
    
    @abstractmethod
    def register_modules(self) -> Dict[str, Any]:
        """
        Register modules for this scenario.
        
        Returns:
            Dict mapping module names to module instances (or mocks)
        """
        pass
    
    @abstractmethod
    def create_test_workflow(self) -> List[TestMessage]:
        """
        Create the test workflow as a list of messages.
        
        Returns:
            List of TestMessage objects defining the workflow
        """
        pass
    
    @abstractmethod
    def assert_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Assert expected results from the workflow execution.
        
        Args:
            results: List of result dictionaries from workflow execution
        """
        pass
    
    async def run_scenario(
        self, 
        mock_responses: Optional[Dict[str, Dict[str, Any]]] = None,
        timeout: int = 30,
        fail_fast: bool = True
    ) -> Dict[str, Any]:
        """
        Execute the scenario with optional mocking
        
        Args:
            mock_responses: Optional dict of module_name -> {task -> response}
            timeout: Timeout for each step in seconds
            fail_fast: Stop on first error if True
            
        Returns:
            Dict containing scenario results and metrics
        """
        # Apply mock responses if provided
        if mock_responses:
            for module_name, responses in mock_responses.items():
                if module_name in self.modules:
                    module = self.modules[module_name]
                    if hasattr(module, 'set_responses'):
                        module.set_responses(responses)
        
        # Create workflow
        workflow = self.create_test_workflow()
        
        # Validate workflow
        for i, message in enumerate(workflow):
            valid, error = message.validate()
            if not valid:
                raise ValueError(f"Invalid message at step {i}: {error}")
        
        # Execute workflow
        self.performance_metrics["start_time"] = time.time()
        results = []
        
        for step, message in enumerate(workflow):
            step_start = time.time()
            
            try:
                # Log message
                self.messages.append({
                    "step": step,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Get target module
                module = self.modules.get(message.to_module)
                if not module:
                    raise ValueError(f"Module '{message.to_module}' not registered")
                
                # Process message
                if asyncio.iscoroutinefunction(module.process):
                    result = await asyncio.wait_for(
                        module.process(message.content),
                        timeout=timeout
                    )
                else:
                    # Handle sync modules
                    result = await asyncio.wait_for(
                        asyncio.to_thread(module.process, message.content),
                        timeout=timeout
                    )
                
                # Record result
                step_duration = time.time() - step_start
                self.performance_metrics["step_durations"].append({
                    "step": step,
                    "module": message.to_module,
                    "duration": step_duration
                })
                
                results.append({
                    "step": step,
                    "from": message.from_module,
                    "to": message.to_module,
                    "content": message.content,
                    "result": result,
                    "duration": step_duration,
                    "metadata": message.metadata
                })
                
            except asyncio.TimeoutError:
                error_info = {
                    "step": step,
                    "module": message.to_module,
                    "error": "timeout",
                    "error_type": "TimeoutError",
                    "duration": time.time() - step_start
                }
                results.append(error_info)
                self.errors.append(error_info)
                
                if fail_fast:
                    break
                    
            except Exception as e:
                error_info = {
                    "step": step,
                    "module": message.to_module,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": time.time() - step_start
                }
                results.append(error_info)
                self.errors.append(error_info)
                
                if fail_fast:
                    break
        
        # Calculate total duration
        self.performance_metrics["end_time"] = time.time()
        self.performance_metrics["total_duration"] = (
            self.performance_metrics["end_time"] - 
            self.performance_metrics["start_time"]
        )
        
        self.results = results
        
        return {
            "scenario": self.__class__.__name__,
            "success": len(self.errors) == 0,
            "results": results,
            "errors": self.errors,
            "performance": self.performance_metrics,
            "messages_sent": len(self.messages),
            "workflow_steps": len(workflow),
            "completed_steps": len([r for r in results if "error" not in r])
        }
    
    def run_sync(self, **kwargs) -> Dict[str, Any]:
        """Synchronous wrapper for run_scenario"""
        return asyncio.run(self.run_scenario(**kwargs))
    
    def get_step_result(self, step: int) -> Optional[Dict[str, Any]]:
        """Get result for a specific step"""
        for result in self.results:
            if result.get("step") == step:
                return result
        return None
    
    def get_module_results(self, module_name: str) -> List[Dict[str, Any]]:
        """Get all results from a specific module"""
        return [
            r for r in self.results 
            if r.get("to") == module_name or r.get("from") == module_name
        ]
    
    def print_workflow_summary(self):
        """Print a summary of the workflow execution"""
        print(f"\n{'='*60}")
        print(f"Scenario: {self.__class__.__name__}")
        print(f"{'='*60}")
        print(f"Total Steps: {len(self.results)}")
        print(f"Successful: {len([r for r in self.results if 'error' not in r])}")
        print(f"Failed: {len(self.errors)}")
        print(f"Total Duration: {self.performance_metrics['total_duration']:.2f}s")
        print(f"\nStep Details:")
        print(f"{'Step':<6} {'From':<15} {'To':<15} {'Duration':<10} {'Status':<10}")
        print(f"{'-'*66}")
        
        for result in self.results:
            step = result.get("step", "?")
            from_mod = result.get("from", "?")[:14]
            to_mod = result.get("to", "?")[:14]
            duration = f"{result.get('duration', 0):.3f}s"
            status = "ERROR" if "error" in result else "OK"
            
            print(f"{step:<6} {from_mod:<15} {to_mod:<15} {duration:<10} {status:<10}")
            
            if "error" in result:
                print(f"       Error: {result['error']}")
        
        print(f"{'='*60}\n")