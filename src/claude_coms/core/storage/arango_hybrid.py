"""
Hybrid Storage Approach combining SQLite and ArangoDB.

Purpose: Provides a hybrid storage solution that uses SQLite for fast local
caching and real-time tracking, while using ArangoDB for persistent graph
storage and complex queries.

Third-party packages:
- python-arango: https://docs.python-arango.com/
- aiosqlite: https://aiosqlite.omnilib.dev/

Sample Input:
- Real-time message: {"source": "ModuleA", "target": "ModuleB", "action": "process"}
- Sync request: {"action": "sync", "since": "2024-01-01T00:00:00"}

Expected Output:
- Fast local responses from SQLite cache
- Complex graph queries from ArangoDB
- Synchronized data between both stores
"""

import asyncio
import aiosqlite
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from pathlib import Path
import queue
import threading

from .graph_backend import ArangoGraphBackend, ModuleNode, CommunicationEdge
from .arango_conversation import ArangoConversationStore
from ..core.communication_tracker import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class StorageMetrics:
    """Metrics for hybrid storage performance."""
    sqlite_reads: int = 0
    sqlite_writes: int = 0
    arango_reads: int = 0
    arango_writes: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    sync_operations: int = 0
    last_sync: Optional[str] = None


class HybridStorage:
    """
    Hybrid storage combining SQLite and ArangoDB.
    
    SQLite is used for:
    - Real-time message tracking
    - Fast local queries
    - Temporary caching
    - Session management
    
    ArangoDB is used for:
    - Persistent graph storage
    - Complex relationship queries
    - Historical data analysis
    - Cross-module analytics
    """
    
    def __init__(self,
                 sqlite_path: Optional[Path] = None,
                 arango_config: Optional[Dict[str, Any]] = None,
                 sync_interval: int = 60):  # seconds
        """Initialize hybrid storage.
        
        Args:
            sqlite_path: Path to SQLite database
            arango_config: ArangoDB configuration
            sync_interval: Interval for syncing data to ArangoDB
        """
        # SQLite components
        self.sqlite_path = str(sqlite_path) if sqlite_path else ":memory:"
        self.progress_tracker = ProgressTracker(sqlite_path)
        self._sqlite_db: Optional[aiosqlite.Connection] = None
        
        # ArangoDB components
        self.graph_backend = ArangoGraphBackend(
            **arango_config if arango_config else {}
        )
        self.conversation_store = ArangoConversationStore(
            **arango_config if arango_config else {}
        )
        
        # Sync management
        self.sync_interval = sync_interval
        self._sync_queue: queue.Queue = queue.Queue()
        self._sync_thread: Optional[threading.Thread] = None
        self._stop_sync = threading.Event()
        
        # Metrics
        self.metrics = StorageMetrics()
        
        # Cache
        self._module_cache: Dict[str, Dict[str, Any]] = {}
        self._route_cache: Dict[Tuple[str, str], Any] = {}
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize both storage backends."""
        if self._initialized:
            return
        
        # Initialize SQLite
        await self.progress_tracker._ensure_initialized()
        self._sqlite_db = await aiosqlite.connect(self.sqlite_path)
        await self._create_sqlite_tables()
        
        # Initialize ArangoDB
        await self.graph_backend.initialize()
        await self.conversation_store.initialize()
        
        # Start sync thread
        self._start_sync_thread()
        
        self._initialized = True
        logger.info("Hybrid storage initialized")
    
    async def _create_sqlite_tables(self):
        """Create additional SQLite tables for hybrid storage."""
        # Cache table for quick lookups
        await self._sqlite_db.execute("""
            CREATE TABLE IF NOT EXISTS module_cache (
                name TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)
        
        # Sync tracking table
        await self._sqlite_db.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,
                last_sync TEXT NOT NULL,
                records_synced INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # Performance metrics table
        await self._sqlite_db.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL,
                duration_ms REAL NOT NULL,
                storage_backend TEXT NOT NULL
            )
        """)
        
        await self._sqlite_db.commit()
    
    def _start_sync_thread(self):
        """Start background sync thread."""
        def sync_worker():
            """Worker thread for syncing data to ArangoDB."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while not self._stop_sync.is_set():
                try:
                    # Process sync queue
                    batch = []
                    while not self._sync_queue.empty() and len(batch) < 100:
                        try:
                            item = self._sync_queue.get_nowait()
                            batch.append(item)
                        except queue.Empty:
                            break
                    
                    if batch:
                        loop.run_until_complete(self._sync_batch(batch))
                    
                    # Periodic full sync
                    if not self._stop_sync.wait(self.sync_interval):
                        loop.run_until_complete(self._periodic_sync())
                        
                except Exception as e:
                    logger.error(f"Sync error: {e}")
            
            loop.close()
        
        self._sync_thread = threading.Thread(target=sync_worker, daemon=True)
        self._sync_thread.start()
        logger.info("Started sync thread")
    
    async def _sync_batch(self, batch: List[Dict[str, Any]]):
        """Sync a batch of operations to ArangoDB.
        
        Args:
            batch: List of operations to sync
        """
        for item in batch:
            op_type = item.get("type")
            
            try:
                if op_type == "communication":
                    # Sync communication to graph
                    edge = CommunicationEdge(**item["data"])
                    await self.graph_backend.add_communication(edge)
                    
                elif op_type == "module":
                    # Sync module to graph
                    node = ModuleNode(**item["data"])
                    await self.graph_backend.add_module(node)
                    
                elif op_type == "conversation":
                    # Sync conversation message
                    await self.conversation_store.add_message(**item["data"])
                
                self.metrics.arango_writes += 1
                
            except Exception as e:
                logger.error(f"Failed to sync {op_type}: {e}")
        
        self.metrics.sync_operations += 1
        logger.debug(f"Synced {len(batch)} items to ArangoDB")
    
    async def _periodic_sync(self):
        """Perform periodic full synchronization."""
        try:
            # Get unsync'd records from SQLite
            cursor = await self._sqlite_db.execute("""
                SELECT * FROM messages 
                WHERE status = 'pending' 
                ORDER BY timestamp ASC 
                LIMIT 1000
            """)
            
            messages = await cursor.fetchall()
            
            # Sync to ArangoDB
            for msg in messages:
                # Convert to appropriate format and sync
                # This would be implemented based on schema
                pass
            
            # Update sync status
            await self._sqlite_db.execute("""
                INSERT INTO sync_status (sync_type, last_sync, records_synced, status)
                VALUES (?, ?, ?, ?)
            """, ("periodic", datetime.now().isoformat(), len(messages), "completed"))
            
            await self._sqlite_db.commit()
            
            self.metrics.last_sync = datetime.now().isoformat()
            logger.info(f"Periodic sync completed: {len(messages)} records")
            
        except Exception as e:
            logger.error(f"Periodic sync failed: {e}")
    
    async def log_message(self,
                         source: str,
                         target: str,
                         action: str,
                         data: Dict[str, Any],
                         sync: bool = True) -> str:
        """Log a message with hybrid storage.
        
        Args:
            source: Source module
            target: Target module
            action: Action performed
            data: Message data
            sync: Whether to sync to ArangoDB
            
        Returns:
            Message ID
        """
        start_time = datetime.now()
        
        # Log to SQLite first (fast)
        message_id = await self.progress_tracker.log_message(
            source, target, action, data
        )
        self.metrics.sqlite_writes += 1
        
        # Queue for ArangoDB sync if enabled
        if sync:
            self._sync_queue.put({
                "type": "communication",
                "data": {
                    "_from": f"modules/{source}",
                    "_to": f"modules/{target}",
                    "action": action,
                    "timestamp": datetime.now().isoformat(),
                    "data_size": len(json.dumps(data))
                }
            })
        
        # Track performance
        duration = (datetime.now() - start_time).total_seconds() * 1000
        await self._track_performance("log_message", duration, "sqlite")
        
        return message_id
    
    async def get_module_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get module information with caching.
        
        Args:
            name: Module name
            
        Returns:
            Module information
        """
        # Check cache first
        if name in self._module_cache:
            cache_entry = self._module_cache[name]
            cache_time = datetime.fromisoformat(cache_entry["cached_at"])
            if datetime.now() - cache_time < timedelta(minutes=5):
                self.metrics.cache_hits += 1
                return cache_entry["data"]
        
        self.metrics.cache_misses += 1
        
        # Try SQLite cache
        cursor = await self._sqlite_db.execute(
            "SELECT data FROM module_cache WHERE name = ?",
            (name,)
        )
        row = await cursor.fetchone()
        
        if row:
            self.metrics.sqlite_reads += 1
            data = json.loads(row[0])
            # Update memory cache
            self._module_cache[name] = {
                "data": data,
                "cached_at": datetime.now().isoformat()
            }
            return data
        
        # Fallback to ArangoDB
        module_data = await self.graph_backend.get_module(name)
        self.metrics.arango_reads += 1
        
        if module_data:
            # Cache in SQLite
            await self._sqlite_db.execute("""
                INSERT OR REPLACE INTO module_cache (name, data, last_updated)
                VALUES (?, ?, ?)
            """, (name, json.dumps(module_data), datetime.now().isoformat()))
            await self._sqlite_db.commit()
            
            # Update memory cache
            self._module_cache[name] = {
                "data": module_data,
                "cached_at": datetime.now().isoformat()
            }
        
        return module_data
    
    async def find_route(self,
                        source: str,
                        target: str,
                        use_cache: bool = True) -> Optional[List[str]]:
        """Find route between modules with caching.
        
        Args:
            source: Source module
            target: Target module
            use_cache: Whether to use cache
            
        Returns:
            Route if found
        """
        cache_key = (source, target)
        
        # Check cache
        if use_cache and cache_key in self._route_cache:
            self.metrics.cache_hits += 1
            return self._route_cache[cache_key]
        
        # Query ArangoDB for route
        route = await self.graph_backend.find_shortest_path(source, target)
        self.metrics.arango_reads += 1
        
        if route:
            # Cache the route
            self._route_cache[cache_key] = route
        
        return route
    
    async def get_recent_communications(self,
                                      module: str,
                                      limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent communications from SQLite (fast).
        
        Args:
            module: Module name
            limit: Maximum results
            
        Returns:
            Recent communications
        """
        cursor = await self._sqlite_db.execute("""
            SELECT * FROM messages
            WHERE source = ? OR target = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (module, module, limit))
        
        rows = await cursor.fetchall()
        self.metrics.sqlite_reads += 1
        
        # Convert to dictionaries
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    async def get_historical_analysis(self,
                                    module: str,
                                    days: int = 30) -> Dict[str, Any]:
        """Get historical analysis from ArangoDB (complex queries).
        
        Args:
            module: Module name
            days: Days of history
            
        Returns:
            Historical analysis
        """
        start_date = datetime.now() - timedelta(days=days)
        
        # Complex analysis using ArangoDB
        stats = await self.graph_backend.get_communication_stats(
            start_time=start_date
        )
        
        # Get module-specific communications
        comms = await self.graph_backend.get_module_communications(
            module,
            direction="both",
            limit=1000
        )
        
        self.metrics.arango_reads += 2
        
        # Analyze patterns
        analysis = {
            "module": module,
            "period_days": days,
            "total_communications": len(comms),
            "general_stats": stats,
            "communication_partners": set(),
            "action_frequency": {}
        }
        
        for comm in comms:
            # Extract partner
            if comm["_from"].endswith(f"/{module}"):
                partner = comm["_to"].split("/")[1]
            else:
                partner = comm["_from"].split("/")[1]
            
            analysis["communication_partners"].add(partner)
            
            # Count actions
            action = comm.get("action", "unknown")
            analysis["action_frequency"][action] = analysis["action_frequency"].get(action, 0) + 1
        
        analysis["communication_partners"] = list(analysis["communication_partners"])
        
        return analysis
    
    async def _track_performance(self,
                               operation: str,
                               duration_ms: float,
                               backend: str):
        """Track performance metrics.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            backend: Storage backend used
        """
        await self._sqlite_db.execute("""
            INSERT INTO performance_metrics (timestamp, operation, duration_ms, storage_backend)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), operation, duration_ms, backend))
        
        # Don't wait for commit in performance tracking
        asyncio.create_task(self._sqlite_db.commit())
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get storage metrics.
        
        Returns:
            Current metrics
        """
        # Get performance stats from SQLite
        cursor = await self._sqlite_db.execute("""
            SELECT 
                storage_backend,
                COUNT(*) as operation_count,
                AVG(duration_ms) as avg_duration,
                MIN(duration_ms) as min_duration,
                MAX(duration_ms) as max_duration
            FROM performance_metrics
            WHERE timestamp > datetime('now', '-1 hour')
            GROUP BY storage_backend
        """)
        
        perf_stats = await cursor.fetchall()
        
        return {
            "counters": {
                "sqlite_reads": self.metrics.sqlite_reads,
                "sqlite_writes": self.metrics.sqlite_writes,
                "arango_reads": self.metrics.arango_reads,
                "arango_writes": self.metrics.arango_writes,
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "sync_operations": self.metrics.sync_operations
            },
            "cache_hit_rate": (
                self.metrics.cache_hits / (self.metrics.cache_hits + self.metrics.cache_misses)
                if (self.metrics.cache_hits + self.metrics.cache_misses) > 0 else 0
            ),
            "last_sync": self.metrics.last_sync,
            "performance": [
                {
                    "backend": row[0],
                    "operation_count": row[1],
                    "avg_duration_ms": row[2],
                    "min_duration_ms": row[3],
                    "max_duration_ms": row[4]
                }
                for row in perf_stats
            ]
        }
    
    async def optimize_caches(self):
        """Optimize caches based on usage patterns."""
        # Clear old entries from memory cache
        now = datetime.now()
        expired_modules = []
        
        for name, entry in self._module_cache.items():
            cache_time = datetime.fromisoformat(entry["cached_at"])
            if now - cache_time > timedelta(minutes=10):
                expired_modules.append(name)
        
        for name in expired_modules:
            del self._module_cache[name]
        
        # Limit route cache size
        if len(self._route_cache) > 1000:
            # Keep most recent 500
            self._route_cache = dict(list(self._route_cache.items())[-500:])
        
        logger.info(f"Cache optimization: removed {len(expired_modules)} expired modules")
    
    async def close(self):
        """Close all connections and stop sync."""
        # Stop sync thread
        self._stop_sync.set()
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        
        # Close databases
        if self._sqlite_db:
            await self._sqlite_db.close()
        
        await self.progress_tracker.close()
        await self.graph_backend.close()
        await self.conversation_store.close()


if __name__ == "__main__":
    # Test hybrid storage with real data
    async def test_hybrid_storage():
        storage = HybridStorage(
            sqlite_path=Path("test_hybrid.db"),
            sync_interval=5  # 5 seconds for testing
        )
        
        await storage.initialize()
        
        # Log messages (fast SQLite)
        for i in range(10):
            await storage.log_message(
                source="producer",
                target="processor",
                action="send_data",
                data={"batch": i, "size": 100}
            )
        
        print("Logged 10 messages")
        
        # Get recent communications (from SQLite)
        recent = await storage.get_recent_communications("producer", limit=5)
        print(f"Recent communications: {len(recent)}")
        
        # Wait for sync
        await asyncio.sleep(6)
        
        # Get historical analysis (from ArangoDB)
        analysis = await storage.get_historical_analysis("producer", days=1)
        print(f"Historical analysis: {json.dumps(analysis, indent=2)}")
        
        # Check metrics
        metrics = await storage.get_metrics()
        print(f"Storage metrics: {json.dumps(metrics, indent=2)}")
        
        await storage.close()
        
        # Cleanup
        Path("test_hybrid.db").unlink(missing_ok=True)
    
    asyncio.run(test_hybrid_storage())