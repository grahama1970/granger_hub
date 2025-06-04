"""
ArangoDB storage for RL metrics

This module handles storing and retrieving RL metrics in ArangoDB,
with support for time-series queries and aggregations.

Third-party documentation:
- python-arango: https://docs.python-arango.com/en/main/
- ArangoDB AQL: https://www.arangodb.com/docs/stable/aql/

Sample input:
    store = ArangoDBMetricsStore()
    await store.store_metric(metric)

Expected output:
    Metric stored with document key returned
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import json
from contextlib import asynccontextmanager

from arango import ArangoClient
from arango.database import StandardDatabase
from arango.exceptions import ArangoError
from loguru import logger

from .models import (
    RLMetric, ModuleDecision, PipelineExecution, 
    LearningProgress, ResourceUtilization
)


class ArangoDBMetricsStore:
    """Manages RL metrics storage in ArangoDB"""
    
    def __init__(self, connection_config: Optional[Dict[str, Any]] = None):
        self.client: Optional[ArangoClient] = None
        self.db: Optional[StandardDatabase] = None
        self._lock = asyncio.Lock()
        
        # Configuration
        if connection_config:
            self.config = connection_config
        else:
            self.config = {
                'host': os.getenv('ARANGODB_HOST', 'localhost'),
                'port': int(os.getenv('ARANGODB_PORT', '8529')),
                'username': os.getenv('ARANGODB_USERNAME', 'root'),
                'password': os.getenv('ARANGODB_PASSWORD', 'password'),
                'database': os.getenv('ARANGODB_DATABASE', 'granger')
            }
        
        # Collection names
        self.collections = {
            'metrics': 'rl_metrics',
            'decisions': 'module_decisions',
            'pipelines': 'pipeline_executions',
            'progress': 'learning_progress',
            'resources': 'resource_utilization'
        }
    
    async def initialize(self):
        """Initialize ArangoDB connection and ensure collections exist"""
        async with self._lock:
            if self.client is None:
                try:
                    # Create client
                    self.client = ArangoClient(
                        hosts=f"http://{self.config['host']}:{self.config['port']}"
                    )
                    
                    # Connect to database
                    self.db = self.client.db(
                        name=self.config['database'],
                        username=self.config['username'],
                        password=self.config['password']
                    )
                    
                    # Verify connection
                    await asyncio.to_thread(self.db.properties)
                    logger.info(f"Connected to ArangoDB for RL metrics")
                    
                    # Ensure collections and indexes exist
                    await self._ensure_collections()
                    await self._create_indexes()
                    
                except ArangoError as e:
                    logger.error(f"Failed to initialize ArangoDB: {e}")
                    raise
    
    async def _ensure_collections(self):
        """Ensure all required collections exist"""
        for name, collection in self.collections.items():
            if not await asyncio.to_thread(self.db.has_collection, collection):
                await asyncio.to_thread(self.db.create_collection, collection)
                logger.info(f"Created collection: {collection}")
    
    async def _create_indexes(self):
        """Create time-series indexes for efficient queries"""
        # Indexes for rl_metrics
        metrics_col = self.db.collection(self.collections['metrics'])
        await asyncio.to_thread(
            metrics_col.add_persistent_index,
            fields=['timestamp'],
            name='idx_timestamp'
        )
        await asyncio.to_thread(
            metrics_col.add_persistent_index,
            fields=['module_id', 'timestamp'],
            name='idx_module_time'
        )
        
        # Indexes for module_decisions
        decisions_col = self.db.collection(self.collections['decisions'])
        await asyncio.to_thread(
            decisions_col.add_persistent_index,
            fields=['timestamp'],
            name='idx_timestamp'
        )
        await asyncio.to_thread(
            decisions_col.add_persistent_index,
            fields=['selected_module', 'timestamp'],
            name='idx_module_time'
        )
        
        logger.info("Created database indexes")
    
    async def store_metric(self, metric: RLMetric) -> str:
        """Store a single RL metric"""
        if not self.db:
            await self.initialize()
        
        try:
            collection = self.db.collection(self.collections['metrics'])
            result = await asyncio.to_thread(
                collection.insert,
                metric.dict()
            )
            return result['_key']
        except ArangoError as e:
            logger.error(f"Error storing metric: {e}")
            raise
    
    async def store_decision(self, decision: ModuleDecision) -> str:
        """Store a module selection decision"""
        if not self.db:
            await self.initialize()
        
        try:
            collection = self.db.collection(self.collections['decisions'])
            result = await asyncio.to_thread(
                collection.insert,
                decision.dict()
            )
            return result['_key']
        except ArangoError as e:
            logger.error(f"Error storing decision: {e}")
            raise
    
    async def store_pipeline(self, pipeline: PipelineExecution) -> str:
        """Store pipeline execution data"""
        if not self.db:
            await self.initialize()
        
        try:
            # Calculate duration if needed
            pipeline.calculate_duration()
            
            collection = self.db.collection(self.collections['pipelines'])
            result = await asyncio.to_thread(
                collection.insert,
                pipeline.dict()
            )
            return result['_key']
        except ArangoError as e:
            logger.error(f"Error storing pipeline: {e}")
            raise
    
    async def store_progress(self, progress: LearningProgress) -> str:
        """Store learning progress snapshot"""
        if not self.db:
            await self.initialize()
        
        try:
            collection = self.db.collection(self.collections['progress'])
            result = await asyncio.to_thread(
                collection.insert,
                progress.dict()
            )
            return result['_key']
        except ArangoError as e:
            logger.error(f"Error storing progress: {e}")
            raise
    
    async def get_recent_metrics(
        self, 
        limit: int = 100,
        module_id: Optional[str] = None,
        time_range: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve recent RL metrics"""
        if not self.db:
            await self.initialize()
        
        try:
            bind_vars = {'@collection': self.collections['metrics'], 'limit': limit}
            
            # Build query
            conditions = []
            if module_id:
                conditions.append("doc.module_id == @module_id")
                bind_vars['module_id'] = module_id
            
            if time_range:
                cutoff = (datetime.utcnow() - time_range).isoformat()
                conditions.append("doc.timestamp >= @cutoff")
                bind_vars['cutoff'] = cutoff
            
            where_clause = "FILTER " + " AND ".join(conditions) if conditions else ""
            
            query = f'''
            FOR doc IN @@collection
                {where_clause}
                SORT doc.timestamp DESC
                LIMIT @limit
                RETURN doc
            '''
            
            cursor = await asyncio.to_thread(
                self.db.aql.execute,
                query,
                bind_vars=bind_vars
            )
            
            return list(cursor)
            
        except ArangoError as e:
            logger.error(f"Error fetching metrics: {e}")
            raise
    
    async def get_module_performance(
        self,
        module_id: str,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get aggregated performance metrics for a module"""
        if not self.db:
            await self.initialize()
        
        try:
            bind_vars = {
                '@collection': self.collections['decisions'],
                'module_id': module_id
            }
            
            time_filter = ""
            if time_range:
                cutoff = (datetime.utcnow() - time_range).isoformat()
                time_filter = "FILTER doc.timestamp >= @cutoff"
                bind_vars['cutoff'] = cutoff
            
            query = f'''
            FOR doc IN @@collection
                FILTER doc.selected_module == @module_id
                {time_filter}
                COLLECT AGGREGATE 
                    total = COUNT(1),
                    successes = SUM(doc.success ? 1 : 0),
                    avg_reward = AVG(doc.reward),
                    avg_execution_time = AVG(doc.execution_time_ms),
                    total_reward = SUM(doc.reward)
                RETURN {{
                    module_id: @module_id,
                    total_selections: total,
                    success_count: successes,
                    success_rate: successes / total,
                    average_reward: avg_reward,
                    total_reward: total_reward,
                    average_execution_time_ms: avg_execution_time
                }}
            '''
            
            cursor = await asyncio.to_thread(
                self.db.aql.execute,
                query,
                bind_vars=bind_vars
            )
            
            results = list(cursor)
            return results[0] if results else {
                'module_id': module_id,
                'total_selections': 0,
                'success_rate': 0.0,
                'average_reward': 0.0
            }
            
        except ArangoError as e:
            logger.error(f"Error fetching module performance: {e}")
            raise
    
    async def get_learning_curves(
        self,
        agent_type: str,
        window_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Get learning curve data for visualization"""
        if not self.db:
            await self.initialize()
        
        try:
            query = '''
            FOR doc IN @@collection
                FILTER doc.agent_type == @agent_type
                SORT doc.episode_number ASC
                RETURN {
                    episode: doc.episode_number,
                    timestamp: doc.timestamp,
                    average_reward: doc.average_reward,
                    success_rate: doc.success_rate,
                    exploration_rate: doc.exploration_rate,
                    window_average_reward: doc.window_average_reward,
                    window_success_rate: doc.window_success_rate
                }
            '''
            
            cursor = await asyncio.to_thread(
                self.db.aql.execute,
                query,
                bind_vars={
                    '@collection': self.collections['progress'],
                    'agent_type': agent_type
                }
            )
            
            return list(cursor)
            
        except ArangoError as e:
            logger.error(f"Error fetching learning curves: {e}")
            raise
    
    async def close(self):
        """Close ArangoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("Closed ArangoDB metrics connection")


if __name__ == "__main__":
    # Test the store
    async def test_store():
        store = ArangoDBMetricsStore()
        
        try:
            # Initialize
            await store.initialize()
            print("✓ Connected to ArangoDB")
            
            # Test storing a metric
            metric = RLMetric(
                state={"task_type": "pdf", "size": 1024},
                action="select_marker",
                reward=0.9,
                module_id="marker"
            )
            key = await store.store_metric(metric)
            print(f"✓ Stored metric with key: {key}")
            
            # Test storing a decision
            decision = ModuleDecision(
                available_modules=["marker", "surya"],
                selected_module="marker",
                selection_probabilities={"marker": 0.8, "surya": 0.2},
                task_type="pdf_extraction",
                task_complexity=0.7,
                success=True,
                reward=0.85
            )
            key = await store.store_decision(decision)
            print(f"✓ Stored decision with key: {key}")
            
            # Test fetching metrics
            metrics = await store.get_recent_metrics(limit=5)
            print(f"✓ Fetched {len(metrics)} recent metrics")
            
            # Test module performance
            perf = await store.get_module_performance("marker")
            print(f"✓ Module performance: {perf}")
            
            await store.close()
            print("✓ Connection closed")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            raise
    
    asyncio.run(test_store())
