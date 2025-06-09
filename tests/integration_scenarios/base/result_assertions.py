"""
Common assertions for scenario testing
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))



from typing import List, Dict, Any, Optional, Union, Callable
import pytest


class ScenarioAssertions:
    """Reusable assertions for integration scenarios"""
    
    @staticmethod
    def assert_workflow_completed(results: List[Dict[str, Any]], expected_steps: int) -> None:
        """
        Assert all workflow steps completed successfully
        
        Args:
            results: Workflow execution results
            expected_steps: Expected number of steps
        """
        assert len(results) == expected_steps, f"Expected {expected_steps} steps, got {len(results)}"
        
        errors = []
        for i, result in enumerate(results):
            assert result.get("step") == i, f"Step {i} missing or out of order"
            if "error" in result:
                errors.append(f"Step {i} ({result.get('to', 'unknown')}): {result['error']}")
        
        if errors:
            pytest.fail(f"Workflow had errors:\n" + "\n".join(errors))
    
    @staticmethod
    def assert_module_called(
        results: List[Dict[str, Any]], 
        module_name: str, 
        times: Optional[int] = None,
        min_times: Optional[int] = None,
        max_times: Optional[int] = None
    ) -> None:
        """
        Assert a module was called expected number of times
        
        Args:
            results: Workflow execution results
            module_name: Name of the module
            times: Exact number of times (optional)
            min_times: Minimum number of times (optional)
            max_times: Maximum number of times (optional)
        """
        calls = [r for r in results if r.get("to") == module_name]
        call_count = len(calls)
        
        if times is not None:
            assert call_count == times, f"Expected {module_name} called {times} times, got {call_count}"
        
        if min_times is not None:
            assert call_count >= min_times, f"Expected {module_name} called at least {min_times} times, got {call_count}"
        
        if max_times is not None:
            assert call_count <= max_times, f"Expected {module_name} called at most {max_times} times, got {call_count}"
    
    @staticmethod
    def assert_data_flow(
        results: List[Dict[str, Any]], 
        key: str, 
        from_step: int, 
        to_step: int,
        transform: Optional[Callable[[Any], Any]] = None
    ) -> None:
        """
        Assert data flows correctly between steps
        
        Args:
            results: Workflow execution results
            key: Data key to track
            from_step: Source step index
            to_step: Target step index
            transform: Optional transformation function to apply
        """
        # Get source data
        source_result = results[from_step].get("result", {})
        source_data = source_result.get(key)
        assert source_data is not None, f"Key '{key}' not found in step {from_step} result"
        
        # Get target data
        target_message = results[to_step].get("content", {})
        target_data = target_message.get(key)
        
        # Apply transformation if specified
        if transform:
            expected_data = transform(source_data)
        else:
            expected_data = source_data
        
        assert target_data == expected_data, f"Data mismatch: {key} not propagated correctly from step {from_step} to {to_step}"
    
    @staticmethod
    def assert_performance(
        results: List[Dict[str, Any]], 
        max_total_duration: Optional[float] = None,
        max_step_duration: Optional[float] = None,
        performance_metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Assert performance requirements are met
        
        Args:
            results: Workflow execution results
            max_total_duration: Maximum allowed total duration
            max_step_duration: Maximum allowed duration for any single step
            performance_metrics: Optional performance metrics dict
        """
        # Check individual step durations
        if max_step_duration:
            for result in results:
                duration = result.get("duration", 0)
                step = result.get("step", "?")
                module = result.get("to", "?")
                assert duration <= max_step_duration, f"Step {step} ({module}) took {duration}s, max allowed {max_step_duration}s"
        
        # Check total duration
        if max_total_duration:
            if performance_metrics and "total_duration" in performance_metrics:
                total_duration = performance_metrics["total_duration"]
            else:
                total_duration = sum(r.get("duration", 0) for r in results)
            
            assert total_duration <= max_total_duration, f"Workflow took {total_duration}s, max allowed {max_total_duration}s"
    
    @staticmethod
    def assert_result_contains(
        results: List[Dict[str, Any]], 
        step: int, 
        expected_data: Dict[str, Any],
        in_result: bool = True
    ) -> None:
        """
        Assert that a step's result contains expected data'
        
        Args:
            results: Workflow execution results
            step: Step index to check
            expected_data: Expected key-value pairs
            in_result: If True, check in result field, else in message content
        """
        assert step < len(results), f"Step {step} does not exist (only {len(results)} steps)"
        
        step_data = results[step]
        if in_result:
            actual_data = step_data.get("result", {})
        else:
            actual_data = step_data.get("content", {})
        
        for key, expected_value in expected_data.items():
            assert key in actual_data, f"Key '{key}' not found in step {step} {'result' if in_result else 'content'}"
            actual_value = actual_data[key]
            assert actual_value == expected_value, f"Step {step}: Expected {key}={expected_value}, got {actual_value}"
    
    @staticmethod
    def assert_error_at_step(
        results: List[Dict[str, Any]], 
        step: int,
        error_type: Optional[str] = None,
        error_contains: Optional[str] = None
    ) -> None:
        """
        Assert that an error occurred at a specific step
        
        Args:
            results: Workflow execution results
            step: Step where error should occur
            error_type: Expected error type (optional)
            error_contains: Substring that should be in error message (optional)
        """
        assert step < len(results), f"Step {step} does not exist"
        
        step_result = results[step]
        assert "error" in step_result, f"Expected error at step {step}, but step succeeded"
        
        if error_type:
            actual_type = step_result.get("error_type", "unknown")
            assert actual_type == error_type, f"Expected error type '{error_type}', got '{actual_type}'"
        
        if error_contains:
            error_msg = step_result.get("error", "")
            assert error_contains in error_msg, f"Error message does not contain '{error_contains}': {error_msg}"
    
    @staticmethod
    def assert_no_errors(results: List[Dict[str, Any]]) -> None:
        """Assert that no errors occurred in the workflow"""
        errors = [r for r in results if "error" in r]
        if errors:
            error_summary = []
            for error in errors:
                step = error.get("step", "?")
                module = error.get("module", error.get("to", "?"))
                msg = error.get("error", "unknown error")
                error_summary.append(f"Step {step} ({module}): {msg}")
            pytest.fail(f"Workflow had {len(errors)} errors:\n" + "\n".join(error_summary))
    
    @staticmethod
    def assert_module_sequence(
        results: List[Dict[str, Any]], 
        expected_sequence: List[str]
    ) -> None:
        """
        Assert that modules were called in the expected sequence
        
        Args:
            results: Workflow execution results
            expected_sequence: Expected sequence of module names
        """
        actual_sequence = [r.get("to", "") for r in results if "error" not in r]
        assert actual_sequence == expected_sequence, f"Module sequence mismatch.\nExpected: {expected_sequence}\nActual: {actual_sequence}"
    
    @staticmethod
    def assert_metadata_propagated(
        results: List[Dict[str, Any]], 
        key: str,
        from_step: int,
        to_step: int
    ) -> None:
        """
        Assert that metadata is propagated between steps
        
        Args:
            results: Workflow execution results
            key: Metadata key to check
            from_step: Source step
            to_step: Target step
        """
        source_metadata = results[from_step].get("metadata", {})
        target_metadata = results[to_step].get("metadata", {})
        
        assert key in source_metadata, f"Metadata key '{key}' not found in step {from_step}"
        assert key in target_metadata, f"Metadata key '{key}' not found in step {to_step}"
        assert source_metadata[key] == target_metadata[key], f"Metadata '{key}' not propagated correctly"
    
    @staticmethod
    def assert_partial_completion(
        results: List[Dict[str, Any]], 
        completed_steps: int,
        total_steps: int
    ) -> None:
        """
        Assert that workflow partially completed up to a certain step
        
        Args:
            results: Workflow execution results
            completed_steps: Number of steps that should have completed
            total_steps: Total expected steps
        """
        assert len(results) <= total_steps, f"Got more results ({len(results)}) than expected steps ({total_steps})"
        
        successful = [r for r in results if "error" not in r]
        assert len(successful) == completed_steps, f"Expected {completed_steps} successful steps, got {len(successful)}"
        
        # Verify steps are in order
        for i in range(completed_steps):
            assert results[i].get("step") == i, f"Step {i} is out of order or missing"
            assert "error" not in results[i], f"Step {i} should have succeeded but has error"