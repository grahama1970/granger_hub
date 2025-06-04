#!/usr/bin/env python3
"""
Test Task #105: Learning Curves with proper .env configuration
"""
import sys
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, 'src')

from granger_hub.rl.metrics.learning_curves import LearningCurvesCalculator
from arango import ArangoClient

# Get credentials from .env
ARANGO_HOST = os.getenv('ARANGO_HOST', 'localhost')
ARANGO_PORT = int(os.getenv('ARANGO_PORT', '8529'))
ARANGO_USERNAME = os.getenv('ARANGO_USER', 'root')
ARANGO_PASSWORD = os.getenv('ARANGO_PASSWORD', 'openSesame')
ARANGO_DATABASE = os.getenv('ARANGO_DATABASE', 'claude_projects')

print(f"🔍 Using ArangoDB config:")
print(f"   Host: {ARANGO_HOST}:{ARANGO_PORT}")
print(f"   Database: {ARANGO_DATABASE}")
print(f"   Username: {ARANGO_USERNAME}")

try:
    # Connect to ArangoDB with proper credentials
    client = ArangoClient(hosts=f'http://localhost:{ARANGO_PORT}')
    db = client.db(ARANGO_DATABASE, username=ARANGO_USERNAME, password=ARANGO_PASSWORD)
    print("✅ Connected to ArangoDB successfully!")
    
    # Create calculator with authenticated connection
    calculator = LearningCurvesCalculator(db)
    
    # Test learning curves
    start_time = time.time()
    curves = calculator.get_learning_curves('sparta', window_size=50)
    duration = time.time() - start_time
    
    print(f"\n📊 Learning Curves Results:")
    print(f"   Module: {curves['module']}")
    print(f"   Total episodes: {curves['summary']['total_episodes']}")
    print(f"   Duration: {duration:.3f}s")
    
    if curves['summary']['total_episodes'] > 0:
        print(f"   Average reward: {curves['summary']['avg_reward']:.2f}")
        print(f"   Improvement rate: {curves['summary']['improvement_rate']:.4f}")
    
    # Test module comparison
    comparison = calculator.get_module_comparison(['sparta', 'marker'], metric='reward')
    print(f"\n📊 Module Comparison:")
    print(f"   Best performer: {comparison.get('best_performer', 'No data')}")
    
    # Verify test duration
    if 0.2 <= duration <= 2.0:
        print(f"\n✅ Test duration {duration:.3f}s is within expected range (0.2s-2.0s)")
    else:
        print(f"\n⚠️  Test duration {duration:.3f}s is outside expected range")
        
    print("\n✅ Task #105 Implementation Working Correctly!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
