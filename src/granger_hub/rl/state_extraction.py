"""
State extraction functions for RL decision making.
Module: state_extraction.py
Description: Functions for state extraction operations

Converts Hub contexts (tasks, pipelines, errors) into numerical state vectors
that RL agents can use for decision making.

No classes, pure functions following CLAUDE.md standards.
"""

import numpy as np
from typing import Dict, Any, List, Optional
from loguru import logger


# Module capability encodings - which modules can do what
MODULE_CAPABILITIES = {
    "arxiv-mcp-server": [1, 0, 0, 0, 0, 1, 0, 0, 1],  # search, retrieve, compare
    "marker": [0, 0, 1, 1, 0, 0, 0, 0, 0],  # extract, transform
    "arangodb": [0, 0, 0, 0, 1, 1, 0, 0, 0],  # store, retrieve
    "sparta": [1, 1, 1, 0, 0, 0, 1, 0, 0],  # search, analyze, extract, validate
    "youtube_transcripts": [1, 0, 1, 0, 0, 1, 0, 0, 0],  # search, extract, retrieve
    "claude_max_proxy": [0, 1, 0, 0, 0, 0, 0, 1, 0],  # analyze, generate
    "mcp-screenshot": [0, 0, 1, 0, 0, 0, 0, 0, 0],  # extract
    "unsloth": [0, 0, 0, 1, 0, 0, 0, 1, 0],  # transform, generate
    "test-reporter": [0, 0, 0, 0, 0, 0, 1, 1, 0]  # validate, generate
}

# Task type mappings
TASK_TYPES = {
    "search": 0,
    "analyze": 1,
    "extract": 2,
    "transform": 3,
    "store": 4,
    "retrieve": 5,
    "validate": 6,
    "generate": 7,
    "compare": 8,
    "unknown": 9
}


def extract_task_state(task: Dict[str, Any]) -> np.ndarray:
    """
    Extract state vector from task description for RL agents.
    
    Args:
        task: Task dictionary with type, description, data_size, priority, etc.
        
    Returns:
        20-dimensional numpy array representing task state
        
    Example:
        >>> task = {
        ...     "type": "search",
        ...     "description": "Find papers on quantum computing",
        ...     "data_size_mb": 5.2,
        ...     "priority": "high"
        ... }
        >>> state = extract_task_state(task)
        >>> assert state.shape == (20,)
    """
    state = []
    
    # Task type encoding (10 dims) - one-hot
    task_type = task.get("type", "unknown").lower()
    task_vector = [0.0] * len(TASK_TYPES)
    
    # Find matching task type
    for key, idx in TASK_TYPES.items():
        if key in task_type:
            task_vector[idx] = 1.0
            break
    else:
        task_vector[TASK_TYPES["unknown"]] = 1.0
    
    state.extend(task_vector)
    
    # Data size features (3 dims)
    data_size = float(task.get("data_size_mb", 1.0))
    state.append(np.log1p(data_size) / 10.0)  # Log scale normalized
    state.append(1.0 if data_size > 10 else 0.0)  # Large data flag
    state.append(1.0 if data_size > 100 else 0.0)  # Very large data flag
    
    # Priority and urgency (2 dims)
    priority_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
    priority = task.get("priority", "medium").lower()
    state.append(priority_map.get(priority, 0.5))
    state.append(1.0 if task.get("real_time", False) else 0.0)
    
    # Complexity indicators (3 dims)
    description = task.get("description", "").lower()
    state.append(1.0 if "complex" in description or "advanced" in description else 0.0)
    state.append(1.0 if "multi" in description or "multiple" in description else 0.0)
    state.append(min(1.0, len(task.get("requirements", [])) / 10.0))
    
    # Domain indicators (2 dims)
    state.append(1.0 if "security" in description or "cyber" in description else 0.0)
    state.append(1.0 if "research" in description or "paper" in description else 0.0)
    
    return np.array(state, dtype=np.float32)


def extract_pipeline_state(
    modules: List[str],
    task: Dict[str, Any],
    constraints: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Extract state for pipeline optimization decisions.
    
    Args:
        modules: List of module names in pipeline
        task: Task information
        constraints: Execution constraints (time, memory, etc.)
        
    Returns:
        30-dimensional state vector for pipeline decisions
        
    Example:
        >>> modules = ["arxiv-mcp-server", "marker", "arangodb"]
        >>> task = {"type": "research", "data_size_mb": 10}
        >>> state = extract_pipeline_state(modules, task)
        >>> assert state.shape == (30,)
    """
    state = []
    constraints = constraints or {}
    
    # Pipeline structure (5 dims)
    state.append(len(modules) / 10.0)  # Normalized module count
    state.append(1.0 if len(modules) > 3 else 0.0)  # Complex pipeline
    state.append(1.0 if len(modules) > 5 else 0.0)  # Very complex
    state.append(len(set(modules)) / len(modules) if modules else 1.0)  # Uniqueness
    state.append(1.0 if len(modules) != len(set(modules)) else 0.0)  # Has duplicates
    
    # Module capabilities aggregate (9 dims)
    capability_matrix = np.zeros(9)
    for module in modules:
        if module in MODULE_CAPABILITIES:
            capability_matrix += np.array(MODULE_CAPABILITIES[module])
    
    # Normalize by module count
    if modules:
        capability_matrix = np.clip(capability_matrix / len(modules), 0, 1)
    state.extend(capability_matrix.tolist())
    
    # Task features (5 dims) - subset of task state
    task_state = extract_task_state(task)
    state.extend(task_state[:5].tolist())
    
    # Constraints (5 dims)
    state.append(constraints.get("max_time_seconds", 300) / 300.0)
    state.append(1.0 if constraints.get("parallel_allowed", True) else 0.0)
    state.append(constraints.get("max_memory_mb", 1000) / 1000.0)
    state.append(1.0 if constraints.get("streaming_required", False) else 0.0)
    state.append(min(1.0, constraints.get("max_cost", 1.0)))
    
    # Resource estimates (6 dims)
    resource_estimates = estimate_pipeline_resources(modules, task)
    state.extend(resource_estimates)
    
    return np.array(state, dtype=np.float32)


def extract_error_state(
    error: Exception,
    context: Dict[str, Any]
) -> np.ndarray:
    """
    Extract state from error context for recovery decisions.
    
    Args:
        error: The exception that occurred
        context: Error context with module, retry_count, etc.
        
    Returns:
        15-dimensional error state vector
        
    Example:
        >>> error = TimeoutError("Module timeout")
        >>> context = {"module": "arxiv-mcp-server", "retry_count": 1}
        >>> state = extract_error_state(error, context)
        >>> assert state.shape == (15,)
    """
    state = []
    
    # Error type encoding (5 dims)
    error_types = {
        "timeout": 0,
        "connection": 1,
        "validation": 2,
        "resource": 3,
        "unknown": 4
    }
    
    error_str = str(error).lower()
    error_vector = [0.0] * len(error_types)
    
    # Match error type
    for error_type, idx in error_types.items():
        if error_type in error_str or error_type in type(error).__name__.lower():
            error_vector[idx] = 1.0
            break
    else:
        error_vector[error_types["unknown"]] = 1.0
    
    state.extend(error_vector)
    
    # Module characteristics (5 dims)
    failed_module = context.get("module", "").lower()
    module_vector = [0.0] * 5
    
    if "arxiv" in failed_module or "youtube" in failed_module:
        module_vector[0] = 1.0  # External service
    if "llm" in failed_module or "claude" in failed_module:
        module_vector[1] = 1.0  # LLM service
    if "db" in failed_module or "arango" in failed_module:
        module_vector[2] = 1.0  # Database
    if "marker" in failed_module or "screenshot" in failed_module:
        module_vector[3] = 1.0  # Processing service
    if not any(module_vector):
        module_vector[4] = 1.0  # Unknown
        
    state.extend(module_vector)
    
    # Context features (5 dims)
    state.append(min(1.0, context.get("retry_count", 0) / 5.0))
    state.append(min(1.0, context.get("time_elapsed", 0) / 300.0))
    state.append(1.0 if context.get("critical_path", False) else 0.0)
    state.append(min(1.0, context.get("queue_depth", 0) / 10.0))
    state.append(1.0 if context.get("partial_success", False) else 0.0)
    
    return np.array(state, dtype=np.float32)


def extract_timeout_context(
    task: Dict[str, Any],
    modules: List[str]
) -> np.ndarray:
    """
    Extract context for timeout allocation decisions.
    
    Args:
        task: Task information
        modules: Modules involved in the task
        
    Returns:
        15-dimensional timeout context vector
    """
    state = []
    
    # Task complexity (3 dims)
    task_state = extract_task_state(task)
    state.extend(task_state[15:18].tolist())  # Complexity indicators
    
    # Module characteristics (4 dims)
    slow_modules = {"arxiv-mcp-server", "youtube_transcripts", "claude_max_proxy"}
    fast_modules = {"arangodb", "test-reporter"}
    
    slow_count = sum(1 for m in modules if m in slow_modules)
    fast_count = sum(1 for m in modules if m in fast_modules)
    
    state.append(slow_count / len(modules) if modules else 0.0)
    state.append(fast_count / len(modules) if modules else 0.0)
    state.append(1.0 if any("llm" in m or "claude" in m for m in modules) else 0.0)
    state.append(1.0 if any("search" in m or "arxiv" in m for m in modules) else 0.0)
    
    # Data characteristics (4 dims)
    data_size = task.get("data_size_mb", 1.0)
    state.append(np.log1p(data_size) / 10.0)
    state.append(1.0 if task.get("batch_processing", False) else 0.0)
    state.append(min(1.0, task.get("expected_results", 10) / 100.0))
    state.append(1.0 if task.get("network_intensive", False) else 0.0)
    
    # Historical performance placeholders (4 dims)
    # In production, these would come from metrics
    state.extend([0.5, 0.5, 0.5, 0.5])
    
    return np.array(state, dtype=np.float32)


def estimate_pipeline_resources(
    modules: List[str],
    task: Dict[str, Any]
) -> List[float]:
    """
    Estimate resource needs for a pipeline.
    
    Returns 6 values: CPU, Memory, Network, Storage, Time, Cost (all 0-1)
    """
    # Base estimates per module
    module_resources = {
        "arxiv-mcp-server": [0.2, 0.3, 0.8, 0.1, 0.6, 0.1],
        "marker": [0.8, 0.6, 0.1, 0.3, 0.4, 0.2],
        "arangodb": [0.3, 0.5, 0.2, 0.8, 0.2, 0.3],
        "sparta": [0.4, 0.4, 0.6, 0.4, 0.5, 0.2],
        "youtube_transcripts": [0.2, 0.3, 0.9, 0.2, 0.7, 0.1],
        "claude_max_proxy": [0.5, 0.4, 0.7, 0.1, 0.8, 0.5],
        "mcp-screenshot": [0.6, 0.5, 0.1, 0.4, 0.3, 0.1],
        "unsloth": [0.9, 0.8, 0.2, 0.5, 0.9, 0.4],
        "test-reporter": [0.3, 0.3, 0.1, 0.3, 0.2, 0.1]
    }
    
    resources = [0.0] * 6
    
    # Aggregate resources
    for module in modules:
        if module in module_resources:
            for i, val in enumerate(module_resources[module]):
                resources[i] = min(1.0, resources[i] + val)
    
    # Scale by task complexity
    complexity_factor = 1.0 + (task.get("complexity", 0.5) - 0.5)
    resources = [min(1.0, r * complexity_factor) for r in resources]
    
    return resources


# Validation and testing
if __name__ == "__main__":
    logger.info("Testing state extraction functions")
    
    # Test task state extraction
    test_task = {
        "type": "search",
        "description": "Find research papers on quantum computing security",
        "data_size_mb": 15.5,
        "priority": "high",
        "real_time": False,
        "requirements": ["peer-reviewed", "recent", "citations"]
    }
    
    task_state = extract_task_state(test_task)
    logger.info(f"Task state shape: {task_state.shape}")
    logger.info(f"Task state: {task_state}")
    assert task_state.shape == (20,), f"Expected shape (20,), got {task_state.shape}"
    assert task_state[0] == 1.0, "Search task type should be encoded"
    assert task_state[13] == 0.8, "High priority should be 0.8"
    
    # Test pipeline state extraction
    test_modules = ["arxiv-mcp-server", "marker", "arangodb"]
    test_constraints = {
        "max_time_seconds": 120,
        "parallel_allowed": True,
        "max_memory_mb": 2000
    }
    
    pipeline_state = extract_pipeline_state(test_modules, test_task, test_constraints)
    logger.info(f"Pipeline state shape: {pipeline_state.shape}")
    assert pipeline_state.shape == (30,), f"Expected shape (30,), got {pipeline_state.shape}"
    
    # Test error state extraction
    test_error = TimeoutError("Module execution timeout")
    test_context = {
        "module": "arxiv-mcp-server",
        "retry_count": 2,
        "time_elapsed": 150,
        "critical_path": True
    }
    
    error_state = extract_error_state(test_error, test_context)
    logger.info(f"Error state shape: {error_state.shape}")
    assert error_state.shape == (15,), f"Expected shape (15,), got {error_state.shape}"
    assert error_state[0] == 1.0, "Timeout error should be encoded"
    
    # Test timeout context
    timeout_state = extract_timeout_context(test_task, test_modules)
    logger.info(f"Timeout state shape: {timeout_state.shape}")
    assert timeout_state.shape == (15,), f"Expected shape (15,), got {timeout_state.shape}"
    
    logger.success(" All state extraction tests passed!")
