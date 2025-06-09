"""
RL Metrics Collector
Module: collector.py

This module provides the main interface for collecting RL metrics
from the hub decision-making process and storing them in ArangoDB.

Third-party documentation:
- asyncio: https://docs.python.org/3/library/asyncio.html
- loguru: https://loguru.readthedocs.io/

Sample input:
    collector = RLMetricsCollector()
    await collector.record_module_selection(
        available_modules=["marker", "surya"],
        selected_module="marker",
        task_context={"type": "pdf", "size": 1024}
    )

Expected output:
    Metrics stored in ArangoDB with decision tracking
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time
from contextlib import asynccontextmanager

from loguru import logger

from .models import (
    RLMetric, ModuleDecision, PipelineExecution, 
    LearningProgress, ResourceUtilization
)
from .arangodb_store import ArangoDBMetricsStore


class RLMetricsCollector:
    """Collects and stores RL metrics for the GRANGER dashboard"""
    
    def __init__(self, store: Optional[ArangoDBMetricsStore] = None):
        self.store = store or ArangoDBMetricsStore()
        self._active_pipelines: Dict[str, PipelineExecution] = {}
        self._active_decisions: Dict[str, ModuleDecision] = {}
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the metrics collector"""
        async with self._lock:
            if not self._initialized:
                await self.store.initialize()
                self._initialized = True
                logger.info("RL Metrics Collector initialized")
    
    async def record_module_selection(
        self,
        available_modules: List[str],
        selected_module: str,
        selection_probabilities: Dict[str, float],
        task_context: Dict[str, Any],
        algorithm: str = "contextual_bandit",
        exploration_rate: Optional[float] = None
    ) -> str:
        """Record a module selection decision"""
        if not self._initialized:
            await self.initialize()
        
        # Extract task details
        task_type = task_context.get('type', 'unknown')
        task_complexity = task_context.get('complexity', 0.5)
        input_size = task_context.get('size_bytes', None)
        
        # Create decision record
        decision = ModuleDecision(
            available_modules=available_modules,
            selected_module=selected_module,
            selection_probabilities=selection_probabilities,
            task_type=task_type,
            task_complexity=task_complexity,
            input_size_bytes=input_size,
            algorithm=algorithm,
            exploration_rate=exploration_rate
        )
        
        # Store for later update with results
        self._active_decisions[decision.id] = decision
        
        # Store immediately
        await self.store.store_decision(decision)
        
        logger.debug(f"Recorded module selection: {selected_module} for {task_type}")
        return decision.id
    
    async def update_decision_outcome(
        self,
        decision_id: str,
        success: bool,
        execution_time_ms: float,
        reward: float,
        error_message: Optional[str] = None
    ):
        """Update a decision with its outcome"""
        if decision_id in self._active_decisions:
            decision = self._active_decisions[decision_id]
            decision.success = success
            decision.execution_time_ms = execution_time_ms
            decision.reward = reward
            decision.error_message = error_message
            
            # Re-store with updated information
            await self.store.store_decision(decision)
            
            # Create RL metric
            metric = RLMetric(
                state={
                    "task_type": decision.task_type,
                    "complexity": decision.task_complexity,
                    "available_modules": len(decision.available_modules)
                },
                action=f"select_{decision.selected_module}",
                reward=reward,
                module_id=decision.selected_module,
                agent_type=decision.algorithm
            )
            await self.store.store_metric(metric)
            
            # Clean up
            del self._active_decisions[decision_id]
            
            logger.debug(f"Updated decision {decision_id}: success={success}, reward={reward}")
    
    @asynccontextmanager
    async def track_pipeline(self, pipeline_id: str, planned_modules: List[str]):
        """Context manager for tracking pipeline execution"""
        if not self._initialized:
            await self.initialize()
        
        pipeline = PipelineExecution(
            pipeline_id=pipeline_id,
            modules_planned=planned_modules,
            start_time=datetime.utcnow()
        )
        
        self._active_pipelines[pipeline_id] = pipeline
        
        try:
            yield pipeline
        finally:
            # Finalize pipeline
            pipeline.end_time = datetime.utcnow()
            pipeline.calculate_duration()
            
            # Determine success
            if len(pipeline.error_modules) == 0:
                pipeline.success = True
            elif len(pipeline.modules_executed) > 0:
                pipeline.partial_success = True
            
            # Store pipeline
            await self.store.store_pipeline(pipeline)
            
            # Clean up
            if pipeline_id in self._active_pipelines:
                del self._active_pipelines[pipeline_id]
            
            logger.info(
                f"Pipeline {pipeline_id} completed: "
                f"success={pipeline.success}, "
                f"duration={pipeline.total_duration_ms}ms"
            )
    
    async def record_module_execution(
        self,
        pipeline_id: str,
        module_id: str,
        duration_ms: float,
        success: bool,
        reward: float
    ):
        """Record module execution within a pipeline"""
        if pipeline_id in self._active_pipelines:
            pipeline = self._active_pipelines[pipeline_id]
            
            pipeline.modules_executed.append(module_id)
            pipeline.module_durations_ms[module_id] = duration_ms
            pipeline.module_rewards[module_id] = reward
            pipeline.cumulative_reward += reward
            
            if not success:
                pipeline.error_modules.append(module_id)
            
            logger.debug(
                f"Module {module_id} in pipeline {pipeline_id}: "
                f"duration={duration_ms}ms, reward={reward}"
            )
    
    async def record_learning_progress(
        self,
        agent_type: str,
        module_or_pipeline: str,
        episode_number: int,
        performance_metrics: Dict[str, Any]
    ):
        """Record learning algorithm progress"""
        if not self._initialized:
            await self.initialize()
        
        progress = LearningProgress(
            agent_type=agent_type,
            module_or_pipeline=module_or_pipeline,
            episode_number=episode_number,
            total_episodes=performance_metrics.get('total_episodes', episode_number),
            average_reward=performance_metrics['average_reward'],
            success_rate=performance_metrics.get('success_rate', 0.0),
            exploration_rate=performance_metrics.get('exploration_rate', 0.0),
            window_size=performance_metrics.get('window_size', 100),
            window_average_reward=performance_metrics.get('window_average_reward', 0.0),
            window_success_rate=performance_metrics.get('window_success_rate', 0.0),
            model_version=performance_metrics.get('model_version'),
            hyperparameters=performance_metrics.get('hyperparameters')
        )
        
        await self.store.store_progress(progress)
        
        logger.info(
            f"Learning progress for {agent_type}/{module_or_pipeline}: "
            f"episode {episode_number}, avg_reward={progress.average_reward:.3f}"
        )
    
    async def get_module_stats(
        self, 
        module_id: str,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get performance statistics for a module"""
        if not self._initialized:
            await self.initialize()
        
        from datetime import timedelta
        time_range = timedelta(hours=time_window_hours)
        
        return await self.store.get_module_performance(module_id, time_range)
    
    async def get_learning_curves(self, agent_type: str) -> List[Dict[str, Any]]:
        """Get learning curve data for visualization"""
        if not self._initialized:
            await self.initialize()
        
        return await self.store.get_learning_curves(agent_type)
    
    async def close(self):
        """Close connections and clean up"""
        await self.store.close()
        self._initialized = False


# Global collector instance
_collector: Optional[RLMetricsCollector] = None


def get_metrics_collector() -> RLMetricsCollector:
    """Get or create the global metrics collector"""
    global _collector
    if _collector is None:
        _collector = RLMetricsCollector()
    return _collector


if __name__ == "__main__":
    # Test the collector
    async def test_collector():
        collector = RLMetricsCollector()
        
        try:
            # Initialize
            await collector.initialize()
            print(" Collector initialized")
            
            # Test module selection
            decision_id = await collector.record_module_selection(
                available_modules=["marker", "surya", "openai"],
                selected_module="marker",
                selection_probabilities={"marker": 0.7, "surya": 0.2, "openai": 0.1},
                task_context={
                    "type": "pdf_extraction",
                    "complexity": 0.6,
                    "size_bytes": 1024000
                },
                exploration_rate=0.1
            )
            print(f" Recorded decision: {decision_id}")
            
            # Simulate execution
            await asyncio.sleep(0.1)
            
            # Update with outcome
            await collector.update_decision_outcome(
                decision_id=decision_id,
                success=True,
                execution_time_ms=250.5,
                reward=0.85
            )
            print(" Updated decision outcome")
            
            # Test pipeline tracking
            async with collector.track_pipeline(
                "test_pipeline_123",
                ["marker", "gpt4", "storage"]
            ) as pipeline:
                # Simulate module executions
                await collector.record_module_execution(
                    pipeline.pipeline_id, "marker", 150.0, True, 0.8
                )
                await collector.record_module_execution(
                    pipeline.pipeline_id, "gpt4", 500.0, True, 0.9
                )
                await collector.record_module_execution(
                    pipeline.pipeline_id, "storage", 50.0, True, 1.0
                )
            
            print(" Pipeline tracking completed")
            
            # Test progress recording
            await collector.record_learning_progress(
                agent_type="contextual_bandit",
                module_or_pipeline="marker",
                episode_number=100,
                performance_metrics={
                    "average_reward": 0.75,
                    "success_rate": 0.85,
                    "exploration_rate": 0.1,
                    "window_average_reward": 0.8,
                    "window_success_rate": 0.9
                }
            )
            print(" Recorded learning progress")
            
            # Get stats
            stats = await collector.get_module_stats("marker")
            print(f" Module stats: {stats}")
            
            await collector.close()
            print(" Collector closed")
            
        except Exception as e:
            print(f" Error: {e}")
            raise
    
    asyncio.run(test_collector())
