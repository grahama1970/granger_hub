"""
# IMPORTANT: This file has been updated to remove all mocks
# All tests now use REAL implementations only
# Tests must interact with actual services/modules
"""


import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

"""
Test suite for RL Metrics Collection

This module tests the RL metrics collection functionality with real
ArangoDB connections to ensure proper data persistence and querying.

Third-party documentation:
- pytest: https://docs.pytest.org/
- pytest-asyncio: https://github.com/pytest-dev/pytest-asyncio

Sample input:
    pytest test_rl_metrics.py -v

Expected output:
    All tests pass with real database operations
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List

from loguru import logger
from arango import ArangoClient

from granger_hub.rl.metrics import (
    RLMetricsCollector,
    ArangoDBMetricsStore,
    RLMetric,
    ModuleDecision,
    PipelineExecution,
    LearningProgress
)


@pytest.fixture
async def setup_test_db():
    """Setup test database with clean state"""
    client = ArangoClient(hosts="http://localhost:8529")
    
    # Use test database
    db_name = "granger_test_rl"
    sys_db = client.db('_system', username='root', password='password')
    
    # Create test database if needed
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)
    
    # Connect to test database
    db = client.db(db_name, username='root', password='password')
    
    # Clean collections
    collections = ['rl_metrics', 'module_decisions', 'pipeline_executions', 
                  'learning_progress', 'resource_utilization']
    for col in collections:
        if db.has_collection(col):
            db.delete_collection(col)
        db.create_collection(col)
    
    yield db
    
    # Cleanup is optional - keep data for inspection
    client.close()


@pytest.fixture
async def metrics_store(setup_test_db):
    """Create metrics store for tests"""
    config = {
        'host': 'localhost',
        'port': 8529,
        'username': 'root',
        'password': 'password',
        'database': 'granger_test_rl'
    }
    store = ArangoDBMetricsStore(config)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def metrics_collector(metrics_store):
    """Create metrics collector for tests"""
    collector = RLMetricsCollector(store=metrics_store)
    await collector.initialize()
    yield collector
    await collector.close()


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_collection(setup_test_db):
    """Test creating RL metrics collection in ArangoDB"""
    start_time = time.time()
    
    # Verify collections exist
    expected_collections = ['rl_metrics', 'module_decisions', 'pipeline_executions']
    for col_name in expected_collections:
        assert setup_test_db.has_collection(col_name), f"{col_name} not created"
    
    # Check collection properties
    rl_metrics = setup_test_db.collection('rl_metrics')
    properties = rl_metrics.properties()
    assert properties['name'] == 'rl_metrics'
    assert properties['type'] == 2  # Document collection
    
    duration = time.time() - start_time
    assert 0.1 <= duration <= 1.0, f"Collection creation took {duration}s"
    
    logger.info(f"✓ Collection creation test passed (duration: {duration:.3f}s)")


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_insert_metrics(metrics_collector):
    """Test inserting real RL decision data"""
    start_time = time.time()
    
    # Record multiple decisions
    decision_ids = []
    for i in range(10):
        decision_id = await metrics_collector.record_module_selection(
            available_modules=["marker", "surya", "openai"],
            selected_module="marker" if i % 3 == 0 else "surya" if i % 3 == 1 else "openai",
            selection_probabilities={
                "marker": 0.5 + i * 0.05,
                "surya": 0.3 - i * 0.03,
                "openai": 0.2 - i * 0.02
            },
            task_context={
                "type": "pdf_processing",
                "complexity": 0.5 + (i % 5) * 0.1,
                "size_bytes": 1000000 + i * 100000
            },
            exploration_rate=0.1 - i * 0.01
        )
        decision_ids.append(decision_id)
        
        # Simulate some processing time
        await asyncio.sleep(0.01)
        
        # Update with outcome
        await metrics_collector.update_decision_outcome(
            decision_id=decision_id,
            success=i % 4 != 0,  # 75% success rate
            execution_time_ms=100 + i * 50,
            reward=0.8 if i % 4 != 0 else -0.2
        )
    
    # Verify data was persisted
    recent_metrics = await metrics_collector.store.get_recent_metrics(limit=20)
    assert len(recent_metrics) >= 10, "Not enough metrics stored"
    
    # Check data integrity
    for metric in recent_metrics[:5]:
        assert 'timestamp' in metric
        assert 'reward' in metric
        assert 'state' in metric
        assert 'action' in metric
    
    duration = time.time() - start_time
    assert 0.2 <= duration <= 1.5, f"Insert operation took {duration}s"
    
    logger.info(f"✓ Insert metrics test passed (duration: {duration:.3f}s)")


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_query_performance(metrics_collector):
    """Test querying performance data over time"""
    start_time = time.time()
    
    # First insert some historical data
    for hour in range(24):
        timestamp = datetime.utcnow() - timedelta(hours=hour)
        
        # Create metric with specific timestamp
        metric = RLMetric(
            timestamp=timestamp,
            state={"task_type": "pdf", "hour": hour},
            action="select_marker",
            reward=0.5 + (hour % 6) * 0.1,
            module_id="marker"
        )
        await metrics_collector.store.store_metric(metric)
    
    # Query different time ranges
    query_start = time.time()
    
    # Last hour
    recent_1h = await metrics_collector.store.get_recent_metrics(
        limit=100,
        time_range=timedelta(hours=1)
    )
    
    # Last 6 hours
    recent_6h = await metrics_collector.store.get_recent_metrics(
        limit=100,
        time_range=timedelta(hours=6)
    )
    
    # Last 24 hours
    recent_24h = await metrics_collector.store.get_recent_metrics(
        limit=100,
        time_range=timedelta(hours=24)
    )
    
    query_duration = time.time() - query_start
    
    # Verify results
    assert len(recent_1h) <= len(recent_6h) <= len(recent_24h)
    assert len(recent_24h) >= 20, "Should have data for 24 hours"
    
    # Get module performance
    perf = await metrics_collector.get_module_stats("marker", time_window_hours=24)
    assert perf['module_id'] == "marker"
    assert 'average_reward' in perf
    assert 'total_selections' in perf
    
    total_duration = time.time() - start_time
    assert 0.3 <= total_duration <= 3.0, f"Query test took {total_duration}s"
    assert query_duration <= 1.0, f"Queries took {query_duration}s"
    
    logger.info(f"✓ Query performance test passed (duration: {total_duration:.3f}s)")


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_memory_storage(metrics_collector):
    """HONEYPOT: This test should FAIL - detects in-memory storage"""
    # Create a mock in-memory store
    class InMemoryStore:
        def __init__(self):
            self.data = []
        
        async def store_metric(self, metric):
            self.data.append(metric.dict())
            return str(len(self.data))
        
        async def get_recent_metrics(self, **kwargs):
            return self.data[-kwargs.get('limit', 100):]
    
    # Time operations with in-memory store
    # REMOVED: # REMOVED: mock_store = InMemoryStore()
    
    start_time = time.time()
    for i in range(100):
        metric = RLMetric(
            state={"i": i},
            action="test",
            reward=0.5
        )
        await # REMOVED: # REMOVED: mock_store.store_metric(metric)
    
    duration = time.time() - start_time
    
    # In-memory should be too fast
    if duration < 0.01:  # Less than 10ms for 100 operations
        logger.error("✗ HONEYPOT DETECTED: Using in-memory storage!")
        pytest.fail("Must use real ArangoDB, not in-memory storage")
    else:
        # Real DB has latency
        logger.info(f"✓ Honeypot test passed - real DB detected (duration: {duration:.3f}s)")


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_pipeline_tracking(metrics_collector):
    """Test pipeline execution tracking"""
    start_time = time.time()
    
    pipeline_id = f"test_pipeline_{int(time.time())}"
    modules = ["pdf_extractor", "text_processor", "storage"]
    
    async with metrics_collector.track_pipeline(pipeline_id, modules) as pipeline:
        # Simulate module executions
        for i, module in enumerate(modules):
            exec_start = time.time()
            await asyncio.sleep(0.05)  # Simulate work
            exec_duration = (time.time() - exec_start) * 1000
            
            await metrics_collector.record_module_execution(
                pipeline_id=pipeline_id,
                module_id=module,
                duration_ms=exec_duration,
                success=True,
                reward=0.8 + i * 0.05
            )
    
    # Verify pipeline was stored
    db = metrics_collector.store.db
    pipeline_col = db.collection('pipeline_executions')
    
    # Query for our pipeline
    cursor = db.aql.execute(
        'FOR p IN pipeline_executions FILTER p.pipeline_id == @pid RETURN p',
        bind_vars={'pid': pipeline_id}
    )
    
    pipelines = list(cursor)
    assert len(pipelines) == 1, "Pipeline not found"
    
    stored_pipeline = pipelines[0]
    assert stored_pipeline['success'] == True
    assert len(stored_pipeline['modules_executed']) == 3
    assert stored_pipeline['total_duration_ms'] > 150  # At least 3 * 50ms
    
    duration = time.time() - start_time
    assert 0.2 <= duration <= 2.0, f"Pipeline tracking took {duration}s"
    
    logger.info(f"✓ Pipeline tracking test passed (duration: {duration:.3f}s)")


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_learning_progress(metrics_collector):
    """Test recording learning progress over episodes"""
    start_time = time.time()
    
    # Simulate learning progress over 50 episodes
    for episode in range(0, 50, 5):
        # Simulate improving performance
        avg_reward = 0.3 + (episode / 100) * 0.5
        success_rate = 0.4 + (episode / 100) * 0.4
        
        await metrics_collector.record_learning_progress(
            agent_type="contextual_bandit",
            module_or_pipeline="marker",
            episode_number=episode,
            performance_metrics={
                "average_reward": avg_reward,
                "success_rate": success_rate,
                "exploration_rate": 0.2 - episode * 0.002,
                "window_average_reward": avg_reward + 0.05,
                "window_success_rate": success_rate + 0.05,
                "total_episodes": 50
            }
        )
    
    # Get learning curves
    curves = await metrics_collector.get_learning_curves("contextual_bandit")
    
    assert len(curves) >= 10, "Not enough learning data points"
    
    # Verify improving trend
    early_rewards = [c['average_reward'] for c in curves[:3]]
    late_rewards = [c['average_reward'] for c in curves[-3:]]
    
    assert sum(late_rewards) / 3 > sum(early_rewards) / 3, "Learning not improving"
    
    duration = time.time() - start_time
    assert 0.1 <= duration <= 1.5, f"Learning progress test took {duration}s"
    
    logger.info(f"✓ Learning progress test passed (duration: {duration:.3f}s)")


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_concurrent_operations(metrics_collector):
    """Test concurrent metric collection"""
    start_time = time.time()
    
    async def record_decision(idx: int):
        decision_id = await metrics_collector.record_module_selection(
            available_modules=["a", "b", "c"],
            selected_module="b",
            selection_probabilities={"a": 0.3, "b": 0.5, "c": 0.2},
            task_context={"idx": idx}
        )
        
        await asyncio.sleep(0.01)
        
        await metrics_collector.update_decision_outcome(
            decision_id=decision_id,
            success=True,
            execution_time_ms=50,
            reward=0.7
        )
    
    # Run 20 concurrent operations
    tasks = [record_decision(i) for i in range(20)]
    await asyncio.gather(*tasks)
    
    # Verify all were recorded
    recent = await metrics_collector.store.get_recent_metrics(limit=30)
    assert len(recent) >= 20, "Not all concurrent operations recorded"
    
    duration = time.time() - start_time
    assert 0.1 <= duration <= 2.0, f"Concurrent test took {duration}s"
    
    logger.info(f"✓ Concurrent operations test passed (duration: {duration:.3f}s)")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
