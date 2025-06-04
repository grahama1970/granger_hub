"""
ArangoDB Expert Module for Advanced Graph Operations.

Purpose: Provides an expert module that specializes in ArangoDB operations,
graph queries, and pattern analysis for the module communication system.

Third-party packages:
- python-arango: https://docs.python-arango.com/

Sample Input:
- Query request: {"action": "find_pattern", "pattern": "hub_spoke", "min_connections": 5}
- Analysis request: {"action": "analyze_module", "module": "data_processor", "metrics": ["centrality", "reliability"]}

Expected Output:
- Query results with graph patterns, paths, and analysis
- Module recommendations based on graph structure
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timedelta
import json

from .base_module import BaseModule
from .module_registry import ModuleRegistry
from .graph_backend import ArangoGraphBackend, ModuleNode
from .graph_communicator import GraphCommunicator

logger = logging.getLogger(__name__)


class ArangoExpertModule(BaseModule):
    """Expert module for ArangoDB graph operations and analysis."""
    
    def __init__(self, 
                 registry: ModuleRegistry,
                 arango_config: Optional[Dict[str, Any]] = None):
        """Initialize ArangoDB expert module.
        
        Args:
            registry: Module registry
            arango_config: ArangoDB configuration
        """
        super().__init__(
            name="ArangoExpert",
            system_prompt=(
                "You are an ArangoDB expert module specializing in graph database operations, "
                "pattern analysis, and intelligent routing for module communications. "
                "You can analyze module relationships, find optimal communication paths, "
                "detect patterns, and provide insights about the module ecosystem."
            ),
            capabilities=[
                "graph_query",
                "pattern_analysis",
                "path_finding",
                "module_recommendation",
                "performance_analysis",
                "anomaly_detection"
            ],
            registry=registry
        )
        
        # Initialize ArangoDB components
        self.graph_backend = ArangoGraphBackend(
            **arango_config if arango_config else {}
        )
        self.graph_communicator = GraphCommunicator(self.graph_backend, registry)
        self._initialized = False
    
    async def start(self):
        """Start the expert module and initialize connections."""
        await super().start()
        
        if not self._initialized:
            await self.graph_backend.initialize()
            await self.graph_communicator.initialize()
            self._initialized = True
            logger.info("ArangoDB expert module initialized")
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for the expert module."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "find_pattern",
                        "analyze_module",
                        "find_path",
                        "recommend_modules",
                        "analyze_performance",
                        "detect_anomalies",
                        "get_insights",
                        "execute_query"
                    ]
                },
                "parameters": {
                    "type": "object",
                    "description": "Action-specific parameters"
                }
            },
            "required": ["action"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output schema for the expert module."""
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "action": {"type": "string"},
                "results": {"type": "object"},
                "metadata": {"type": "object"}
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process expert requests.
        
        Args:
            data: Request data with action and parameters
            
        Returns:
            Processing results
        """
        action = data.get("action")
        parameters = data.get("parameters", {})
        
        # Route to appropriate handler
        handlers = {
            "find_pattern": self._handle_find_pattern,
            "analyze_module": self._handle_analyze_module,
            "find_path": self._handle_find_path,
            "recommend_modules": self._handle_recommend_modules,
            "analyze_performance": self._handle_analyze_performance,
            "detect_anomalies": self._handle_detect_anomalies,
            "get_insights": self._handle_get_insights,
            "execute_query": self._handle_execute_query
        }
        
        handler = handlers.get(action)
        if not handler:
            return {
                "status": "error",
                "action": action,
                "results": {"error": f"Unknown action: {action}"}
            }
        
        try:
            results = await handler(parameters)
            return {
                "status": "success",
                "action": action,
                "results": results,
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "expert": self.name
                }
            }
        except Exception as e:
            logger.error(f"Error processing {action}: {e}")
            return {
                "status": "error",
                "action": action,
                "results": {"error": str(e)}
            }
    
    async def _handle_find_pattern(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find specific patterns in the module graph.
        
        Args:
            params: Pattern parameters
            
        Returns:
            Found patterns
        """
        pattern_type = params.get("pattern", "any")
        
        # Analyze communication patterns
        analysis = await self.graph_communicator.analyze_communication_patterns()
        
        results = {
            "pattern_type": pattern_type,
            "found_patterns": []
        }
        
        if pattern_type == "hub_spoke":
            # Find hub modules
            min_connections = params.get("min_connections", 5)
            hubs = [
                {"module": node, "centrality": score}
                for node, score in analysis["centrality"]["hubs"]
                if score >= min_connections / analysis["graph_metrics"]["node_count"]
            ]
            results["found_patterns"] = hubs
        
        elif pattern_type == "pipeline":
            # Find pipeline patterns
            if "patterns" in analysis:
                for pattern in analysis["patterns"]:
                    if pattern["type"] == "pipeline":
                        results["found_patterns"] = pattern.get("examples", [])
        
        elif pattern_type == "bottleneck":
            # Find bottlenecks
            results["found_patterns"] = [
                {"module": node, "type": "bottleneck"}
                for node in analysis.get("bottlenecks", [])
            ]
        
        elif pattern_type == "community":
            # Find communities
            results["found_patterns"] = analysis.get("communities", [])
        
        else:
            # Return all patterns
            results["found_patterns"] = analysis.get("patterns", [])
        
        results["total_found"] = len(results["found_patterns"])
        return results
    
    async def _handle_analyze_module(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a specific module.
        
        Args:
            params: Module name and metrics to analyze
            
        Returns:
            Module analysis
        """
        module_name = params.get("module")
        if not module_name:
            return {"error": "Module name required"}
        
        metrics = params.get("metrics", ["all"])
        
        results = {
            "module": module_name,
            "analysis": {}
        }
        
        # Get module info from graph
        module_data = await self.graph_backend.get_module(module_name)
        if module_data:
            results["module_info"] = module_data
        
        # Get neighborhood
        if "all" in metrics or "neighborhood" in metrics:
            neighborhood = await self.graph_communicator.get_module_neighborhood(
                module_name,
                depth=params.get("depth", 2)
            )
            results["analysis"]["neighborhood"] = neighborhood
        
        # Get communications
        if "all" in metrics or "communications" in metrics:
            comms = await self.graph_backend.get_module_communications(
                module_name,
                direction="both",
                limit=params.get("limit", 50)
            )
            
            # Analyze communications
            total_comms = len(comms)
            successful = sum(1 for c in comms if c.get("success", True))
            
            results["analysis"]["communications"] = {
                "total": total_comms,
                "successful": successful,
                "success_rate": successful / total_comms if total_comms > 0 else 0,
                "recent": comms[:10]  # Most recent 10
            }
        
        # Get dependencies
        if "all" in metrics or "dependencies" in metrics:
            deps = await self.graph_backend.get_module_dependencies(module_name)
            results["analysis"]["dependencies"] = {
                "count": len(deps),
                "modules": [d["module"]["name"] for d in deps]
            }
        
        # Calculate reliability
        if "all" in metrics or "reliability" in metrics:
            # Get all paths where this module is involved
            comms = await self.graph_backend.get_module_communications(
                module_name,
                direction="both",
                limit=100
            )
            
            if comms:
                success_count = sum(1 for c in comms if c.get("success", True))
                avg_duration = sum(
                    c.get("duration_ms", 0) for c in comms if c.get("duration_ms")
                ) / len([c for c in comms if c.get("duration_ms")])
                
                results["analysis"]["reliability"] = {
                    "success_rate": success_count / len(comms),
                    "avg_duration_ms": avg_duration,
                    "total_communications": len(comms)
                }
        
        return results
    
    async def _handle_find_path(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find optimal path between modules.
        
        Args:
            params: Source and target modules
            
        Returns:
            Optimal path information
        """
        source = params.get("source")
        target = params.get("target")
        
        if not source or not target:
            return {"error": "Source and target modules required"}
        
        # Find optimal route
        route = await self.graph_communicator.find_optimal_route(
            source, target, constraints=params.get("constraints")
        )
        
        if route:
            return {
                "path_found": True,
                "route": route.to_dict(),
                "alternatives": []  # Could implement k-shortest paths
            }
        else:
            return {
                "path_found": False,
                "reason": "No path exists between modules"
            }
    
    async def _handle_recommend_modules(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend modules based on requirements.
        
        Args:
            params: Requirements and context
            
        Returns:
            Module recommendations
        """
        capability = params.get("capability")
        if not capability:
            return {"error": "Capability required"}
        
        context = {
            "current_module": params.get("current_module"),
            "preferences": params.get("preferences", {})
        }
        
        recommendations = await self.graph_communicator.recommend_modules(
            capability, context
        )
        
        return {
            "capability": capability,
            "recommendations": recommendations[:params.get("limit", 5)],
            "total_found": len(recommendations)
        }
    
    async def _handle_analyze_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system performance.
        
        Args:
            params: Time range and filters
            
        Returns:
            Performance analysis
        """
        # Get time range
        hours = params.get("hours", 24)
        start_time = datetime.now() - timedelta(hours=hours)
        
        # Get communication stats
        stats = await self.graph_backend.get_communication_stats(
            start_time=start_time
        )
        
        # Get graph metrics
        analysis = await self.graph_communicator.analyze_communication_patterns()
        
        return {
            "time_range": {
                "start": start_time.isoformat(),
                "end": datetime.now().isoformat(),
                "hours": hours
            },
            "communication_stats": stats,
            "graph_metrics": analysis["graph_metrics"],
            "top_modules": analysis["centrality"]["hubs"][:5],
            "bottlenecks": analysis["bottlenecks"]
        }
    
    async def _handle_detect_anomalies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in communication patterns.
        
        Args:
            params: Anomaly detection parameters
            
        Returns:
            Detected anomalies
        """
        threshold = params.get("threshold", 2.0)  # Standard deviations
        
        anomalies = []
        
        # Get recent communications
        # In a real implementation, this would be more sophisticated
        graph_data = await self.graph_backend.get_module_graph_structure()
        
        # Check for unusual communication patterns
        for comm in graph_data["edges"]["communications"][-100:]:  # Last 100
            # Check for unusually long duration
            if comm.get("duration_ms"):
                # Simple threshold check (would use statistical methods in production)
                if comm["duration_ms"] > 1000:  # 1 second
                    anomalies.append({
                        "type": "slow_communication",
                        "from": comm["_from"].split("/")[1],
                        "to": comm["_to"].split("/")[1],
                        "duration_ms": comm["duration_ms"],
                        "timestamp": comm["timestamp"]
                    })
            
            # Check for failed communications
            if not comm.get("success", True):
                anomalies.append({
                    "type": "failed_communication",
                    "from": comm["_from"].split("/")[1],
                    "to": comm["_to"].split("/")[1],
                    "timestamp": comm["timestamp"]
                })
        
        return {
            "anomalies": anomalies,
            "count": len(anomalies),
            "threshold": threshold
        }
    
    async def _handle_get_insights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get insights about the module ecosystem.
        
        Args:
            params: Insight parameters
            
        Returns:
            System insights
        """
        # Comprehensive analysis
        analysis = await self.graph_communicator.analyze_communication_patterns()
        stats = await self.graph_backend.get_communication_stats()
        
        insights = []
        
        # Graph connectivity insight
        if analysis["graph_metrics"]["is_connected"]:
            insights.append({
                "type": "connectivity",
                "message": "All modules are connected in the communication graph",
                "severity": "info"
            })
        else:
            insights.append({
                "type": "connectivity",
                "message": "Module graph is disconnected - some modules cannot communicate",
                "severity": "warning"
            })
        
        # Density insight
        density = analysis["graph_metrics"]["density"]
        if density < 0.1:
            insights.append({
                "type": "density",
                "message": f"Low graph density ({density:.2f}) - consider adding more module connections",
                "severity": "info"
            })
        elif density > 0.5:
            insights.append({
                "type": "density",
                "message": f"High graph density ({density:.2f}) - good module interconnectivity",
                "severity": "info"
            })
        
        # Performance insight
        if stats.get("success_rate", 0) < 0.9:
            insights.append({
                "type": "reliability",
                "message": f"Communication success rate is {stats['success_rate']:.1%} - investigate failures",
                "severity": "warning"
            })
        
        # Bottleneck insight
        if analysis["bottlenecks"]:
            insights.append({
                "type": "bottleneck",
                "message": f"Found {len(analysis['bottlenecks'])} bottleneck modules: {', '.join(analysis['bottlenecks'][:3])}",
                "severity": "warning",
                "modules": analysis["bottlenecks"]
            })
        
        return {
            "insights": insights,
            "summary": {
                "total_modules": analysis["graph_metrics"]["node_count"],
                "total_connections": analysis["graph_metrics"]["edge_count"],
                "success_rate": stats.get("success_rate", 0),
                "communities": len(analysis.get("communities", []))
            }
        }
    
    async def _handle_execute_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom AQL query.
        
        Args:
            params: Query parameters
            
        Returns:
            Query results
        """
        query = params.get("query")
        if not query:
            return {"error": "Query required"}
        
        # Safety check - only allow SELECT queries
        if not query.strip().upper().startswith(("FOR", "LET", "RETURN")):
            return {"error": "Only read queries allowed"}
        
        try:
            cursor = self.graph_backend.db.aql.execute(
                query,
                bind_vars=params.get("bind_vars", {})
            )
            
            results = list(cursor)
            
            return {
                "query": query,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return {
                "error": f"Query execution failed: {str(e)}",
                "query": query
            }


if __name__ == "__main__":
    # Test the ArangoDB expert module with real data
    async def test_expert_module():
        registry = ModuleRegistry()
        expert = ArangoExpertModule(registry)
        
        await expert.start()
        
        # Find patterns
        result = await expert.process({
            "action": "find_pattern",
            "parameters": {
                "pattern": "hub_spoke",
                "min_connections": 3
            }
        })
        print(f"Pattern search: {json.dumps(result, indent=2)}")
        
        # Analyze module
        result = await expert.process({
            "action": "analyze_module",
            "parameters": {
                "module": "data_producer",
                "metrics": ["all"]
            }
        })
        print(f"Module analysis: {json.dumps(result, indent=2)}")
        
        # Get insights
        result = await expert.process({
            "action": "get_insights",
            "parameters": {}
        })
        print(f"System insights: {json.dumps(result, indent=2)}")
        
        await expert.stop()
    
    asyncio.run(test_expert_module())