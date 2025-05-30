"""
Graph-based Communication Layer for Module Interactions.

Purpose: Provides intelligent routing and communication patterns based on
the module graph structure stored in ArangoDB.

Third-party packages:
- python-arango: https://docs.python-arango.com/
- networkx: https://networkx.org/documentation/stable/

Sample Input:
- Route request: {"source": "ModuleA", "target": "ModuleC", "action": "process"}
- Pattern query: {"pattern": "pipeline", "start": "data_producer"}

Expected Output:
- Optimal communication paths
- Module recommendations based on graph analysis
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
import json
import networkx as nx

from .graph_backend import ArangoGraphBackend, CommunicationEdge
from .base_module import BaseModule
from .module_registry import ModuleRegistry

logger = logging.getLogger(__name__)


@dataclass
class CommunicationRoute:
    """Represents a communication route through the module graph."""
    source: str
    target: str
    path: List[str]
    total_distance: int
    estimated_time_ms: float
    reliability_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "path": self.path,
            "hops": len(self.path) - 1,
            "total_distance": self.total_distance,
            "estimated_time_ms": self.estimated_time_ms,
            "reliability_score": self.reliability_score
        }


class GraphCommunicator:
    """Intelligent graph-based communication layer."""
    
    def __init__(self,
                 graph_backend: ArangoGraphBackend,
                 registry: ModuleRegistry):
        """Initialize graph communicator.
        
        Args:
            graph_backend: ArangoDB graph backend
            registry: Module registry
        """
        self.graph_backend = graph_backend
        self.registry = registry
        self._nx_graph: Optional[nx.DiGraph] = None
        self._communication_cache: Dict[Tuple[str, str], CommunicationRoute] = {}
    
    async def initialize(self):
        """Initialize the graph communicator."""
        await self.graph_backend.initialize()
        await self._build_networkx_graph()
    
    async def _build_networkx_graph(self):
        """Build NetworkX graph from ArangoDB data for analysis."""
        self._nx_graph = nx.DiGraph()
        
        # Get graph structure from ArangoDB
        graph_data = await self.graph_backend.get_module_graph_structure()
        
        # Add nodes
        for module in graph_data["nodes"]:
            self._nx_graph.add_node(
                module["name"],
                capabilities=module.get("capabilities", []),
                metadata=module.get("metadata", {})
            )
        
        # Add communication edges with weights
        for comm in graph_data["edges"]["communications"]:
            source = comm["_from"].split("/")[1]
            target = comm["_to"].split("/")[1]
            
            # Calculate edge weight based on success rate and duration
            weight = 1.0  # Base weight
            if not comm.get("success", True):
                weight += 10.0  # Penalty for failed communications
            if comm.get("duration_ms"):
                weight += comm["duration_ms"] / 1000.0  # Add normalized duration
            
            # Update or add edge
            if self._nx_graph.has_edge(source, target):
                # Average the weights
                current_weight = self._nx_graph[source][target]["weight"]
                self._nx_graph[source][target]["weight"] = (current_weight + weight) / 2
            else:
                self._nx_graph.add_edge(source, target, weight=weight)
        
        # Add dependency edges
        for dep in graph_data["edges"]["dependencies"]:
            source = dep["_from"].split("/")[1]
            target = dep["_to"].split("/")[1]
            
            if not self._nx_graph.has_edge(source, target):
                self._nx_graph.add_edge(source, target, weight=0.5, type="dependency")
        
        logger.info(f"Built graph with {self._nx_graph.number_of_nodes()} nodes and {self._nx_graph.number_of_edges()} edges")
    
    async def find_optimal_route(self, 
                               source: str, 
                               target: str,
                               constraints: Optional[Dict[str, Any]] = None) -> Optional[CommunicationRoute]:
        """Find optimal communication route between modules.
        
        Args:
            source: Source module name
            target: Target module name
            constraints: Optional routing constraints
            
        Returns:
            Optimal route if found
        """
        # Check cache
        cache_key = (source, target)
        if cache_key in self._communication_cache:
            return self._communication_cache[cache_key]
        
        # Ensure graph is built
        if not self._nx_graph:
            await self._build_networkx_graph()
        
        try:
            # Find shortest path
            path = nx.shortest_path(
                self._nx_graph,
                source=source,
                target=target,
                weight="weight"
            )
            
            # Calculate metrics
            total_weight = nx.shortest_path_length(
                self._nx_graph,
                source=source,
                target=target,
                weight="weight"
            )
            
            # Estimate time based on historical data
            estimated_time = await self._estimate_route_time(path)
            
            # Calculate reliability score
            reliability = await self._calculate_route_reliability(path)
            
            route = CommunicationRoute(
                source=source,
                target=target,
                path=path,
                total_distance=len(path) - 1,
                estimated_time_ms=estimated_time,
                reliability_score=reliability
            )
            
            # Cache the route
            self._communication_cache[cache_key] = route
            
            return route
            
        except nx.NetworkXNoPath:
            logger.warning(f"No path found from {source} to {target}")
            return None
    
    async def _estimate_route_time(self, path: List[str]) -> float:
        """Estimate communication time for a route.
        
        Args:
            path: Module path
            
        Returns:
            Estimated time in milliseconds
        """
        total_time = 0.0
        
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            # Get historical communication data
            comms = await self.graph_backend.get_module_communications(
                source,
                direction="out",
                limit=10
            )
            
            # Filter to target module
            target_comms = [
                c for c in comms 
                if c["_to"] == f"modules/{target}" and c.get("duration_ms")
            ]
            
            if target_comms:
                # Average duration
                avg_duration = sum(c["duration_ms"] for c in target_comms) / len(target_comms)
                total_time += avg_duration
            else:
                # Default estimate
                total_time += 100.0  # 100ms default
        
        return total_time
    
    async def _calculate_route_reliability(self, path: List[str]) -> float:
        """Calculate reliability score for a route.
        
        Args:
            path: Module path
            
        Returns:
            Reliability score (0-1)
        """
        if len(path) < 2:
            return 1.0
        
        reliabilities = []
        
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            
            # Get historical success rate
            comms = await self.graph_backend.get_module_communications(
                source,
                direction="out",
                limit=20
            )
            
            # Filter to target module
            target_comms = [
                c for c in comms 
                if c["_to"] == f"modules/{target}"
            ]
            
            if target_comms:
                success_rate = sum(1 for c in target_comms if c.get("success", True)) / len(target_comms)
                reliabilities.append(success_rate)
            else:
                # No historical data, assume moderate reliability
                reliabilities.append(0.8)
        
        # Overall reliability is product of individual reliabilities
        overall_reliability = 1.0
        for r in reliabilities:
            overall_reliability *= r
        
        return overall_reliability
    
    async def recommend_modules(self,
                              capability: str,
                              context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Recommend modules based on capability and graph analysis.
        
        Args:
            capability: Required capability
            context: Optional context (current module, preferences, etc.)
            
        Returns:
            List of recommended modules with scores
        """
        # Find modules with capability
        modules = self.registry.find_modules_by_capability(capability)
        
        if not modules:
            return []
        
        recommendations = []
        current_module = context.get("current_module") if context else None
        
        for module in modules:
            score = 1.0
            reasons = []
            
            # Check if module is in graph
            if self._nx_graph and module.name in self._nx_graph:
                # Boost score based on centrality
                centrality = nx.degree_centrality(self._nx_graph).get(module.name, 0)
                score += centrality
                if centrality > 0.5:
                    reasons.append("highly connected")
                
                # Consider distance from current module
                if current_module and current_module in self._nx_graph:
                    try:
                        distance = nx.shortest_path_length(
                            self._nx_graph,
                            current_module,
                            module.name
                        )
                        if distance == 1:
                            score += 0.5
                            reasons.append("direct connection")
                        elif distance <= 3:
                            score += 0.2
                            reasons.append("nearby")
                    except nx.NetworkXNoPath:
                        pass
            
            # Get success rate
            stats = await self.graph_backend.get_communication_stats()
            # This would need module-specific stats in real implementation
            
            recommendations.append({
                "module": module.name,
                "score": score,
                "capabilities": module.capabilities,
                "reasons": reasons,
                "metadata": module.metadata
            })
        
        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations
    
    async def analyze_communication_patterns(self) -> Dict[str, Any]:
        """Analyze communication patterns in the graph.
        
        Returns:
            Analysis results
        """
        if not self._nx_graph:
            await self._build_networkx_graph()
        
        analysis = {
            "graph_metrics": {
                "node_count": self._nx_graph.number_of_nodes(),
                "edge_count": self._nx_graph.number_of_edges(),
                "density": nx.density(self._nx_graph),
                "is_connected": nx.is_weakly_connected(self._nx_graph)
            },
            "centrality": {},
            "communities": [],
            "bottlenecks": [],
            "patterns": []
        }
        
        # Centrality analysis
        degree_centrality = nx.degree_centrality(self._nx_graph)
        betweenness_centrality = nx.betweenness_centrality(self._nx_graph)
        
        # Find most central modules
        analysis["centrality"]["hubs"] = sorted(
            degree_centrality.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Find bottlenecks
        analysis["bottlenecks"] = [
            node for node, centrality in betweenness_centrality.items()
            if centrality > 0.3
        ]
        
        # Detect communities (for undirected version)
        undirected = self._nx_graph.to_undirected()
        communities = list(nx.community.greedy_modularity_communities(undirected))
        analysis["communities"] = [
            list(community) for community in communities
        ]
        
        # Detect common patterns
        # Pipeline pattern (linear chains)
        chains = []
        for node in self._nx_graph.nodes():
            if self._nx_graph.in_degree(node) == 1 and self._nx_graph.out_degree(node) == 1:
                # Part of a chain
                pred = list(self._nx_graph.predecessors(node))[0]
                succ = list(self._nx_graph.successors(node))[0]
                chains.append((pred, node, succ))
        
        if chains:
            analysis["patterns"].append({
                "type": "pipeline",
                "instances": len(chains),
                "examples": chains[:3]
            })
        
        # Hub-spoke pattern
        hubs = [
            node for node in self._nx_graph.nodes()
            if self._nx_graph.degree(node) > 5
        ]
        if hubs:
            analysis["patterns"].append({
                "type": "hub_spoke",
                "hubs": hubs
            })
        
        return analysis
    
    async def record_communication(self,
                                 source: str,
                                 target: str,
                                 action: str,
                                 success: bool,
                                 duration_ms: Optional[float] = None,
                                 data_size: Optional[int] = None) -> bool:
        """Record a communication in the graph.
        
        Args:
            source: Source module
            target: Target module
            action: Action performed
            success: Whether communication succeeded
            duration_ms: Duration in milliseconds
            data_size: Size of data transferred
            
        Returns:
            True if recorded successfully
        """
        edge = CommunicationEdge(
            _from=f"modules/{source}",
            _to=f"modules/{target}",
            action=action,
            timestamp=datetime.now().isoformat(),
            success=success,
            duration_ms=duration_ms,
            data_size=data_size
        )
        
        result = await self.graph_backend.add_communication(edge)
        
        # Invalidate cache for this route
        self._communication_cache.pop((source, target), None)
        
        # Rebuild graph periodically (in production, this would be more sophisticated)
        if len(self._communication_cache) > 100:
            self._communication_cache.clear()
            await self._build_networkx_graph()
        
        return result
    
    async def get_module_neighborhood(self, 
                                    module: str, 
                                    depth: int = 2) -> Dict[str, Any]:
        """Get the neighborhood of a module in the graph.
        
        Args:
            module: Module name
            depth: How many hops to include
            
        Returns:
            Neighborhood information
        """
        if not self._nx_graph or module not in self._nx_graph:
            return {"error": "Module not found in graph"}
        
        # Get subgraph
        nodes = set([module])
        for _ in range(depth):
            new_nodes = set()
            for node in nodes:
                new_nodes.update(self._nx_graph.predecessors(node))
                new_nodes.update(self._nx_graph.successors(node))
            nodes.update(new_nodes)
        
        subgraph = self._nx_graph.subgraph(nodes)
        
        return {
            "center": module,
            "depth": depth,
            "nodes": list(subgraph.nodes()),
            "edges": [
                {"from": u, "to": v, "weight": d.get("weight", 1.0)}
                for u, v, d in subgraph.edges(data=True)
            ],
            "stats": {
                "node_count": subgraph.number_of_nodes(),
                "edge_count": subgraph.number_of_edges(),
                "in_degree": self._nx_graph.in_degree(module),
                "out_degree": self._nx_graph.out_degree(module)
            }
        }


if __name__ == "__main__":
    # Test the graph communicator with real data
    async def test_graph_communicator():
        # Initialize components
        backend = ArangoGraphBackend()
        registry = ModuleRegistry()
        
        communicator = GraphCommunicator(backend, registry)
        await communicator.initialize()
        
        # Find optimal route
        route = await communicator.find_optimal_route("data_producer", "data_processor")
        if route:
            print(f"Optimal route: {route.to_dict()}")
        
        # Analyze patterns
        analysis = await communicator.analyze_communication_patterns()
        print(f"Graph analysis: {json.dumps(analysis, indent=2)}")
        
        # Get neighborhood
        neighborhood = await communicator.get_module_neighborhood("data_producer", depth=2)
        print(f"Neighborhood: {json.dumps(neighborhood, indent=2)}")
        
        await backend.close()
    
    asyncio.run(test_graph_communicator())