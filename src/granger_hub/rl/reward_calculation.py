"""
Reward calculation functions for Hub RL learning.

Defines how to calculate rewards for different Hub decisions to guide learning.
Pure functions following CLAUDE.md standards.
"""

from typing import Dict, Any, Optional
import numpy as np
from loguru import logger


# Reward weights for different objectives
REWARD_WEIGHTS = {
    "success": 10.0,      # Task completed successfully
    "speed": 3.0,         # Fast execution
    "efficiency": 2.0,    # Resource usage
    "reliability": 5.0,   # No errors
    "quality": 4.0        # Result quality
}

# Penalty weights
PENALTY_WEIGHTS = {
    "failure": -20.0,     # Task failed
    "timeout": -10.0,     # Execution timeout
    "error": -5.0,        # Non-fatal error
    "retry": -2.0,        # Had to retry
    "inefficient": -1.0   # Used too many resources
}

# Performance baselines
PERFORMANCE_BASELINES = {
    "response_time_ms": 1000,    # Target 1 second
    "memory_usage_mb": 500,      # Target 500MB
    "cpu_usage_percent": 70,     # Target 70% CPU
    "retry_count": 0,            # Target no retries
    "error_rate": 0.01           # Target 1% error rate
}


def calculate_reward(
    decision_type: str,
    action: Any,
    outcome: Dict[str, Any]
) -> float:
    """
    Calculate reward based on decision type and outcome.
    
    Args:
        decision_type: Type of decision (module_selection, pipeline, resource, error)
        action: The action taken
        outcome: Result of the action
        
    Returns:
        Reward value (positive for good, negative for bad)
        
    Example:
        >>> outcome = {"success": True, "response_time_ms": 800}
        >>> reward = calculate_reward("module_selection", "arxiv-mcp-server", outcome)
        >>> assert reward > 0  # Successful outcome should have positive reward
    """
    if decision_type == "module_selection":
        return calculate_module_selection_reward(action, outcome)
    elif decision_type == "pipeline_optimization":
        return calculate_pipeline_reward(action, outcome)
    elif decision_type == "resource_allocation":
        return calculate_resource_reward(action, outcome)
    elif decision_type == "error_recovery":
        return calculate_error_recovery_reward(action, outcome)
    else:
        logger.warning(f"Unknown decision type: {decision_type}")
        return 0.0


def calculate_module_selection_reward(
    selected_module: str,
    outcome: Dict[str, Any]
) -> float:
    """
    Calculate reward for module selection decision.
    
    Args:
        selected_module: Name of the module that was selected
        outcome: Execution outcome with success, timing, quality metrics
        
    Returns:
        Reward value
        
    Example:
        >>> outcome = {
        ...     "success": True,
        ...     "response_time_ms": 500,
        ...     "quality_score": 0.9,
        ...     "resource_usage": {"cpu_percent": 50, "memory_mb": 300}
        ... }
        >>> reward = calculate_module_selection_reward("marker", outcome)
        >>> assert reward > 10  # Good outcome should have high reward
    """
    reward = 0.0
    
    # Success is most important
    if outcome.get("success", False):
        reward += REWARD_WEIGHTS["success"]
        
        # Speed bonus
        response_time = outcome.get("response_time_ms", 1000)
        if response_time < PERFORMANCE_BASELINES["response_time_ms"]:
            speed_bonus = (PERFORMANCE_BASELINES["response_time_ms"] - response_time) / PERFORMANCE_BASELINES["response_time_ms"]
            reward += REWARD_WEIGHTS["speed"] * speed_bonus
        
        # Quality bonus
        quality_score = outcome.get("quality_score", 0.0)
        if quality_score > 0:
            reward += REWARD_WEIGHTS["quality"] * quality_score
            
    else:
        # Failure penalty
        reward += PENALTY_WEIGHTS["failure"]
        
        # Additional penalties
        if outcome.get("timeout", False):
            reward += PENALTY_WEIGHTS["timeout"]
        if outcome.get("error", False):
            reward += PENALTY_WEIGHTS["error"]
    
    # Efficiency considerations
    resource_usage = outcome.get("resource_usage", {})
    efficiency_score = calculate_efficiency_score(resource_usage)
    reward += REWARD_WEIGHTS["efficiency"] * efficiency_score
    
    # Retry penalty
    retry_count = outcome.get("retry_count", 0)
    if retry_count > 0:
        reward += PENALTY_WEIGHTS["retry"] * retry_count
    
    return reward


def calculate_pipeline_reward(
    strategy: Dict[str, Any],
    outcome: Dict[str, Any]
) -> float:
    """
    Calculate reward for pipeline optimization decision.
    
    Args:
        strategy: Execution strategy used (mode, timeouts, etc.)
        outcome: Pipeline execution results
        
    Returns:
        Reward value
    """
    reward = 0.0
    
    # Completion reward
    completed_steps = outcome.get("completed_steps", 0)
    total_steps = outcome.get("total_steps", 1)
    completion_ratio = completed_steps / total_steps if total_steps > 0 else 0
    
    if completion_ratio == 1.0:
        reward += REWARD_WEIGHTS["success"]
    else:
        # Partial credit
        reward += REWARD_WEIGHTS["success"] * completion_ratio * 0.5
    
    # Parallel execution bonus
    if strategy.get("mode") == "parallel" and outcome.get("parallel_speedup", 1.0) > 1.0:
        speedup = outcome.get("parallel_speedup", 1.0)
        reward += REWARD_WEIGHTS["speed"] * np.log(speedup)
    
    # Reliability bonus
    if not outcome.get("errors", []):
        reward += REWARD_WEIGHTS["reliability"]
    else:
        error_count = len(outcome.get("errors", []))
        reward += PENALTY_WEIGHTS["error"] * error_count
    
    # Memory efficiency for streaming/lazy modes
    if strategy.get("mode") in ["streaming", "lazy"]:
        memory_saved = outcome.get("memory_saved_percent", 0)
        reward += REWARD_WEIGHTS["efficiency"] * (memory_saved / 100.0)
    
    # Timeout penalty
    if outcome.get("timeout", False):
        reward += PENALTY_WEIGHTS["timeout"]
        
    return reward


def calculate_resource_reward(
    timeout_selection: str,
    outcome: Dict[str, Any]
) -> float:
    """
    Calculate reward for resource allocation decision.
    
    Args:
        timeout_selection: Selected timeout (e.g., "timeout_60s")
        outcome: Execution results with timing
        
    Returns:
        Reward value
    """
    reward = 0.0
    
    # Parse timeout value
    timeout_ms = int(timeout_selection.split("_")[1].replace("s", "")) * 1000
    actual_time = outcome.get("execution_time_ms", 0)
    
    # Success within timeout
    if outcome.get("success", False) and actual_time < timeout_ms:
        reward += REWARD_WEIGHTS["success"]
        
        # Efficiency bonus - good prediction
        efficiency_ratio = actual_time / timeout_ms if timeout_ms > 0 else 0
        if 0.5 < efficiency_ratio < 0.9:
            reward += REWARD_WEIGHTS["efficiency"] * (1 - abs(0.7 - efficiency_ratio))
        elif efficiency_ratio > 0.9:
            # Too close for comfort
            reward -= 1.0
    
    # Timeout occurred
    elif actual_time >= timeout_ms:
        reward += PENALTY_WEIGHTS["timeout"]
        
        # Bad prediction penalty
        if outcome.get("would_have_succeeded", False):
            reward += PENALTY_WEIGHTS["inefficient"] * 2
    
    return reward


def calculate_error_recovery_reward(
    recovery_strategy: Dict[str, Any],
    outcome: Dict[str, Any]
) -> float:
    """
    Calculate reward for error recovery decision.
    
    Args:
        recovery_strategy: Recovery approach taken
        outcome: Recovery results
        
    Returns:
        Reward value
    """
    reward = 0.0
    
    # Recovery succeeded
    if outcome.get("recovered", False):
        reward += REWARD_WEIGHTS["reliability"]
        
        # Fast recovery bonus
        recovery_time = outcome.get("recovery_time_ms", 1000)
        if recovery_time < 5000:  # Under 5 seconds
            reward += REWARD_WEIGHTS["speed"] * (5000 - recovery_time) / 5000
        
        # Minimal retries bonus
        retry_count = outcome.get("retry_count", 0)
        max_attempts = recovery_strategy.get("max_attempts", 3)
        if retry_count <= max_attempts:
            reward += REWARD_WEIGHTS["efficiency"] * (1 - retry_count / 5)
    
    # Recovery failed
    else:
        reward += PENALTY_WEIGHTS["failure"] * 0.5  # Less severe
        
        # Wasted resources
        wasted_time = outcome.get("wasted_time_ms", 0)
        reward += PENALTY_WEIGHTS["inefficient"] * (wasted_time / 10000)
    
    return reward


def calculate_efficiency_score(resource_usage: Dict[str, Any]) -> float:
    """
    Calculate efficiency score from resource usage metrics.
    
    Args:
        resource_usage: Dict with cpu_percent, memory_mb, etc.
        
    Returns:
        Efficiency score between 0 and 1
    """
    scores = []
    
    # CPU efficiency
    cpu_usage = resource_usage.get("cpu_percent", 50)
    cpu_baseline = PERFORMANCE_BASELINES["cpu_usage_percent"]
    if cpu_usage < cpu_baseline:
        scores.append(1.0 - (cpu_usage / cpu_baseline))
    else:
        scores.append(max(0, 1.0 - (cpu_usage - cpu_baseline) / 30))
    
    # Memory efficiency
    memory_usage = resource_usage.get("memory_mb", 300)
    memory_baseline = PERFORMANCE_BASELINES["memory_usage_mb"]
    if memory_usage < memory_baseline:
        scores.append(1.0 - (memory_usage / memory_baseline))
    else:
        scores.append(max(0, 1.0 - (memory_usage - memory_baseline) / 500))
    
    # Network efficiency
    if "network_mb" in resource_usage:
        network_usage = resource_usage["network_mb"]
        scores.append(max(0, 1.0 - network_usage / 10))
    
    return np.mean(scores) if scores else 0.5


def get_reward_summary(rewards_history: list) -> Dict[str, Any]:
    """
    Get summary statistics of rewards for analysis.
    
    Args:
        rewards_history: List of reward values
        
    Returns:
        Summary statistics dict
    """
    if not rewards_history:
        return {
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "positive_ratio": 0.0,
            "total_samples": 0
        }
        
    rewards_array = np.array(rewards_history)
    
    return {
        "mean": float(np.mean(rewards_array)),
        "std": float(np.std(rewards_array)),
        "min": float(np.min(rewards_array)),
        "max": float(np.max(rewards_array)),
        "positive_ratio": float(np.sum(rewards_array > 0) / len(rewards_array)),
        "total_samples": len(rewards_array)
    }


# Validation and testing
if __name__ == "__main__":
    logger.info("Testing reward calculation functions")
    
    # Test module selection reward - success case
    good_outcome = {
        "success": True,
        "response_time_ms": 500,
        "quality_score": 0.9,
        "resource_usage": {"cpu_percent": 50, "memory_mb": 300},
        "retry_count": 0
    }
    
    reward = calculate_module_selection_reward("arxiv-mcp-server", good_outcome)
    logger.info(f"Good outcome reward: {reward:.2f}")
    assert reward > 10, f"Expected reward > 10, got {reward}"
    
    # Test module selection reward - failure case
    bad_outcome = {
        "success": False,
        "timeout": True,
        "error": True,
        "retry_count": 3
    }
    
    reward = calculate_module_selection_reward("slow-module", bad_outcome)
    logger.info(f"Bad outcome reward: {reward:.2f}")
    assert reward < -20, f"Expected reward < -20, got {reward}"
    
    # Test pipeline reward
    pipeline_outcome = {
        "completed_steps": 5,
        "total_steps": 5,
        "parallel_speedup": 2.5,
        "errors": [],
        "timeout": False
    }
    
    strategy = {"mode": "parallel", "max_concurrent": 3}
    reward = calculate_pipeline_reward(strategy, pipeline_outcome)
    logger.info(f"Pipeline reward: {reward:.2f}")
    assert reward > 15, f"Expected reward > 15, got {reward}"
    
    # Test resource allocation reward
    resource_outcome = {
        "success": True,
        "execution_time_ms": 45000  # 45 seconds
    }
    
    reward = calculate_resource_reward("timeout_60s", resource_outcome)
    logger.info(f"Resource allocation reward: {reward:.2f}")
    assert reward > 10, f"Expected reward > 10, got {reward}"
    
    # Test reward summary
    rewards_history = [15.5, -10.2, 22.3, 18.1, -5.5, 30.0]
    summary = get_reward_summary(rewards_history)
    logger.info(f"Reward summary: {summary}")
    assert summary["mean"] > 0, "Average reward should be positive"
    assert summary["positive_ratio"] > 0.5, "Most rewards should be positive"
    
    logger.success("✅ All reward calculation tests passed!")
