"""
Integration module for RL metrics collection

This module provides integration points between the existing
hub decision-making code and the new metrics collection system.

Third-party documentation:
- asyncio: https://docs.python.org/3/library/asyncio.html

Sample input:
    from claude_coms.rl.metrics.integration import with_metrics_collection
    
    @with_metrics_collection
    async def select_module(modules, context):
        # Existing selection logic
        return selected_module

Expected output:
    Module selection with automatic metrics recording
"""

import functools
from typing import Dict, Any, List, Callable, Optional
import asyncio

from loguru import logger

from .collector import get_metrics_collector, RLMetricsCollector


def with_metrics_collection(func: Callable) -> Callable:
    """Decorator to add metrics collection to module selection functions"""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        collector = get_metrics_collector()
        
        # Extract context from arguments
        # This assumes the function signature includes modules and context
        modules = args[0] if args else kwargs.get('modules', [])
        context = args[1] if len(args) > 1 else kwargs.get('context', {})
        
        # Record the decision
        decision_id = await collector.record_module_selection(
            available_modules=modules,
            selected_module="pending",  # Will be updated
            selection_probabilities={},  # Will be filled if available
            task_context=context
        )
        
        try:
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Extract results
            if isinstance(result, tuple):
                selected_module, metadata = result
            else:
                selected_module = result
                metadata = {}
            
            # Update with outcome
            await collector.update_decision_outcome(
                decision_id=decision_id,
                success=True,
                execution_time_ms=metadata.get('execution_time_ms', 0),
                reward=metadata.get('reward', 0.5)
            )
            
            return result
            
        except Exception as e:
            # Record failure
            await collector.update_decision_outcome(
                decision_id=decision_id,
                success=False,
                execution_time_ms=0,
                reward=-1.0,
                error_message=str(e)
            )
            raise
    
    return wrapper


async def record_hub_decision(
    available_modules: List[str],
    selected_module: str,
    selection_probs: Dict[str, float],
    state: Dict[str, Any],
    reward: float,
    algorithm: str = "contextual_bandit"
) -> None:
    """
    Record a hub decision for metrics collection.
    
    This function should be called from hub_decisions.py after each decision.
    """
    collector = get_metrics_collector()
    
    # Record the selection
    decision_id = await collector.record_module_selection(
        available_modules=available_modules,
        selected_module=selected_module,
        selection_probabilities=selection_probs,
        task_context=state,
        algorithm=algorithm
    )
    
    # If we already know the outcome, update immediately
    if reward != 0:
        await collector.update_decision_outcome(
            decision_id=decision_id,
            success=reward > 0,
            execution_time_ms=state.get('execution_time_ms', 0),
            reward=reward
        )


async def record_pipeline_execution(
    pipeline_id: str,
    modules: List[str],
    results: List[Dict[str, Any]]
) -> None:
    """
    Record a complete pipeline execution.
    
    Args:
        pipeline_id: Unique identifier for the pipeline
        modules: List of modules in the pipeline
        results: List of execution results for each module
    """
    collector = get_metrics_collector()
    
    async with collector.track_pipeline(pipeline_id, modules) as pipeline:
        for module, result in zip(modules, results):
            await collector.record_module_execution(
                pipeline_id=pipeline_id,
                module_id=module,
                duration_ms=result.get('duration_ms', 0),
                success=result.get('success', False),
                reward=result.get('reward', 0)
            )


# Integration hooks for hub_decisions.py
def integrate_metrics_collection():
    """
    Call this function to integrate metrics collection into hub_decisions.
    
    This modifies the global agents to include metrics recording.
    """
    logger.info("Integrating RL metrics collection into hub decisions")
    
    # Import would be circular, so we do it here
    from claude_coms.rl import hub_decisions
    
    # Wrap the decision functions
    original_select = hub_decisions.select_module_for_task
    
    @functools.wraps(original_select)
    async def wrapped_select(*args, **kwargs):
        result = await original_select(*args, **kwargs)
        # Record metrics after selection
        # Implementation depends on exact function signature
        return result
    
    # Replace the function
    hub_decisions.select_module_for_task = wrapped_select
    
    logger.info("Metrics collection integration complete")


if __name__ == "__main__":
    # Example integration
    print("RL Metrics Integration Module")
    print("Use integrate_metrics_collection() to enable metrics")
