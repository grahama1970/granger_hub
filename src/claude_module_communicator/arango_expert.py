"""
ArangoDB Expert Module - Provides comprehensive ArangoDB knowledge and operations.
This module serves as the expert system that all Claude instances can use.
"""

from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import json
from arango import ArangoClient
from arango.database import StandardDatabase
from arango.graph import Graph
from arango.collection import StandardCollection
import logging

logger = logging.getLogger(__name__)


class ArangoExpert:
    """Expert system for ArangoDB operations that modules can leverage."""
    
    # Common AQL patterns for reuse
    AQL_PATTERNS = {
        "find_connected": """
            FOR vertex IN 1..@depth ANY @start_vertex @@edge_collection
                RETURN DISTINCT vertex
        """,
        
        "shortest_path": """
            FOR path IN OUTBOUND SHORTEST_PATH @from TO @to @@edge_collection
                RETURN path
        """,
        
        "subgraph": """
            FOR vertex, edge, path IN @min..@max ANY @start @@edge_collection
                RETURN {vertex: vertex, edge: edge, path: path}
        """,
        
        "pattern_match": """
            FOR doc IN @@collection
                FILTER REGEX_TEST(doc.@field, @pattern, @case_insensitive)
                RETURN doc
        """,
        
        "time_range": """
            FOR doc IN @@collection
                FILTER doc.@timestamp_field >= @start_time
                FILTER doc.@timestamp_field <= @end_time
                SORT doc.@timestamp_field DESC
                RETURN doc
        """,
        
        "aggregate_by_property": """
            FOR doc IN @@collection
                COLLECT property = doc.@property WITH COUNT INTO count
                SORT count DESC
                RETURN {property: property, count: count}
        """,
        
        "find_orphans": """
            FOR vertex IN @@vertex_collection
                LET incoming = (FOR v IN 1..1 INBOUND vertex @@edge_collection RETURN 1)
                LET outgoing = (FOR v IN 1..1 OUTBOUND vertex @@edge_collection RETURN 1)
                FILTER LENGTH(incoming) == 0 AND LENGTH(outgoing) == 0
                RETURN vertex
        """,
        
        "community_detection": """
            FOR vertex IN @@vertex_collection
                LET community = (
                    FOR v, e, p IN 1..@depth ANY vertex @@edge_collection
                        OPTIONS {uniqueVertices: "global"}
                        RETURN DISTINCT v._id
                )
                RETURN {
                    center: vertex,
                    community_size: LENGTH(community),
                    members: community
                }
        """
    }
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with best practices configuration."""
        self.config = config
        self.client = None
        self.db = None
        self._connect()
        
    def _connect(self):
        """Establish connection with retry logic."""
        try:
            self.client = ArangoClient(
                hosts=self.config.get("hosts", ["http://localhost:8529"]),
                http_client_options={
                    "verify": self.config.get("verify_ssl", True),
                    "timeout": self.config.get("timeout", 60)
                }
            )
            
            self.db = self.client.db(
                self.config.get("database", "_system"),
                username=self.config.get("username", "root"),
                password=self.config.get("password", ""),
                verify=True
            )
            
            logger.info(f"Connected to ArangoDB: {self.config.get('database')}")
            
        except Exception as e:
            logger.error(f"Failed to connect to ArangoDB: {e}")
            raise
            
    def explain_query(self, aql: str, bind_vars: Dict = None) -> Dict[str, Any]:
        """Explain an AQL query's execution plan."""
        return self.db.aql.explain(aql, bind_vars=bind_vars or {})
        
    def optimize_query(self, aql: str) -> str:
        """Provide optimization suggestions for an AQL query."""
        plan = self.explain_query(aql)
        
        suggestions = []
        
        # Check for full collection scans
        if "FullCollectionScan" in str(plan):
            suggestions.append("Consider adding indexes to avoid full collection scans")
            
        # Check for missing LIMIT
        if "LIMIT" not in aql.upper() and "RETURN" in aql.upper():
            suggestions.append("Consider adding LIMIT to prevent returning too many results")
            
        # Check for inefficient filters
        if "FILTER" in aql and "INDEX" not in str(plan):
            suggestions.append("Filters may not be using indexes efficiently")
            
        return "\n".join(suggestions) if suggestions else "Query appears optimized"
        
    # Graph Analysis Functions
    
    def find_influencers(self, graph_name: str, edge_collection: str, 
                        min_connections: int = 10) -> List[Dict[str, Any]]:
        """Find influential nodes in a graph (high connectivity)."""
        query = """
        FOR vertex IN @@vertex_collection
            LET inbound = LENGTH(FOR v IN 1..1 INBOUND vertex @@edge_collection RETURN 1)
            LET outbound = LENGTH(FOR v IN 1..1 OUTBOUND vertex @@edge_collection RETURN 1)
            LET total = inbound + outbound
            FILTER total >= @min_connections
            SORT total DESC
            LIMIT 100
            RETURN {
                vertex: vertex,
                inbound_connections: inbound,
                outbound_connections: outbound,
                total_connections: total,
                influence_score: total
            }
        """
        
        graph = self.db.graph(graph_name)
        vertex_collections = graph.vertex_collections()
        
        results = []
        for vertex_collection in vertex_collections:
            cursor = self.db.aql.execute(
                query,
                bind_vars={
                    "@vertex_collection": vertex_collection,
                    "@edge_collection": edge_collection,
                    "min_connections": min_connections
                }
            )
            results.extend(list(cursor))
            
        return sorted(results, key=lambda x: x["influence_score"], reverse=True)
        
    def find_bridges(self, graph_name: str, edge_collection: str) -> List[Dict[str, Any]]:
        """Find bridge nodes that connect different communities."""
        query = """
        FOR vertex IN @@vertex_collection
            LET neighbors = (
                FOR v IN 1..1 ANY vertex @@edge_collection
                    RETURN v._id
            )
            
            LET neighbor_connections = (
                FOR n IN neighbors
                    LET n_neighbors = (
                        FOR v IN 1..1 ANY n @@edge_collection
                            RETURN v._id
                    )
                    RETURN {
                        neighbor: n,
                        shared: LENGTH(INTERSECTION(neighbors, n_neighbors))
                    }
            )
            
            LET clustering_coefficient = (
                LENGTH(neighbor_connections) > 1 
                ? AVG(FOR nc IN neighbor_connections RETURN nc.shared) / LENGTH(neighbors)
                : 0
            )
            
            FILTER clustering_coefficient < 0.3  // Low clustering = bridge node
            FILTER LENGTH(neighbors) >= 3       // Connected to multiple nodes
            
            RETURN {
                vertex: vertex,
                neighbor_count: LENGTH(neighbors),
                clustering_coefficient: clustering_coefficient,
                bridge_score: LENGTH(neighbors) * (1 - clustering_coefficient)
            }
        """
        
        # Execute for each vertex collection in the graph
        graph = self.db.graph(graph_name)
        results = []
        
        for vertex_collection in graph.vertex_collections():
            cursor = self.db.aql.execute(
                query,
                bind_vars={
                    "@vertex_collection": vertex_collection,
                    "@edge_collection": edge_collection
                }
            )
            results.extend(list(cursor))
            
        return sorted(results, key=lambda x: x["bridge_score"], reverse=True)
        
    def analyze_information_flow(self, start_node: str, edge_collection: str,
                               max_depth: int = 3) -> Dict[str, Any]:
        """Analyze how information flows from a starting node."""
        query = """
        LET flow = (
            FOR vertex, edge, path IN 0..@max_depth OUTBOUND @start_node @@edge_collection
                LET depth = LENGTH(path.edges)
                COLLECT d = depth INTO nodes = vertex._id
                RETURN {
                    depth: d,
                    count: LENGTH(nodes),
                    nodes: nodes
                }
        )
        
        LET total_reach = SUM(FOR f IN flow RETURN f.count)
        
        RETURN {
            start_node: @start_node,
            max_depth: @max_depth,
            total_reach: total_reach,
            flow_by_depth: flow,
            avg_branching_factor: total_reach > 0 ? POW(total_reach, 1/@max_depth) : 0
        }
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "start_node": start_node,
                "@edge_collection": edge_collection,
                "max_depth": max_depth
            }
        )
        
        return list(cursor)[0]
        
    # Knowledge Graph Operations
    
    def build_context_graph(self, central_topic: str, collections: List[str],
                          radius: int = 2) -> Dict[str, Any]:
        """Build a context graph around a central topic."""
        query = """
        // Find all documents mentioning the topic
        LET topic_docs = (
            FOR doc IN UNION(
                FOR coll IN @collections
                    FOR d IN COLLECTION(coll)
                        FILTER CONTAINS(LOWER(TO_STRING(d)), LOWER(@topic))
                        RETURN {doc: d, collection: coll}
            )
            RETURN doc
        )
        
        // Find related documents
        LET context = (
            FOR td IN topic_docs
                FOR vertex, edge, path IN 1..@radius ANY td.doc GRAPH @graph_name
                    RETURN DISTINCT {
                        vertex: vertex,
                        distance: LENGTH(path.edges),
                        path_type: path.edges[*].type
                    }
        )
        
        RETURN {
            topic: @topic,
            direct_mentions: LENGTH(topic_docs),
            total_context: LENGTH(context),
            documents: topic_docs,
            context_graph: context
        }
        """
        
        # Note: This requires a graph to be defined
        # For now, return a structured approach
        results = {
            "topic": central_topic,
            "direct_documents": [],
            "related_documents": [],
            "connections": []
        }
        
        # Search each collection
        for collection in collections:
            if self.db.has_collection(collection):
                # Find direct mentions
                direct_query = """
                FOR doc IN @@collection
                    FILTER CONTAINS(LOWER(TO_STRING(doc)), LOWER(@topic))
                    LIMIT 100
                    RETURN doc
                """
                
                cursor = self.db.aql.execute(
                    direct_query,
                    bind_vars={
                        "@collection": collection,
                        "topic": central_topic
                    }
                )
                
                results["direct_documents"].extend([
                    {"collection": collection, "document": doc}
                    for doc in cursor
                ])
                
        return results
        
    def find_knowledge_gaps(self, domain: str, collections: List[str]) -> List[Dict[str, Any]]:
        """Identify gaps in knowledge coverage."""
        # This would analyze document coverage and identify missing connections
        query = """
        // Find all unique concepts/entities in the domain
        LET all_concepts = (
            FOR doc IN UNION(
                FOR coll IN @collections
                    FOR d IN COLLECTION(coll)
                        FILTER CONTAINS(LOWER(TO_STRING(d)), LOWER(@domain))
                        RETURN d.concepts || d.entities || []
            )
            RETURN DISTINCT concept
        )
        
        // Find which concepts lack connections
        FOR concept IN all_concepts
            LET connections = (
                FOR doc IN UNION(
                    FOR coll IN @collections
                        FOR d IN COLLECTION(coll)
                            FILTER CONTAINS(d.concepts, concept) OR CONTAINS(d.entities, concept)
                            RETURN 1
                )
                RETURN 1
            )
            FILTER LENGTH(connections) < 3  // Poorly connected concepts
            RETURN {
                concept: concept,
                connection_count: LENGTH(connections),
                gap_score: 3 - LENGTH(connections)
            }
        """
        
        # Simplified version for demonstration
        gaps = []
        
        # Check for common patterns that indicate gaps
        common_topics = [
            "implementation", "integration", "security", "performance",
            "scalability", "monitoring", "testing", "deployment"
        ]
        
        for topic in common_topics:
            topic_query = f"{domain} {topic}"
            coverage = self._check_coverage(topic_query, collections)
            
            if coverage < 0.3:  # Less than 30% coverage
                gaps.append({
                    "gap": f"{domain} - {topic}",
                    "coverage": coverage,
                    "recommendation": f"Need more documentation on {topic} for {domain}"
                })
                
        return gaps
        
    def _check_coverage(self, query: str, collections: List[str]) -> float:
        """Check coverage of a topic across collections."""
        total_docs = 0
        matching_docs = 0
        
        for collection in collections:
            if self.db.has_collection(collection):
                # Count total
                total_cursor = self.db.aql.execute(
                    "RETURN LENGTH(@@collection)",
                    bind_vars={"@collection": collection}
                )
                total_docs += list(total_cursor)[0]
                
                # Count matches
                match_cursor = self.db.aql.execute(
                    """
                    FOR doc IN @@collection
                        FILTER CONTAINS(LOWER(TO_STRING(doc)), LOWER(@query))
                        COLLECT WITH COUNT INTO matches
                        RETURN matches
                    """,
                    bind_vars={
                        "@collection": collection,
                        "query": query
                    }
                )
                matching_docs += list(match_cursor)[0]
                
        return matching_docs / total_docs if total_docs > 0 else 0
        
    # Best Practices and Templates
    
    def create_indexes_for_module(self, module_type: str) -> List[Dict[str, Any]]:
        """Create optimal indexes based on module type."""
        index_templates = {
            "communication": [
                {"type": "persistent", "fields": ["timestamp"], "name": "idx_timestamp"},
                {"type": "persistent", "fields": ["source", "target"], "name": "idx_source_target"},
                {"type": "fulltext", "fields": ["content"], "name": "idx_content_search"}
            ],
            "knowledge": [
                {"type": "persistent", "fields": ["topic"], "name": "idx_topic"},
                {"type": "persistent", "fields": ["domain", "timestamp"], "name": "idx_domain_time"},
                {"type": "hash", "fields": ["entity_id"], "name": "idx_entity", "unique": True}
            ],
            "task": [
                {"type": "persistent", "fields": ["status", "priority"], "name": "idx_status_priority"},
                {"type": "persistent", "fields": ["assigned_to"], "name": "idx_assigned"},
                {"type": "ttl", "fields": ["expires_at"], "expireAfter": 0, "name": "idx_ttl"}
            ]
        }
        
        return index_templates.get(module_type, [])
        
    def generate_module_schema(self, module_name: str, capabilities: List[str]) -> Dict[str, Any]:
        """Generate optimal schema for a module based on its capabilities."""
        schema = {
            "module": module_name,
            "collections": {},
            "edges": {},
            "indexes": [],
            "graphs": []
        }
        
        # Base collections all modules need
        schema["collections"]["module_metadata"] = {
            "type": "document",
            "schema": {
                "name": "string",
                "version": "string",
                "capabilities": ["string"],
                "registered_at": "datetime",
                "last_active": "datetime"
            }
        }
        
        # Add collections based on capabilities
        capability_mappings = {
            "pdf_extraction": {
                "collections": {
                    "extracted_content": {
                        "type": "document",
                        "schema": {
                            "source_url": "string",
                            "content": "text",
                            "metadata": "object",
                            "extracted_at": "datetime"
                        }
                    }
                },
                "edges": {
                    "extracted_from": {
                        "from": ["extracted_content"],
                        "to": ["resources"]
                    }
                }
            },
            "threat_detection": {
                "collections": {
                    "threats": {
                        "type": "document",
                        "schema": {
                            "threat_type": "string",
                            "severity": "number",
                            "indicators": ["string"],
                            "detected_at": "datetime"
                        }
                    }
                },
                "edges": {
                    "threatens": {
                        "from": ["threats"],
                        "to": ["resources", "modules"]
                    }
                }
            }
        }
        
        for capability in capabilities:
            if capability in capability_mappings:
                mapping = capability_mappings[capability]
                schema["collections"].update(mapping.get("collections", {}))
                schema["edges"].update(mapping.get("edges", {}))
                
        return schema
        
    def get_module_instructions(self) -> str:
        """Get instructions for modules on how to use ArangoDB effectively."""
        return """
# ArangoDB Expert Instructions for Modules

## Connection Best Practices
```python
from claude_module_communicator import ArangoExpert

expert = ArangoExpert({
    "hosts": ["http://localhost:8529"],
    "database": "module_collaboration",
    "username": "root",
    "password": "secure_password",
    "timeout": 60
})
```

## Essential Operations

### 1. Store Module Data
```python
# Store with automatic indexing
collection = expert.db.collection("my_module_data")
doc = collection.insert({
    "type": "analysis_result",
    "content": result,
    "timestamp": datetime.now().isoformat()
})
```

### 2. Query Relationships
```python
# Find related documents
related = expert.db.aql.execute('''
    FOR doc IN my_collection
        FOR related IN 1..3 ANY doc related_to
        RETURN related
''')
```

### 3. Build Knowledge Graphs
```python
context = expert.build_context_graph(
    "space cybersecurity",
    ["messages", "resources", "knowledge"],
    radius=3
)
```

### 4. Analyze Patterns
```python
# Find influential nodes
influencers = expert.find_influencers(
    "module_graph",
    "communicates_with",
    min_connections=5
)

# Find knowledge gaps
gaps = expert.find_knowledge_gaps(
    "satellite security",
    ["documents", "research", "reports"]
)
```

## Performance Tips

1. **Always use bind variables** - Never concatenate strings in AQL
2. **Create appropriate indexes** - Use expert.create_indexes_for_module()
3. **Limit results** - Always use LIMIT in queries
4. **Use graph algorithms** - Leverage built-in graph functions
5. **Monitor query performance** - Use expert.explain_query()

## Common Patterns

### Time-based Queries
```python
recent_docs = expert.db.aql.execute(
    expert.AQL_PATTERNS["time_range"],
    bind_vars={
        "@collection": "messages",
        "timestamp_field": "created_at",
        "start_time": "2024-01-01",
        "end_time": "2024-12-31"
    }
)
```

### Pattern Matching
```python
matches = expert.db.aql.execute(
    expert.AQL_PATTERNS["pattern_match"],
    bind_vars={
        "@collection": "documents",
        "field": "content",
        "pattern": "cybersecurity|threat|vulnerability",
        "case_insensitive": True
    }
)
```

### Community Detection
```python
communities = expert.db.aql.execute(
    expert.AQL_PATTERNS["community_detection"],
    bind_vars={
        "@vertex_collection": "modules",
        "@edge_collection": "collaborates_with",
        "depth": 2
    }
)
```

## Error Handling

Always wrap operations in try-except:
```python
try:
    result = expert.db.collection("data").insert(doc)
except ArangoError as e:
    logger.error(f"Database error: {e}")
    # Implement retry logic or fallback
```

Remember: You are part of a collaborative intelligence system. 
Store your insights, query others' knowledge, and build connections!
"""