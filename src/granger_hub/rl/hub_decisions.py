"""
Hub decision-making using RL Commons for intelligent routing.
Module: hub_decisions.py
Description: Functions for hub decisions operations

This module integrates rl_commons to provide intelligent decision-making
for the ModuleCommunicator hub. It uses real RL algorithms, not mocks.
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from datetime import datetime
import json

# Import rl_commons components
try:
    from rl_commons import (
        ContextualBandit,
        DQNAgent,
        PPOAgent,
        RLState,
        RLAction,
        RLReward,
        ReplayBuffer
    )
    from rl_commons.core.replay_buffer import Experience
except ImportError as e:
    raise ImportError(
        "rl_commons not installed. Please install with: "
        "pip install git+https://github.com/grahama1970/rl_commons.git@master"
    ) from e

from granger_hub.rl.state_extraction import (
    extract_task_state,
    extract_pipeline_state,
    extract_error_state,
    extract_timeout_context
)
from granger_hub.rl.reward_calculation import (
    calculate_module_selection_reward,
    calculate_pipeline_reward,
    calculate_resource_reward
)

# Global agents for different decision types
_module_selector: Optional[ContextualBandit] = None
_pipeline_optimizer: Optional[DQNAgent] = None
_resource_allocator: Optional[PPOAgent] = None
_error_handler: Optional[DQNAgent] = None
_module_to_index: Dict[str, int] = {}


def initialize_rl_agents(modules: List[str], reset: bool = False) -> None:
    """
    Initialize RL agents for different decision types.
    
    Args:
        modules: List of available module names
        reset: Whether to reset existing agents
    """
    global _module_selector, _pipeline_optimizer, _resource_allocator
    global _error_handler, _module_to_index
    
    # Create module index mapping
    _module_to_index = {module: i for i, module in enumerate(modules)}
    
    # Initialize module selector (contextual bandit)
    if reset or _module_selector is None:
        _module_selector = ContextualBandit(
            name="module_selector",
            n_arms=len(modules),
            n_features=20  # Task state dimension (from extract_task_state)
        )
    
    # Initialize pipeline optimizer (DQN)
    if reset or _pipeline_optimizer is None:
        _pipeline_optimizer = DQNAgent(
            name="pipeline_optimizer",
            state_dim=15,  # Pipeline state dimension
            action_dim=len(modules) * 3,  # Actions: add/remove/reorder modules
            learning_rate=0.001,
            buffer_size=10000
        )
    
    # Initialize resource allocator (PPO for continuous actions)
    if reset or _resource_allocator is None:
        _resource_allocator = PPOAgent(
            name="resource_allocator",
            state_dim=12,  # Resource state dimension
            action_dim=4,  # CPU%, Memory%, Timeout, Priority
            continuous=True,
            learning_rate=0.0003
        )
    
    # Initialize error handler (DQN)
    if reset or _error_handler is None:
        _error_handler = DQNAgent(
            name="error_handler",
            state_dim=20,  # Error context dimension
            action_dim=5,  # retry, fallback, skip, escalate, adapt
            learning_rate=0.001,
            buffer_size=5000
        )


def select_module_with_rl(
    task: Dict[str, Any],
    available_modules: List[str],
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Select the best module for a task using reinforcement learning.
    
    Args:
        task: Task description with type, requirements, etc.
        available_modules: List of modules that can handle the task
        context: Additional context (performance metrics, history)
    
    Returns:
        Selected module name
    """
    # Ensure agents are initialized
    if _module_selector is None:
        initialize_rl_agents(available_modules)
    
    # Extract state from task
    # Merge context into task if provided
    if context:
        task_with_context = {**task, **context}
    else:
        task_with_context = task
    state = extract_task_state(task_with_context)
    
    # Convert state to RLState
    rl_state = RLState(features=state)
    
    # Select module using contextual bandit
    action = _module_selector.select_action(rl_state)
    
    # Extract action index from RLAction
    action_index = action.action_id
    
    # Convert action index back to module name
    index_to_module = {v: k for k, v in _module_to_index.items()}
    selected_module = index_to_module.get(action_index, available_modules[0])
    
    # Log the decision for later reward update
    _log_decision(
        decision_type="module_selection",
        state=state,
        action=action_index,
        selected_module=selected_module,
        task=task,
        context=context
    )
    
    return selected_module


def optimize_pipeline_with_rl(
    pipeline: List[str],
    requirements: Dict[str, Any],
    performance_history: Optional[List[Dict[str, Any]]] = None
) -> List[str]:
    """
    Optimize a pipeline of modules using reinforcement learning.
    
    Args:
        pipeline: Current pipeline of module names
        requirements: Performance requirements and constraints
        performance_history: Historical performance data
    
    Returns:
        Optimized pipeline
    """
    # Ensure agents are initialized
    if _pipeline_optimizer is None:
        initialize_rl_agents(pipeline)
    
    # Extract state from pipeline
    # Create task dict from requirements
    task = {
        'type': 'pipeline_optimization',
        'requirements': requirements,
        'history': performance_history
    }
    state = extract_pipeline_state(pipeline, task, requirements)
    
    # Convert to RLState
    rl_state = RLState(features=state)
    
    # Get optimization action from DQN
    action = _pipeline_optimizer.select_action(rl_state)
    
    # Convert action to pipeline modification
    optimized_pipeline = _apply_pipeline_action(pipeline, action)
    
    # Log the decision
    _log_decision(
        decision_type="pipeline_optimization",
        state=state,
        action=action,
        pipeline=pipeline,
        optimized=optimized_pipeline,
        requirements=requirements
    )
    
    return optimized_pipeline


def allocate_resources_with_rl(
    module: str,
    task: Dict[str, Any],
    current_resources: Dict[str, float]
) -> Dict[str, float]:
    """
    Allocate resources for a module using reinforcement learning.
    
    Args:
        module: Module name
        task: Task being processed
        current_resources: Current resource allocation
    
    Returns:
        Optimized resource allocation
    """
    # Ensure agents are initialized
    if _resource_allocator is None:
        initialize_rl_agents([module])
    
    # Create state vector
    task_state = extract_task_state(task)
    state = np.concatenate([
        task_state,
        [current_resources.get('cpu', 0.5),
         current_resources.get('memory', 0.5)]
    ])
    
    # Convert to RLState
    rl_state = RLState(features=state)
    
    # Get resource allocation from PPO
    action = _resource_allocator.select_action(rl_state)
    
    # PPO returns numpy array for continuous actions
    if isinstance(action, (int, np.integer)):
        # Discrete action space - shouldn't happen for PPO continuous
        action = np.array([0.5, 0.5, 0.5, 0.5])
    
    # Convert continuous action to resource allocation
    allocation = {
        'cpu': float(np.clip(action[0], 0.1, 1.0)),
        'memory': float(np.clip(action[1], 0.1, 1.0)),
        'timeout': float(np.clip(action[2] * 60, 10, 300)),  # 10s to 5min
        'priority': float(np.clip(action[3], 0, 1))
    }
    
    # Log the decision
    _log_decision(
        decision_type="resource_allocation",
        state=state.tolist(),
        action=action.tolist() if hasattr(action, 'tolist') else list(action),
        module=module,
        allocation=allocation
    )
    
    return allocation


def handle_error_with_rl(
    error: Exception,
    module: str,
    task: Dict[str, Any],
    attempts: int = 0
) -> str:
    """
    Decide how to handle an error using reinforcement learning.
    
    Args:
        error: The exception that occurred
        module: Module that failed
        task: Task being processed
        attempts: Number of previous attempts
    
    Returns:
        Action to take: 'retry', 'fallback', 'skip', 'escalate', 'adapt'
    """
    # Ensure agents are initialized
    if _error_handler is None:
        initialize_rl_agents([module])
    
    # Extract error context
    error_context = {
        'module': module,
        'task': task,
        'attempts': attempts,
        'error_type': type(error).__name__,
        'error_message': str(error)
    }
    state = extract_error_state(error, error_context)
    
    # Convert to RLState
    rl_state = RLState(features=state)
    
    # Get error handling action from DQN
    action_idx = _error_handler.select_action(rl_state)
    
    # Map action index to strategy
    actions = ['retry', 'fallback', 'skip', 'escalate', 'adapt']
    action = actions[action_idx % len(actions)]  # Ensure valid index
    
    # Log the decision
    _log_decision(
        decision_type="error_handling",
        state=state.tolist(),
        action=action,
        action_idx=action_idx,
        error=str(error),
        module=module,
        attempts=attempts
    )
    
    return action


def record_decision_outcome(
    decision_id: str,
    outcome: Dict[str, Any],
    reward: Optional[float] = None
) -> None:
    """
    Record the outcome of a decision for learning.
    
    Args:
        decision_id: ID of the decision (from logging)
        outcome: Outcome metrics (success, latency, quality, etc.)
        reward: Optional pre-calculated reward
    """
    # Load the decision from log
    decision = _load_decision(decision_id)
    if not decision:
        return
    
    # Calculate reward if not provided
    if reward is None:
        if decision['decision_type'] == 'module_selection':
            reward = calculate_module_selection_reward(outcome)
        elif decision['decision_type'] == 'pipeline_optimization':
            reward = calculate_pipeline_reward(outcome)
        elif decision['decision_type'] == 'resource_allocation':
            reward = calculate_resource_reward(outcome)
        else:  # error_handling
            reward = 1.0 if outcome.get('success') else -1.0
    
    # Update the appropriate agent
    if decision['decision_type'] == 'module_selection' and _module_selector:
        # Create RLState and RLReward
        state = RLState(features=np.array(decision['state']))
        rl_reward = RLReward(value=reward)
        
        # Create RLAction from the decision
        rl_action = RLAction(action_type="discrete", action_id=decision['action'])
        
        # For bandits, next_state is same as current state (not used)
        next_state = state
        
        # Update contextual bandit
        _module_selector.update(state, rl_action, rl_reward, next_state)
        
    elif decision['decision_type'] == 'pipeline_optimization' and _pipeline_optimizer:
        # For DQN, we need the next state
        task = {
            'type': 'pipeline_optimization',
            'requirements': decision.get('requirements', {}),
            'outcome': outcome
        }
        next_state_features = extract_pipeline_state(
            outcome.get('final_pipeline', decision.get('optimized', [])),
            task,
            decision.get('requirements', {})
        )
        
        # Create experience for DQN
        exp = Experience(
            state=np.array(decision['state']),
            action=decision['action'],
            reward=reward,
            next_state=next_state_features,
            done=outcome.get('done', False)
        )
        
        # Store experience (DQN will train from replay buffer)
        _pipeline_optimizer.store_experience(exp)
        
    elif decision['decision_type'] == 'resource_allocation' and _resource_allocator:
        # PPO stores trajectory data
        state = RLState(features=np.array(decision['state']))
        action = RLAction(value=np.array(decision['action']))
        rl_reward = RLReward(value=reward)
        
        # Store for later training
        _resource_allocator.store_transition(state, action, rl_reward)
        
    elif decision['decision_type'] == 'error_handling' and _error_handler:
        # DQN update with terminal state
        exp = Experience(
            state=np.array(decision['state']),
            action=decision.get('action_idx', 0),  # Use action index
            reward=reward,
            next_state=np.zeros_like(decision['state']),  # Terminal
            done=True
        )
        
        _error_handler.store_experience(exp)


def _apply_pipeline_action(pipeline: List[str], action: int) -> List[str]:
    """Apply a discrete action to modify a pipeline."""
    if not pipeline:
        return pipeline
    
    # Action space: add, remove, swap positions
    num_modules = len(pipeline)
    action_type = action // num_modules
    module_idx = action % num_modules
    
    optimized = pipeline.copy()
    
    if action_type == 0 and module_idx < len(optimized) - 1:
        # Swap with next module
        optimized[module_idx], optimized[module_idx + 1] = (
            optimized[module_idx + 1], optimized[module_idx]
        )
    elif action_type == 1 and len(optimized) > 1:
        # Remove module (if not the only one)
        optimized.pop(module_idx)
    elif action_type == 2:
        # Duplicate module at position
        optimized.insert(module_idx, optimized[module_idx])
    
    return optimized


# Decision logging for experience replay
_decision_log: List[Dict[str, Any]] = []


def _log_decision(**kwargs) -> str:
    """Log a decision for later reward update."""
    decision_id = f"{kwargs['decision_type']}_{datetime.now().timestamp()}"
    kwargs['decision_id'] = decision_id
    kwargs['timestamp'] = datetime.now().isoformat()
    _decision_log.append(kwargs)
    
    # Keep only last 1000 decisions in memory
    if len(_decision_log) > 1000:
        _decision_log.pop(0)
    
    return decision_id


def _load_decision(decision_id: str) -> Optional[Dict[str, Any]]:
    """Load a decision from the log."""
    for decision in reversed(_decision_log):
        if decision.get('decision_id') == decision_id:
            return decision
    return None


# Module validation
if __name__ == "__main__":
    # Test with real module selection
    test_modules = ["marker", "arangodb", "claude_max_proxy"]
    initialize_rl_agents(test_modules)
    
    test_task = {
        "type": "extract",
        "input_type": "pdf",
        "requirements": {"quality": "high", "speed": "medium"}
    }
    
    selected = select_module_with_rl(test_task, test_modules)
    print(f" Selected module: {selected}")
    
    # Test pipeline optimization
    test_pipeline = ["marker", "arangodb"]
    optimized = optimize_pipeline_with_rl(
        test_pipeline,
        {"max_latency": 500, "reliability": 0.95}
    )
    print(f" Optimized pipeline: {optimized}")
    
    # Test resource allocation
    resources = allocate_resources_with_rl(
        "marker",
        test_task,
        {"cpu": 0.5, "memory": 0.5}
    )
    print(f" Resource allocation: {resources}")
    
    # Test error handling
    test_error = ValueError("Processing failed")
    action = handle_error_with_rl(test_error, "marker", test_task, 1)
    print(f" Error handling action: {action}")
    
    print("\n Hub decisions module validated successfully!")