"""
ArangoDB Graph Backend for Module Communication.

Purpose: Provides graph database storage and querying capabilities for
tracking module relationships, communication patterns, and dependencies.

Third-party packages:
- python-arango: https://docs.python-arango.com/
- asyncio: Python standard library

Sample Input:
- Module relationships: {"source": "ModuleA", "target": "ModuleB", "type": "depends_on"}
- Communication patterns: {"from": "ModuleA", "to": "ModuleB", "action": "process", "timestamp": "2024-01-01T00:00:00"}

Expected Output:
- Graph structure with nodes (modules) and edges (relationships/communications)
- Query results for module dependencies, communication patterns, etc.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import json

from arango import ArangoClient
from arango.database import StandardDatabase
from arango.graph import Graph
from arango.exceptions import DocumentInsertError, GraphCreateError

logger = logging.getLogger(__name__)


@dataclass
class ModuleNode:
    """Represents a module in the graph."""
    _key: str  # Module name as key
    name: str
    system_prompt: str
    capabilities: List[str]
    created_at: str
    updated_at: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ArangoDB."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class CommunicationEdge:
    """Represents a communication between modules."""
    _from: str  # Source module (modules/name)
    _to: str    # Target module (modules/name)
    action: str
    timestamp: str
    success: bool = True
    data_size: Optional[int] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ArangoDB."""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ArangoGraphBackend:
    """Graph backend using ArangoDB for module communication tracking."""
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 8529,
                 username: str = "root",
                 password: str = "",
                 database: str = "claude_modules"):
        """Initialize ArangoDB connection.
        
        Args:
            host: ArangoDB host
            port: ArangoDB port
            username: Database username
            password: Database password
            database: Database name
        """
        self.client = ArangoClient(hosts=f"http://{host}:{port}")
        self.database_name = database
        self.username = username
        self.password = password
        self.db: Optional[StandardDatabase] = None
        self.graph: Optional[Graph] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database and graph structures."""
        if self._initialized:
            return
        
        try:
            # Connect to system database
            sys_db = self.client.db("_system", username=self.username, password=self.password)
            
            # Create database if it doesn't exist
            if not sys_db.has_database(self.database_name):
                sys_db.create_database(self.database_name)
                logger.info(f"Created database: {self.database_name}")
            
            # Connect to our database
            self.db = self.client.db(self.database_name, username=self.username, password=self.password)
            
            # Create collections
            await self._create_collections()
            
            # Create graph
            await self._create_graph()
            
            # Create indexes
            await self._create_indexes()
            
            self._initialized = True
            logger.info("ArangoDB graph backend initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize ArangoDB: {e}")
            raise
    
    async def _create_collections(self):
        """Create required collections."""
        # Module nodes collection
        if not self.db.has_collection("modules"):
            self.db.create_collection("modules")
            logger.info("Created 'modules' collection")
        
        # Communication edges collection
        if not self.db.has_collection("communications"):
            self.db.create_collection("communications", edge=True)
            logger.info("Created 'communications' edge collection")
        
        # Dependencies edges collection
        if not self.db.has_collection("dependencies"):
            self.db.create_collection("dependencies", edge=True)
            logger.info("Created 'dependencies' edge collection")
        
        # Capabilities collection
        if not self.db.has_collection("capabilities"):
            self.db.create_collection("capabilities")
            logger.info("Created 'capabilities' collection")
    
    async def _create_graph(self):
        """Create the module communication graph."""
        graph_name = "module_graph"
        
        if not self.db.has_graph(graph_name):
            try:
                self.graph = self.db.create_graph(
                    name=graph_name,
                    edge_definitions=[
                        {
                            "edge_collection": "communications",
                            "from_vertex_collections": ["modules"],
                            "to_vertex_collections": ["modules"]
                        },
                        {
                            "edge_collection": "dependencies",
                            "from_vertex_collections": ["modules"],
                            "to_vertex_collections": ["modules"]
                        }
                    ]
                )
                logger.info(f"Created graph: {graph_name}")
            except GraphCreateError:
                self.graph = self.db.graph(graph_name)
        else:
            self.graph = self.db.graph(graph_name)
    
    async def _create_indexes(self):
        """Create indexes for efficient querying."""
        # Index on module capabilities
        modules = self.db.collection("modules")
        modules.add_persistent_index(fields=["capabilities[*]"], unique=False)
        
        # Index on communication timestamps
        communications = self.db.collection("communications")
        communications.add_persistent_index(fields=["timestamp"], unique=False)
        communications.add_persistent_index(fields=["action"], unique=False)
        
        # Index on communication success
        communications.add_persistent_index(fields=["success"], unique=False)
    
    async def add_module(self, module: ModuleNode) -> bool:
        """Add a module node to the graph.
        
        Args:
            module: Module to add
            
        Returns:
            True if successful
        """
        try:
            modules = self.db.collection("modules")
            modules.insert(module.to_dict())
            logger.info(f"Added module: {module.name}")
            return True
        except DocumentInsertError as e:
            if e.error_code == 1210:  # Duplicate key
                # Update existing module
                modules.update_match(
                    {"_key": module._key},
                    module.to_dict()
                )
                logger.info(f"Updated module: {module.name}")
                return True
            logger.error(f"Failed to add module: {e}")
            return False
    
    async def add_communication(self, edge: CommunicationEdge) -> bool:
        """Add a communication edge to the graph.
        
        Args:
            edge: Communication edge to add
            
        Returns:
            True if successful
        """
        try:
            communications = self.db.collection("communications")
            communications.insert(edge.to_dict())
            return True
        except Exception as e:
            logger.error(f"Failed to add communication: {e}")
            return False
    
    async def add_dependency(self, source: str, target: str, dep_type: str = "depends_on") -> bool:
        """Add a dependency between modules.
        
        Args:
            source: Source module name
            target: Target module name
            dep_type: Type of dependency
            
        Returns:
            True if successful
        """
        try:
            dependencies = self.db.collection("dependencies")
            dependencies.insert({
                "_from": f"modules/{source}",
                "_to": f"modules/{target}",
                "type": dep_type,
                "created_at": datetime.now().isoformat()
            })
            return True
        except DocumentInsertError:
            # Dependency already exists
            return True
        except Exception as e:
            logger.error(f"Failed to add dependency: {e}")
            return False
    
    async def get_module(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a module by name.
        
        Args:
            name: Module name
            
        Returns:
            Module data if found
        """
        try:
            modules = self.db.collection("modules")
            return modules.get(name)
        except Exception:
            return None
    
    async def get_module_dependencies(self, name: str) -> List[Dict[str, Any]]:
        """Get all dependencies of a module.
        
        Args:
            name: Module name
            
        Returns:
            List of dependent modules
        """
        query = """
        FOR v, e IN 1..1 OUTBOUND @start_vertex dependencies
            RETURN {module: v, dependency: e}
        """
        cursor = self.db.aql.execute(
            query,
            bind_vars={"start_vertex": f"modules/{name}"}
        )
        return list(cursor)
    
    async def get_module_communications(self, 
                                      name: str,
                                      direction: str = "both",
                                      limit: int = 100) -> List[Dict[str, Any]]:
        """Get communications for a module.
        
        Args:
            name: Module name
            direction: "in", "out", or "both"
            limit: Maximum number of results
            
        Returns:
            List of communications
        """
        if direction == "out":
            query = """
            FOR e IN communications
                FILTER e._from == @module
                SORT e.timestamp DESC
                LIMIT @limit
                RETURN e
            """
        elif direction == "in":
            query = """
            FOR e IN communications
                FILTER e._to == @module
                SORT e.timestamp DESC
                LIMIT @limit
                RETURN e
            """
        else:  # both
            query = """
            FOR e IN communications
                FILTER e._from == @module OR e._to == @module
                SORT e.timestamp DESC
                LIMIT @limit
                RETURN e
            """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "module": f"modules/{name}",
                "limit": limit
            }
        )
        return list(cursor)
    
    async def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """Find shortest communication path between modules.
        
        Args:
            source: Source module name
            target: Target module name
            
        Returns:
            List of module names in the path
        """
        query = """
        FOR path IN K_SHORTEST_PATHS
            @source TO @target
            GRAPH 'module_graph'
            LIMIT 1
            RETURN path.vertices[*].name
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "source": f"modules/{source}",
                "target": f"modules/{target}"
            }
        )
        
        try:
            result = next(cursor)
            return result[0] if result else None
        except StopIteration:
            return None
    
    async def get_communication_stats(self, 
                                    start_time: Optional[datetime] = None,
                                    end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get communication statistics.
        
        Args:
            start_time: Start time filter
            end_time: End time filter
            
        Returns:
            Statistics dictionary
        """
        filters = []
        bind_vars = {}
        
        if start_time:
            filters.append("e.timestamp >= @start_time")
            bind_vars["start_time"] = start_time.isoformat()
        
        if end_time:
            filters.append("e.timestamp <= @end_time")
            bind_vars["end_time"] = end_time.isoformat()
        
        filter_clause = f"FILTER {' AND '.join(filters)}" if filters else ""
        
        query = f"""
        LET total = (
            FOR e IN communications
                {filter_clause}
                RETURN 1
        )
        LET successful = (
            FOR e IN communications
                {filter_clause}
                FILTER e.success == true
                RETURN 1
        )
        LET by_action = (
            FOR e IN communications
                {filter_clause}
                COLLECT action = e.action WITH COUNT INTO count
                RETURN {{action: action, count: count}}
        )
        LET avg_duration = (
            FOR e IN communications
                {filter_clause}
                FILTER e.duration_ms != null
                RETURN e.duration_ms
        )
        
        RETURN {{
            total_communications: LENGTH(total),
            successful_communications: LENGTH(successful),
            success_rate: LENGTH(total) > 0 ? LENGTH(successful) / LENGTH(total) : 0,
            by_action: by_action,
            avg_duration_ms: LENGTH(avg_duration) > 0 ? AVG(avg_duration) : 0
        }}
        """
        
        cursor = self.db.aql.execute(query, bind_vars=bind_vars)
        return next(cursor)
    
    async def get_module_graph_structure(self) -> Dict[str, Any]:
        """Get the entire module graph structure.
        
        Returns:
            Graph structure with nodes and edges
        """
        # Get all modules
        modules_query = "FOR m IN modules RETURN m"
        modules = list(self.db.aql.execute(modules_query))
        
        # Get all communications
        comm_query = "FOR c IN communications RETURN c"
        communications = list(self.db.aql.execute(comm_query))
        
        # Get all dependencies
        dep_query = "FOR d IN dependencies RETURN d"
        dependencies = list(self.db.aql.execute(dep_query))
        
        return {
            "nodes": modules,
            "edges": {
                "communications": communications,
                "dependencies": dependencies
            },
            "stats": {
                "module_count": len(modules),
                "communication_count": len(communications),
                "dependency_count": len(dependencies)
            }
        }
    
    async def cleanup_old_communications(self, days: int = 30) -> int:
        """Remove old communication records.
        
        Args:
            days: Remove communications older than this many days
            
        Returns:
            Number of removed records
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        cutoff_date = datetime.fromtimestamp(cutoff).isoformat()
        
        query = """
        FOR e IN communications
            FILTER e.timestamp < @cutoff
            REMOVE e IN communications
            RETURN 1
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={"cutoff": cutoff_date}
        )
        
        count = len(list(cursor))
        logger.info(f"Removed {count} old communication records")
        return count
    
    async def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()


if __name__ == "__main__":
    # Test the graph backend with real data
    async def test_graph_backend():
        backend = ArangoGraphBackend()
        await backend.initialize()
        
        # Add test modules
        module1 = ModuleNode(
            _key="data_producer",
            name="data_producer",
            system_prompt="Produces data for processing",
            capabilities=["data_generation", "streaming"],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        module2 = ModuleNode(
            _key="data_processor",
            name="data_processor",
            system_prompt="Processes incoming data",
            capabilities=["data_processing", "transformation"],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        await backend.add_module(module1)
        await backend.add_module(module2)
        
        # Add communication
        comm = CommunicationEdge(
            _from="modules/data_producer",
            _to="modules/data_processor",
            action="process",
            timestamp=datetime.now().isoformat(),
            success=True,
            data_size=1024,
            duration_ms=15.5
        )
        
        await backend.add_communication(comm)
        
        # Add dependency
        await backend.add_dependency("data_processor", "data_producer")
        
        # Query communications
        comms = await backend.get_module_communications("data_producer", direction="out")
        print(f"Producer communications: {len(comms)}")
        
        # Get stats
        stats = await backend.get_communication_stats()
        print(f"Communication stats: {stats}")
        
        # Find path
        path = await backend.find_shortest_path("data_producer", "data_processor")
        print(f"Path: {path}")
        
        await backend.close()
    
    asyncio.run(test_graph_backend())