"""
Graph-based backend for module communication using ArangoDB.
Enables relationship tracking, knowledge graphs, and intelligent discovery.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
from arango import ArangoClient
from arango.database import StandardDatabase
from arango.exceptions import DocumentInsertError, ArangoError
import logging

logger = logging.getLogger(__name__)


class GraphBackend:
    """ArangoDB backend for graph-based module communication."""
    
    # Vertex collections
    MODULES = "modules"
    MESSAGES = "messages"
    SCHEMAS = "schemas"
    RESOURCES = "resources"
    KNOWLEDGE = "knowledge"
    TASKS = "tasks"
    
    # Edge collections
    SENDS = "sends"
    RECEIVES = "receives"
    REFERENCES = "references"
    REQUIRES = "requires"
    PROVIDES = "provides"
    RELATED_TO = "related_to"
    DERIVED_FROM = "derived_from"
    COLLABORATES_ON = "collaborates_on"
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize ArangoDB connection."""
        self.config = config
        self.client = ArangoClient(hosts=config.get("hosts", ["http://localhost:8529"]))
        self.db = self._connect_db()
        self._setup_collections()
        self._setup_graph()
        
    def _connect_db(self) -> StandardDatabase:
        """Connect to ArangoDB database."""
        try:
            sys_db = self.client.db("_system", 
                                   username=self.config.get("username", "root"),
                                   password=self.config.get("password", ""))
            
            db_name = self.config.get("database", "module_collaboration")
            
            # Create database if it doesn't exist
            if not sys_db.has_database(db_name):
                sys_db.create_database(db_name)
                
            # Connect to the database
            return self.client.db(db_name,
                                username=self.config.get("username", "root"),
                                password=self.config.get("password", ""))
                                
        except ArangoError as e:
            logger.error(f"Failed to connect to ArangoDB: {e}")
            raise
            
    def _setup_collections(self):
        """Create vertex and edge collections if they don't exist."""
        # Vertex collections
        vertex_collections = [
            self.MODULES, self.MESSAGES, self.SCHEMAS,
            self.RESOURCES, self.KNOWLEDGE, self.TASKS
        ]
        
        for collection in vertex_collections:
            if not self.db.has_collection(collection):
                self.db.create_collection(collection)
                logger.info(f"Created vertex collection: {collection}")
                
        # Edge collections
        edge_collections = [
            self.SENDS, self.RECEIVES, self.REFERENCES,
            self.REQUIRES, self.PROVIDES, self.RELATED_TO,
            self.DERIVED_FROM, self.COLLABORATES_ON
        ]
        
        for collection in edge_collections:
            if not self.db.has_collection(collection):
                self.db.create_collection(collection, edge=True)
                logger.info(f"Created edge collection: {collection}")
                
    def _setup_graph(self):
        """Create graph definition."""
        graph_name = "module_collaboration_graph"
        
        if not self.db.has_graph(graph_name):
            self.db.create_graph(
                graph_name,
                edge_definitions=[
                    {
                        "edge_collection": self.SENDS,
                        "from_vertex_collections": [self.MODULES],
                        "to_vertex_collections": [self.MESSAGES]
                    },
                    {
                        "edge_collection": self.RECEIVES,
                        "from_vertex_collections": [self.MESSAGES],
                        "to_vertex_collections": [self.MODULES]
                    },
                    {
                        "edge_collection": self.REFERENCES,
                        "from_vertex_collections": [self.MESSAGES],
                        "to_vertex_collections": [self.RESOURCES]
                    },
                    {
                        "edge_collection": self.REQUIRES,
                        "from_vertex_collections": [self.MODULES],
                        "to_vertex_collections": [self.SCHEMAS]
                    },
                    {
                        "edge_collection": self.PROVIDES,
                        "from_vertex_collections": [self.MODULES],
                        "to_vertex_collections": [self.SCHEMAS]
                    },
                    {
                        "edge_collection": self.RELATED_TO,
                        "from_vertex_collections": [self.MESSAGES],
                        "to_vertex_collections": [self.MESSAGES]
                    },
                    {
                        "edge_collection": self.DERIVED_FROM,
                        "from_vertex_collections": [self.KNOWLEDGE],
                        "to_vertex_collections": [self.RESOURCES]
                    },
                    {
                        "edge_collection": self.COLLABORATES_ON,
                        "from_vertex_collections": [self.MODULES],
                        "to_vertex_collections": [self.TASKS]
                    }
                ]
            )
            logger.info(f"Created graph: {graph_name}")
            
    def register_module(self, module_name: str, capabilities: List[str], 
                       description: str = "") -> str:
        """Register a module in the graph."""
        module_doc = {
            "_key": module_name,
            "name": module_name,
            "capabilities": capabilities,
            "description": description,
            "registered_at": datetime.now().isoformat(),
            "active": True
        }
        
        try:
            result = self.db.collection(self.MODULES).insert(module_doc)
            logger.info(f"Registered module: {module_name}")
            return result["_id"]
        except DocumentInsertError:
            # Module already exists, update it
            self.db.collection(self.MODULES).update({
                "_key": module_name,
                "capabilities": capabilities,
                "description": description,
                "last_seen": datetime.now().isoformat(),
                "active": True
            })
            return f"{self.MODULES}/{module_name}"
            
    def store_message(self, message: Dict[str, Any], 
                     source: str, target: str) -> Tuple[str, str]:
        """Store a message and create relationships."""
        # Create message document
        message_doc = {
            **message,
            "stored_at": datetime.now().isoformat()
        }
        
        msg_result = self.db.collection(self.MESSAGES).insert(message_doc)
        msg_id = msg_result["_id"]
        
        # Create edges
        self.db.collection(self.SENDS).insert({
            "_from": f"{self.MODULES}/{source}",
            "_to": msg_id
        })
        
        self.db.collection(self.RECEIVES).insert({
            "_from": msg_id,
            "_to": f"{self.MODULES}/{target}"
        })
        
        # Extract and link references
        for ref in message.get("references", []):
            self._create_reference(msg_id, ref)
            
        logger.info(f"Stored message from {source} to {target}: {msg_id}")
        return msg_id, msg_result["_key"]
        
    def _create_reference(self, message_id: str, reference: Dict[str, Any]):
        """Create a reference from message to resource."""
        # First ensure resource exists
        resource_key = reference.get("id", reference.get("url", "unknown"))
        resource_doc = {
            "_key": resource_key.replace("/", "_").replace(":", "_"),
            **reference,
            "created_at": datetime.now().isoformat()
        }
        
        try:
            resource_result = self.db.collection(self.RESOURCES).insert(resource_doc)
            resource_id = resource_result["_id"]
        except DocumentInsertError:
            # Resource already exists
            resource_id = f"{self.RESOURCES}/{resource_doc['_key']}"
            
        # Create reference edge
        self.db.collection(self.REFERENCES).insert({
            "_from": message_id,
            "_to": resource_id
        })
        
    def find_modules_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find modules with a specific capability."""
        query = """
        FOR module IN @@collection
            FILTER @capability IN module.capabilities
            FILTER module.active == true
            RETURN {
                name: module.name,
                capabilities: module.capabilities,
                description: module.description
            }
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "@collection": self.MODULES,
                "capability": capability
            }
        )
        
        return list(cursor)
        
    def find_compatible_modules(self, module_name: str, 
                              direction: str = "downstream") -> List[Dict[str, Any]]:
        """Find modules compatible with the given module."""
        if direction == "downstream":
            # Find modules that can process this module's output
            query = """
            FOR module IN modules
                FILTER module._key == @module_name
                FOR schema IN 1..1 OUTBOUND module provides
                    FOR compatible_module IN 1..1 INBOUND schema requires
                        FILTER compatible_module._key != @module_name
                        RETURN DISTINCT {
                            name: compatible_module.name,
                            capabilities: compatible_module.capabilities,
                            shared_schema: schema.name
                        }
            """
        else:  # upstream
            # Find modules whose output this module can process
            query = """
            FOR module IN modules
                FILTER module._key == @module_name
                FOR schema IN 1..1 OUTBOUND module requires
                    FOR compatible_module IN 1..1 INBOUND schema provides
                        FILTER compatible_module._key != @module_name
                        RETURN DISTINCT {
                            name: compatible_module.name,
                            capabilities: compatible_module.capabilities,
                            shared_schema: schema.name
                        }
            """
            
        cursor = self.db.aql.execute(
            query,
            bind_vars={"module_name": module_name}
        )
        
        return list(cursor)
        
    def get_module_conversation(self, module1: str, module2: str) -> List[Dict[str, Any]]:
        """Get all messages between two modules."""
        query = """
        LET sent_messages = (
            FOR module IN modules
                FILTER module._key == @module1
                FOR message IN 1..1 OUTBOUND module sends
                    FOR receiver IN 1..1 OUTBOUND message receives
                        FILTER receiver._key == @module2
                        RETURN message
        )
        
        LET received_messages = (
            FOR module IN modules
                FILTER module._key == @module2
                FOR message IN 1..1 OUTBOUND module sends
                    FOR receiver IN 1..1 OUTBOUND message receives
                        FILTER receiver._key == @module1
                        RETURN message
        )
        
        FOR msg IN UNION(sent_messages, received_messages)
            SORT msg.timestamp DESC
            RETURN msg
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={
                "module1": module1,
                "module2": module2
            }
        )
        
        return list(cursor)
        
    def get_knowledge_graph(self, topic: str, depth: int = 2) -> Dict[str, Any]:
        """Build a knowledge graph around a topic."""
        query = """
        // Find all resources related to the topic
        LET topic_resources = (
            FOR resource IN resources
                FILTER CONTAINS(LOWER(resource.title), LOWER(@topic)) OR
                       CONTAINS(LOWER(resource.description), LOWER(@topic))
                RETURN resource
        )
        
        // Find messages that reference these resources
        LET related_messages = (
            FOR resource IN topic_resources
                FOR message IN 1..1 INBOUND resource references
                    RETURN DISTINCT message
        )
        
        // Find modules involved
        LET involved_modules = (
            FOR message IN related_messages
                FOR module IN 1..1 INBOUND message sends
                    RETURN DISTINCT module
        )
        
        // Build the graph
        RETURN {
            topic: @topic,
            resources: topic_resources,
            messages: related_messages,
            modules: involved_modules,
            total_resources: LENGTH(topic_resources),
            total_messages: LENGTH(related_messages),
            total_modules: LENGTH(involved_modules)
        }
        """
        
        cursor = self.db.aql.execute(
            query,
            bind_vars={"topic": topic}
        )
        
        result = list(cursor)
        return result[0] if result else {
            "topic": topic,
            "resources": [],
            "messages": [],
            "modules": [],
            "total_resources": 0,
            "total_messages": 0,
            "total_modules": 0
        }
        
    def create_collaborative_task(self, task_data: Dict[str, Any]) -> str:
        """Create a collaborative task between modules."""
        task_doc = {
            **task_data,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        result = self.db.collection(self.TASKS).insert(task_doc)
        task_id = result["_id"]
        
        # Link participating modules
        for module in task_data.get("modules", []):
            self.db.collection(self.COLLABORATES_ON).insert({
                "_from": f"{self.MODULES}/{module}",
                "_to": task_id
            })
            
        logger.info(f"Created collaborative task: {task_data.get('name')}")
        return task_id