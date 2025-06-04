"""
RL Integration for Claude Module Communicator

Provides functions for intelligent Hub routing using RL Commons.
No mocks, no classes unless needed for state, functional approach.
"""

from granger_hub.rl.state_extraction import (
    extract_task_state,
    extract_pipeline_state,
    extract_error_state,
    extract_timeout_context
)

from granger_hub.rl.reward_calculation import (
    calculate_reward,
    calculate_module_selection_reward,
    calculate_pipeline_reward,
    calculate_resource_reward
)

from granger_hub.rl.hub_decisions import (
    initialize_rl_agents,
    select_module_with_rl,
    optimize_pipeline_with_rl,
    allocate_resources_with_rl,
    handle_error_with_rl,
    record_decision_outcome
)

from granger_hub.rl.experience_collection import (
    initialize_experience_db,
    log_experience,
    load_experiences,
    train_agents_offline,
    get_experience_statistics
)

__all__ = [
    # State extraction
    'extract_task_state',
    'extract_pipeline_state', 
    'extract_error_state',
    'extract_timeout_context',
    
    # Reward calculation
    'calculate_reward',
    'calculate_module_selection_reward',
    'calculate_pipeline_reward',
    'calculate_resource_reward',
    
    # Hub decisions
    'initialize_rl_agents',
    'select_module_with_rl',
    'optimize_pipeline_with_rl',
    'allocate_resources_with_rl',
    'handle_error_with_rl',
    'record_decision_outcome',
    
    # Experience collection
    'initialize_experience_db',
    'log_experience',
    'load_experiences',
    'train_agents_offline',
    'get_experience_statistics'
]
