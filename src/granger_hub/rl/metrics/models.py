"""
Data models for RL metrics collection
Module: models.py
Description: Data models and schemas for models

This module defines the structure of RL metrics that will be stored
in ArangoDB for tracking module selection decisions and performance.

Third-party documentation:
- Pydantic: https://pydantic-docs.helpmanual.io/
- ArangoDB: https://www.arangodb.com/docs/stable/

Sample input:
    RLMetric(
        module_id="marker",
        action="select_module",
        reward=0.85,
        state={"task_type": "pdf_processing", "complexity": 0.7}
    )

Expected output:
    Validated metric object ready for ArangoDB storage
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid


class RLMetric(BaseModel):
    """Base RL metric for ArangoDB storage"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    episode_id: Optional[str] = None
    
    # Core RL components
    state: Dict[str, Any] = Field(..., description="State representation")
    action: str = Field(..., description="Action taken")
    reward: float = Field(..., description="Reward received")
    next_state: Optional[Dict[str, Any]] = None
    
    # Metadata
    agent_type: str = Field(default="contextual_bandit")
    module_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    
    @validator('reward')
    def validate_reward(cls, v):
        if not -100 <= v <= 100:
            raise ValueError("Reward must be between -100 and 100")
        return v


class ModuleDecision(BaseModel):
    """Module selection decision record"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Decision details
    available_modules: List[str]
    selected_module: str
    selection_probabilities: Dict[str, float]
    
    # Context
    task_type: str
    task_complexity: float = Field(ge=0.0, le=1.0)
    input_size_bytes: Optional[int] = None
    
    # Outcome
    execution_time_ms: Optional[float] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    reward: Optional[float] = None
    
    # RL algorithm details
    algorithm: str = Field(default="contextual_bandit")
    exploration_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence_scores: Optional[Dict[str, float]] = None


class PipelineExecution(BaseModel):
    """Pipeline execution metrics"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_id: str
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    # Pipeline structure
    modules_planned: List[str]
    modules_executed: List[str] = Field(default_factory=list)
    
    # Execution details
    total_duration_ms: Optional[float] = None
    module_durations_ms: Dict[str, float] = Field(default_factory=dict)
    
    # Outcomes
    success: bool = False
    partial_success: bool = False
    error_modules: List[str] = Field(default_factory=list)
    
    # RL metrics
    cumulative_reward: float = 0.0
    module_rewards: Dict[str, float] = Field(default_factory=dict)
    
    def calculate_duration(self):
        """Calculate total duration if end_time is set"""
        if self.end_time and self.start_time:
            self.total_duration_ms = (
                self.end_time - self.start_time
            ).total_seconds() * 1000


class LearningProgress(BaseModel):
    """Track RL algorithm learning progress"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Algorithm identification
    agent_type: str
    module_or_pipeline: str
    
    # Learning metrics
    episode_number: int = Field(ge=0)
    total_episodes: int = Field(ge=0)
    
    # Performance metrics
    average_reward: float
    success_rate: float = Field(ge=0.0, le=1.0)
    exploration_rate: float = Field(ge=0.0, le=1.0)
    
    # Rolling window metrics (last N episodes)
    window_size: int = Field(default=100)
    window_average_reward: float
    window_success_rate: float = Field(ge=0.0, le=1.0)
    
    # Model details
    model_version: Optional[str] = None
    hyperparameters: Optional[Dict[str, Any]] = None


class ResourceUtilization(BaseModel):
    """Track resource usage for RL decisions"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Resource metrics
    module_id: str
    cpu_usage_percent: float = Field(ge=0.0, le=100.0)
    memory_usage_mb: float = Field(ge=0.0)
    gpu_usage_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    
    # Load metrics
    queue_length: int = Field(ge=0)
    active_tasks: int = Field(ge=0)
    
    # Decision impact
    allocation_decision: str
    priority_score: float = Field(ge=0.0, le=1.0)


if __name__ == "__main__":
    # Test model validation
    print("Testing RL metrics models...")
    
    # Test RLMetric
    metric = RLMetric(
        state={"task_type": "pdf_processing", "complexity": 0.7},
        action="select_marker",
        reward=0.85,
        module_id="marker"
    )
    print(f" RLMetric: {metric.id[:8]}... created at {metric.timestamp}")
    
    # Test ModuleDecision
    decision = ModuleDecision(
        available_modules=["marker", "surya", "openai"],
        selected_module="marker",
        selection_probabilities={"marker": 0.7, "surya": 0.2, "openai": 0.1},
        task_type="pdf_extraction",
        task_complexity=0.6
    )
    print(f" ModuleDecision: selected {decision.selected_module}")
    
    # Test PipelineExecution
    pipeline = PipelineExecution(
        pipeline_id="pipe_123",
        modules_planned=["marker", "gpt4", "storage"],
        modules_executed=["marker", "gpt4"]
    )
    print(f" PipelineExecution: {pipeline.pipeline_id}")
    
    print("\nAll models validated successfully!")
