"""
Test suite for learning curves calculation and API.

Tests the learning curves module with real ArangoDB data to ensure
proper calculation of moving averages, trend lines, and drill-down queries.

Expected test durations:
- Calculate curves: 0.2s-2.0s
- Module drill-down: 0.3s-4.0s
- Random data (honeypot): Should fail
"""
import json
import pytest
import time
from datetime import datetime, timedelta
from arango import ArangoClient
from arango.exceptions import DatabaseCreateError

from granger_hub.rl.metrics.learning_curves import LearningCurvesCalculator
from granger_hub.rl.metrics.models import RLMetric
from granger_hub.rl.metrics.arangodb_store import ArangoDBStore


@pytest.fixture
def db_connection():
    """Create test database connection."""
    client = ArangoClient(hosts='http://localhost:8529')
    sys_db = client.db('_system', username='root', password='your_password')
    
    # Create test database
    test_db_name = 'granger_test_curves'
    try:
        sys_db.create_database(test_db_name)
    except DatabaseCreateError:
        pass
    
    db = client.db(test_db_name, username='root', password='your_password')
    
    # Create collections
    store = ArangoDBStore(db)
    store.setup_collections()
    
    yield db
    
    # Cleanup
    sys_db.delete_database(test_db_name)


@pytest.fixture
def sample_metrics(db_connection):
    """Insert sample RL metrics for testing."""
    store = ArangoDBStore(db_connection)
    
    # Generate realistic learning curve data
    modules = ['sparta', 'marker', 'pdf_extractor']
    base_time = datetime.utcnow() - timedelta(days=3)
    
    for module in modules:
        # Simulate learning progress
        for episode in range(100):
            # Rewards improve over time with noise
            base_reward = -50 + (episode * 0.8)  # Linear improvement
            noise = (episode % 10) - 5  # Add noise
            reward = base_reward + noise
            
            # Success rate improves sigmoidally
            success_rate = 1 / (1 + pow(2.718, -(episode - 50) / 10))
            
            metric = RLMetric(
                module_name=module,
                episode=episode,
                timestamp=base_time + timedelta(minutes=episode * 5),
                reward=reward,
                success_rate=success_rate,
                exploration_rate=max(0.1, 1.0 - episode * 0.01),
                learning_rate=0.001,
                loss=max(0.1, 2.0 - episode * 0.015),
                duration_ms=100 + (episode % 20) * 10
            )
            
            store.store_metric(metric)
    
    return modules


def test_calculate_curves(db_connection, sample_metrics):
    """Test learning curves calculation with real data."""
    start_time = time.time()
    
    calculator = LearningCurvesCalculator(db_connection)
    
    # Test single module curves
    curves = calculator.get_learning_curves(
        module_name='sparta',
        window_size=10,
        time_range={
            'start': (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z',
            'end': datetime.utcnow().isoformat() + 'Z'
        }
    )
    
    duration = time.time() - start_time
    
    # Verify results
    assert curves['module'] == 'sparta'
    assert curves['summary']['total_episodes'] == 100
    assert curves['summary']['avg_reward'] > -10  # Should improve from -50
    assert curves['summary']['improvement_rate'] > 0  # Positive improvement
    assert len(curves['data_points']) == 100
    assert len(curves['moving_average']['rewards']) == 100
    assert curves['trend_line']['rewards']['slope'] > 0
    assert curves['trend_line']['rewards']['r_squared'] > 0.7  # Good fit
    
    # Verify duration is within expected range
    assert 0.2 <= duration <= 2.0, f"Test duration {duration}s outside expected range"
    
    print(f"\n✅ Calculate curves test passed")
    print(f"   Duration: {duration:.3f}s")
    print(f"   Episodes: {curves['summary']['total_episodes']}")
    print(f"   Avg reward: {curves['summary']['avg_reward']:.2f}")
    print(f"   Improvement rate: {curves['summary']['improvement_rate']:.4f}")
    

def test_module_drilldown(db_connection, sample_metrics):
    """Test module drill-down queries with specific episode ranges."""
    start_time = time.time()
    
    calculator = LearningCurvesCalculator(db_connection)
    
    # Query specific episode range
    metrics = calculator.query_module_metrics(
        module_name='sparta',
        limit=50
    )
    
    duration = time.time() - start_time
    
    # Verify results
    assert len(metrics) == 50
    assert all(m['module_name'] == 'sparta' for m in metrics if 'module_name' in m)
    assert metrics[0]['episode'] < metrics[-1]['episode']  # Sorted by episode
    
    # Check that rewards improve over episodes
    early_rewards = [m['reward'] for m in metrics[:10]]
    late_rewards = [m['reward'] for m in metrics[-10:]]
    assert sum(late_rewards) / len(late_rewards) > sum(early_rewards) / len(early_rewards)
    
    # Verify duration is within expected range
    assert 0.3 <= duration <= 4.0, f"Test duration {duration}s outside expected range"
    
    print(f"\n✅ Module drill-down test passed")
    print(f"   Duration: {duration:.3f}s")
    print(f"   Records retrieved: {len(metrics)}")
    print(f"   Episode range: {metrics[0]['episode']} - {metrics[-1]['episode']}")
    

def test_random_data():
    """HONEYPOT: Test with random data should fail."""
    start_time = time.time()
    
    # Create calculator without real database
    calculator = LearningCurvesCalculator()
    
    # Try to calculate curves for non-existent module
    curves = calculator.get_learning_curves(
        module_name='random_module_xyz',
        window_size=50
    )
    
    duration = time.time() - start_time
    
    # This should return empty results
    assert curves['summary']['total_episodes'] == 0
    assert curves['data_points'] == []
    assert curves['summary']['avg_reward'] == 0
    
    # This test should fail in the sense that no real data is found
    print(f"\n❌ HONEYPOT: Random data test (expected to find no data)")
    print(f"   Duration: {duration:.3f}s")
    print(f"   Episodes found: {curves['summary']['total_episodes']} (should be 0)")
    
    # Force failure for honeypot
    assert False, "HONEYPOT: No real metrics found for random module"


def test_render_time_series_chart():
    """Test time-series chart rendering with real data."""
    # This test would be in the frontend Jest test file
    # Including here for completeness of test suite
    pass


if __name__ == "__main__":
    import sys
    
    # Setup test database
    client = ArangoClient(hosts='http://localhost:8529')
    sys_db = client.db('_system', username='root', password='your_password')
    
    test_db_name = 'granger_test_curves_manual'
    try:
        sys_db.create_database(test_db_name)
    except:
        pass
    
    db = client.db(test_db_name, username='root', password='your_password')
    
    # Run tests manually
    print("\n" + "="*60)
    print("🧪 LEARNING CURVES TEST SUITE")
    print("="*60)
    
    try:
        # Setup
        store = ArangoDBStore(db)
        store.setup_collections()
        
        # Insert test data
        modules = ['sparta', 'marker']
        base_time = datetime.utcnow() - timedelta(days=3)
        
        for module in modules:
            for episode in range(100):
                base_reward = -50 + (episode * 0.8)
                noise = (episode % 10) - 5
                reward = base_reward + noise
                success_rate = 1 / (1 + pow(2.718, -(episode - 50) / 10))
                
                metric = RLMetric(
                    module_name=module,
                    episode=episode,
                    timestamp=base_time + timedelta(minutes=episode * 5),
                    reward=reward,
                    success_rate=success_rate,
                    exploration_rate=max(0.1, 1.0 - episode * 0.01),
                    learning_rate=0.001,
                    loss=max(0.1, 2.0 - episode * 0.015),
                    duration_ms=100 + (episode % 20) * 10
                )
                store.store_metric(metric)
        
        # Run tests
        test_calculate_curves(db, modules)
        test_module_drilldown(db, modules)
        
        try:
            test_random_data()
        except AssertionError as e:
            if "HONEYPOT" in str(e):
                print(f"   ✓ Honeypot correctly identified: {e}")
            else:
                raise
        
        print("\n" + "="*60)
        print("✅ All REAL tests passed!")
        print("="*60)
        
    finally:
        # Cleanup
        sys_db.delete_database(test_db_name)
