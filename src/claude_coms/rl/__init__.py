# claude_coms/rl/__init__.py
"""
Reinforcement Learning components for Claude Module Communicator.

This package implements DeepRetrieval-style RL optimization for:
- Communication route optimization
- Schema adaptation learning  
- Module selection policies

Uses local Ollama server with qwen3:30b-a3b-q8_0 model for better performance.
"""

from .rewards import CommunicationReward
from .ollama_integration import OllamaClient, OllamaConfig, get_ollama_client, get_model_capabilities

# Only import other components if available
try:
    from .episodes import CommunicationEpisode
    from .graph_integration import GraphRLIntegration
    EPISODES_AVAILABLE = True
except ImportError:
    EPISODES_AVAILABLE = False
    CommunicationEpisode = None
    GraphRLIntegration = None

# Only import verl components if available
try:
    from .verl_trainer import (
        ModuleCommunicationRewardModel,
        ModuleCommunicationTrainer
    )
    VERL_AVAILABLE = True
except ImportError:
    VERL_AVAILABLE = False
    ModuleCommunicationRewardModel = None
    ModuleCommunicationTrainer = None

__all__ = [
    'CommunicationReward',
    'CommunicationEpisode', 
    'GraphRLIntegration',
    'ModuleCommunicationRewardModel',
    'ModuleCommunicationTrainer',
    'OllamaClient',
    'OllamaConfig',
    'get_ollama_client',
    'get_model_capabilities',
    'VERL_AVAILABLE',
    'EPISODES_AVAILABLE'
]
