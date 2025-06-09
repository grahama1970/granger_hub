"""
Granger Hub - Dynamic inter-module communication framework.
Module: __init__.py
Description: Package initialization and exports

This package provides a framework for modules to dynamically discover and 
communicate with each other using Claude Code as an intelligent message broker.

Following the 3-layer architecture:
- core/: Business logic and core functionality
- cli/: Command-line interface
- mcp/: MCP integration
"""

# Import core functionality from the proper location
from .core.modules import (
    BaseModule,
    ModuleRegistry,
    ModuleInfo,
    DataProducerModule,
    DataProcessorModule,
    DataAnalyzerModule,
    OrchestratorModule
)

from .core.conversation import (
    ConversationMessage,
    ConversationState,
    ConversationModule,
    ConversationManager,
    ConversationProtocol,
    ConversationIntent,
    ConversationPhase,
    ConversationHandshake,
    ConversationResponse,
    ConversationCapable,
    SchemaProposal
)

__all__ = [
    # Core module classes
    "BaseModule",
    "ModuleRegistry",
    "ModuleInfo",
    
    # Example modules
    "DataProducerModule",
    "DataProcessorModule",
    "DataAnalyzerModule",
    "OrchestratorModule",
    
    # Conversation support
    "ConversationMessage",
    "ConversationState",
    "ConversationModule",
    "ConversationManager",
    "ConversationProtocol",
    "ConversationIntent",
    "ConversationPhase",
    "ConversationHandshake",
    "ConversationResponse",
    "ConversationCapable",
    "SchemaProposal"
]

__version__ = "0.1.0"

import time
from typing import Dict, Any, Optional

class PipelineStateManager:
    """Manages pipeline state and recovery"""
    
    def __init__(self):
        self.pipeline_states = {}
        self.recovery_strategies = {
            'retry': self._retry_recovery,
            'checkpoint': self._checkpoint_recovery,
            'rollback': self._rollback_recovery
        }
        
    def save_pipeline_state(self, pipeline_id: str, state: Dict[str, Any]):
        """Save current pipeline state"""
        self.pipeline_states[pipeline_id] = {
            'state': state,
            'timestamp': time.time(),
            'checkpoints': state.get('checkpoints', [])
        }
        
    def recover_pipeline(self, pipeline_id: str, strategy: str = 'checkpoint') -> Optional[Dict[str, Any]]:
        """Recover pipeline using specified strategy"""
        if pipeline_id not in self.pipeline_states:
            logger.error(f"No state found for pipeline {pipeline_id}")
            return None
            
        if strategy not in self.recovery_strategies:
            logger.error(f"Unknown recovery strategy: {strategy}")
            return None
            
        return self.recovery_strategies[strategy](pipeline_id)
        
    def _retry_recovery(self, pipeline_id: str) -> Dict[str, Any]:
        """Retry from last known state"""
        state = self.pipeline_states[pipeline_id]
        logger.info(f"Retrying pipeline {pipeline_id} from last state")
        return {
            'recovered': True,
            'strategy': 'retry',
            'state': state['state'],
            'message': 'Pipeline recovered using retry strategy'
        }
        
    def _checkpoint_recovery(self, pipeline_id: str) -> Dict[str, Any]:
        """Recover from last checkpoint"""
        state = self.pipeline_states[pipeline_id]
        checkpoints = state.get('checkpoints', [])
        
        if checkpoints:
            last_checkpoint = checkpoints[-1]
            logger.info(f"Recovering pipeline {pipeline_id} from checkpoint")
            return {
                'recovered': True,
                'strategy': 'checkpoint',
                'checkpoint': last_checkpoint,
                'message': f'Pipeline recovered from checkpoint: {last_checkpoint["name"]}'
            }
        else:
            return self._retry_recovery(pipeline_id)
            
    def _rollback_recovery(self, pipeline_id: str) -> Dict[str, Any]:
        """Rollback to initial state"""
        logger.info(f"Rolling back pipeline {pipeline_id}")
        return {
            'recovered': True,
            'strategy': 'rollback',
            'message': 'Pipeline rolled back to initial state'
        }


# Global pipeline state manager
pipeline_state_manager = PipelineStateManager()

from .pipeline_isolation import get_isolation_manager, PipelineIsolationManager

from .security import token_validator, rate_limiter, secure_endpoint, require_auth, rate_limit, sql_protection
