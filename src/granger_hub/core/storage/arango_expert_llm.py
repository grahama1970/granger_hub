"""
Enhanced ArangoDB Expert Module with LLM Integration.

Purpose: Extends the ArangoDB expert module with LLM capabilities for intelligent
analysis, natural language query processing, and advanced pattern recognition.

Dependencies:
- python-arango: For ArangoDB operations
- llm_call: For LLM capabilities
- Original expert module: For base functionality
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .arango_expert import ArangoExpertModule
from ..llm.llm_integration import LLMCapableMixin, LLMConfig, LLMModel, LLMRequest
from ..modules.module_registry import ModuleRegistry

logger = logging.getLogger(__name__)


class ArangoExpertLLMModule(LLMCapableMixin, ArangoExpertModule):
    """Enhanced ArangoDB expert with LLM capabilities."""
    
    def __init__(self,
                 registry: ModuleRegistry,
                 arango_config: Optional[Dict[str, Any]] = None,
                 llm_config: Optional[LLMConfig] = None):
        """Initialize enhanced expert module.
        
        Args:
            registry: Module registry
            arango_config: ArangoDB configuration
            llm_config: LLM configuration
        """
        # Initialize with both parent classes
        super().__init__(
            registry=registry,
            arango_config=arango_config,
            llm_config=llm_config
        )
        
        # Update capabilities
        self.capabilities.extend([
            "natural_language_query",
            "intelligent_analysis",
            "pattern_prediction",
            "anomaly_explanation",
            "optimization_suggestions"
        ])
        
        # Update system prompt
        self.system_prompt += (
            " I have advanced LLM capabilities for natural language understanding, "
            "intelligent analysis, and can provide detailed explanations and predictions."
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Extended input schema with LLM actions."""
        schema = super().get_input_schema()
        schema["properties"]["action"]["enum"].extend([
            "natural_query",
            "explain_pattern",
            "predict_behavior",
            "optimize_graph",
            "generate_insights"
        ])
        return schema
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process requests with LLM enhancement."""
        action = data.get("action")
        
        # Handle LLM-specific actions
        llm_actions = {
            "natural_query": self._handle_natural_query,
            "explain_pattern": self._handle_explain_pattern,
            "predict_behavior": self._handle_predict_behavior,
            "optimize_graph": self._handle_optimize_graph,
            "generate_insights": self._handle_generate_insights
        }
        
        if action in llm_actions:
            try:
                parameters = data.get("parameters", {})
                results = await llm_actions[action](parameters)
                return {
                    "status": "success",
                    "action": action,
                    "results": results,
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "expert": self.name,
                        "llm_enhanced": True
                    }
                }
            except Exception as e:
                logger.error(f"Error in LLM action {action}: {e}")
                return {
                    "status": "error",
                    "action": action,
                    "results": {"error": str(e)}
                }
        
        # Fall back to parent processing
        return await super().process(data)
    
    async def _handle_natural_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle natural language queries about the graph.
        
        Args:
            params: Query parameters
            
        Returns:
            Query results with explanation
        """
        query_text = params.get("query")
        if not query_text:
            return {"error": "Query text required"}
        
        # First, get current graph state
        graph_data = await self.graph_backend.get_module_graph_structure()
        stats = await self.graph_backend.get_communication_stats()
        
        # Use LLM to interpret the query and generate AQL
        interpretation_prompt = f"""Given this natural language query about a module communication graph:
"{query_text}"

And this graph structure:
- Modules: {len(graph_data['nodes']['modules'])}
- Communications: {len(graph_data['edges']['communications'])}
- Dependencies: {len(graph_data['edges']['dependencies'])}

Stats: {json.dumps(stats, indent=2)}

Please provide:
1. An interpretation of what the user is asking for
2. The appropriate AQL query to answer their question
3. Any additional context needed

Respond in JSON format with keys: interpretation, aql_query, context"""

        response = await self.llm_process(
            interpretation_prompt,
            model=LLMModel.CLAUDE_3_SONNET,
            temperature=0.3,
            system_prompt="You are an ArangoDB and AQL expert. Generate valid, safe AQL queries."
        )
        
        if not response.success:
            return {"error": "Failed to interpret query", "details": response.error}
        
        try:
            interpretation = json.loads(response.content)
            
            # Execute the generated AQL query
            aql_query = interpretation.get("aql_query")
            if aql_query:
                query_results = await self._handle_execute_query({
                    "query": aql_query
                })
                
                # Use LLM to explain results
                explanation_prompt = f"""The user asked: "{query_text}"

The query returned these results:
{json.dumps(query_results.get('results', []), indent=2)}

Please provide a natural language explanation of:
1. What the results mean
2. Key findings or patterns
3. Any recommendations based on the results

Keep the explanation clear and concise."""

                explain_response = await self.llm_process(
                    explanation_prompt,
                    model=LLMModel.CLAUDE_3_HAIKU,
                    temperature=0.5
                )
                
                return {
                    "query": query_text,
                    "interpretation": interpretation.get("interpretation"),
                    "aql_query": aql_query,
                    "raw_results": query_results.get("results"),
                    "explanation": explain_response.content if explain_response.success else "Results retrieved successfully",
                    "result_count": query_results.get("count", 0)
                }
            else:
                return {
                    "query": query_text,
                    "interpretation": interpretation.get("interpretation"),
                    "error": "Could not generate valid AQL query"
                }
                
        except json.JSONDecodeError:
            return {
                "query": query_text,
                "error": "Failed to parse LLM response",
                "raw_response": response.content
            }
    
    async def _handle_explain_pattern(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Explain discovered patterns using LLM.
        
        Args:
            params: Pattern parameters
            
        Returns:
            Pattern explanation
        """
        # First find the pattern using parent method
        pattern_results = await self._handle_find_pattern(params)
        
        if not pattern_results.get("found_patterns"):
            return {
                "explanation": "No patterns found matching the criteria",
                "pattern_results": pattern_results
            }
        
        # Get detailed graph context
        analysis = await self.graph_communicator.analyze_communication_patterns()
        
        # Use LLM to explain the patterns
        explanation_prompt = f"""Analyze and explain these communication patterns found in a module graph:

Pattern Type: {params.get('pattern', 'unknown')}
Found Patterns: {json.dumps(pattern_results['found_patterns'], indent=2)}

Graph Context:
- Total Modules: {analysis['graph_metrics']['node_count']}
- Total Connections: {analysis['graph_metrics']['edge_count']}
- Graph Density: {analysis['graph_metrics']['density']:.3f}
- Is Connected: {analysis['graph_metrics']['is_connected']}

Please provide:
1. A clear explanation of what these patterns mean
2. Why these patterns might have emerged
3. The implications for system performance and reliability
4. Specific recommendations for improvement

Format as a structured analysis."""

        response = await self.llm_process(
            explanation_prompt,
            model=LLMModel.CLAUDE_3_SONNET,
            temperature=0.4,
            system_prompt="You are a distributed systems expert analyzing module communication patterns."
        )
        
        return {
            "pattern_type": params.get("pattern"),
            "patterns_found": pattern_results["found_patterns"],
            "total_found": pattern_results["total_found"],
            "explanation": response.content if response.success else "Pattern analysis completed",
            "graph_context": {
                "density": analysis['graph_metrics']['density'],
                "connected": analysis['graph_metrics']['is_connected']
            }
        }
    
    async def _handle_predict_behavior(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Predict future behavior based on historical patterns.
        
        Args:
            params: Prediction parameters
            
        Returns:
            Behavior predictions
        """
        timeframe = params.get("timeframe", "next_24_hours")
        focus_modules = params.get("modules", [])
        
        # Gather historical data
        stats = await self.graph_backend.get_communication_stats()
        patterns = await self.graph_communicator.analyze_communication_patterns()
        
        # Get recent communications for trend analysis
        recent_comms = []
        if focus_modules:
            for module in focus_modules:
                comms = await self.graph_backend.get_module_communications(
                    module, direction="both", limit=100
                )
                recent_comms.extend(comms)
        
        # Use LLM to predict behavior
        prediction_prompt = f"""Based on the following historical data, predict module communication behavior for {timeframe}:

Current Statistics:
{json.dumps(stats, indent=2)}

Communication Patterns:
- Hub modules: {[{"module": m[0], "centrality": m[1]} for m in patterns['centrality']['hubs'][:5]]}
- Bottlenecks: {patterns['bottlenecks']}
- Communities: {len(patterns.get('communities', []))} detected

Recent Communication Trends:
- Total recent communications: {len(recent_comms)}
- Average duration: {sum(c.get('duration_ms', 0) for c in recent_comms) / len(recent_comms) if recent_comms else 0:.2f}ms
- Success rate: {sum(1 for c in recent_comms if c.get('success', True)) / len(recent_comms) * 100 if recent_comms else 0:.1f}%

Focus modules: {focus_modules if focus_modules else 'All modules'}

Please predict:
1. Expected communication volume changes
2. Potential bottlenecks or failures
3. Performance trends
4. Recommended proactive actions

Provide specific, actionable predictions."""

        response = await self.llm_process(
            prediction_prompt,
            model=LLMModel.CLAUDE_3_SONNET,
            temperature=0.5,
            system_prompt="You are an expert in predicting distributed system behavior based on historical patterns."
        )
        
        return {
            "timeframe": timeframe,
            "focus_modules": focus_modules,
            "predictions": response.content if response.success else "Unable to generate predictions",
            "based_on": {
                "historical_communications": len(recent_comms),
                "current_success_rate": stats.get("success_rate", 0),
                "identified_patterns": len(patterns.get("patterns", []))
            }
        }
    
    async def _handle_optimize_graph(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization suggestions for the module graph.
        
        Args:
            params: Optimization parameters
            
        Returns:
            Optimization recommendations
        """
        optimization_goal = params.get("goal", "performance")
        constraints = params.get("constraints", {})
        
        # Analyze current state
        analysis = await self.graph_communicator.analyze_communication_patterns()
        stats = await self.graph_backend.get_communication_stats()
        
        # Identify issues
        issues = []
        if analysis['bottlenecks']:
            issues.append(f"Bottleneck modules: {', '.join(analysis['bottlenecks'])}")
        if not analysis['graph_metrics']['is_connected']:
            issues.append("Graph is disconnected - some modules cannot communicate")
        if stats.get('success_rate', 1) < 0.95:
            issues.append(f"Low success rate: {stats['success_rate']*100:.1f}%")
        if analysis['graph_metrics']['density'] < 0.1:
            issues.append(f"Low graph density: {analysis['graph_metrics']['density']:.3f}")
        
        # Generate optimization recommendations
        optimization_prompt = f"""Analyze this module communication graph and provide optimization recommendations.

Goal: {optimization_goal}

Current State:
- Modules: {analysis['graph_metrics']['node_count']}
- Connections: {analysis['graph_metrics']['edge_count']}
- Density: {analysis['graph_metrics']['density']:.3f}
- Average Degree: {analysis['graph_metrics']['avg_degree']:.2f}
- Success Rate: {stats.get('success_rate', 1)*100:.1f}%

Identified Issues:
{json.dumps(issues, indent=2)}

Top Hub Modules:
{json.dumps([{"module": m[0], "centrality": m[1]} for m in analysis['centrality']['hubs'][:5]], indent=2)}

Constraints:
{json.dumps(constraints, indent=2)}

Please provide:
1. Specific graph structure optimizations (add/remove connections)
2. Module configuration changes
3. Load balancing strategies
4. Redundancy recommendations
5. Priority order for implementing changes

Focus on practical, implementable solutions."""

        response = await self.llm_process(
            optimization_prompt,
            model=LLMModel.CLAUDE_3_OPUS,  # Use most capable model for optimization
            temperature=0.6,
            system_prompt="You are a graph theory and distributed systems optimization expert."
        )
        
        # Also use basic LLM recommendation system
        recommendations = await self.llm_recommend(
            context={
                "goal": optimization_goal,
                "issues": issues,
                "metrics": analysis['graph_metrics']
            },
            constraints=constraints
        )
        
        return {
            "optimization_goal": optimization_goal,
            "current_issues": issues,
            "detailed_recommendations": response.content if response.success else "Unable to generate recommendations",
            "structured_recommendations": recommendations,
            "metrics_before": {
                "density": analysis['graph_metrics']['density'],
                "success_rate": stats.get('success_rate', 1),
                "bottlenecks": len(analysis['bottlenecks'])
            }
        }
    
    async def _handle_generate_insights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate deep insights using LLM analysis.
        
        Args:
            params: Insight parameters
            
        Returns:
            Generated insights
        """
        insight_types = params.get("types", ["all"])
        depth = params.get("depth", "comprehensive")
        
        # Gather comprehensive data
        analysis = await self.graph_communicator.analyze_communication_patterns()
        stats = await self.graph_backend.get_communication_stats()
        
        # Get sample communications for context
        recent_comms = []
        for module in analysis['centrality']['hubs'][:3]:
            comms = await self.graph_backend.get_module_communications(
                module[0], direction="both", limit=20
            )
            recent_comms.extend(comms)
        
        # Perform LLM analysis on different aspects
        analyses = {}
        
        if "all" in insight_types or "patterns" in insight_types:
            pattern_analysis = await self.llm_analyze(
                {
                    "graph_metrics": analysis['graph_metrics'],
                    "patterns": analysis.get('patterns', []),
                    "centrality": analysis['centrality']
                },
                "pattern_detection"
            )
            analyses["pattern_insights"] = pattern_analysis
        
        if "all" in insight_types or "performance" in insight_types:
            perf_analysis = await self.llm_analyze(
                {
                    "stats": stats,
                    "bottlenecks": analysis['bottlenecks'],
                    "communication_samples": recent_comms[:10]
                },
                "performance_analysis"
            )
            analyses["performance_insights"] = perf_analysis
        
        # Generate comprehensive insights
        insight_prompt = f"""Generate comprehensive insights about this module communication system.

System Overview:
{json.dumps(analysis['graph_metrics'], indent=2)}

Key Patterns:
{json.dumps(analysis.get('patterns', [])[:3], indent=2)}

Performance Metrics:
{json.dumps(stats, indent=2)}

Analysis Results:
{json.dumps(analyses, indent=2)}

Depth Level: {depth}

Please provide:
1. Executive summary of system health
2. Hidden patterns or correlations
3. Potential future risks
4. Strategic recommendations
5. Interesting or unexpected findings

Make insights actionable and specific to this system."""

        response = await self.llm_process(
            insight_prompt,
            model=LLMModel.CLAUDE_3_OPUS,
            temperature=0.7,
            system_prompt="You are a senior systems architect providing strategic insights."
        )
        
        return {
            "insight_types": insight_types,
            "depth": depth,
            "executive_insights": response.content if response.success else "Unable to generate insights",
            "detailed_analyses": analyses,
            "key_metrics": {
                "system_health": "healthy" if stats.get('success_rate', 0) > 0.95 else "needs attention",
                "complexity": "high" if analysis['graph_metrics']['density'] > 0.3 else "moderate",
                "bottleneck_risk": "high" if len(analysis['bottlenecks']) > 2 else "low"
            },
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Test enhanced expert module
    async def test_llm_expert():
        registry = ModuleRegistry()
        
        # Configure LLM
        llm_config = LLMConfig(
            default_model=LLMModel.CLAUDE_3_HAIKU,
            api_keys={"anthropic": "your-api-key"}  # Replace with actual key
        )
        
        expert = ArangoExpertLLMModule(
            registry=registry,
            llm_config=llm_config
        )
        
        await expert.start()
        
        # Test natural language query
        print("Testing natural language query...")
        result = await expert.process({
            "action": "natural_query",
            "parameters": {
                "query": "Which modules are the most critical for system communication?"
            }
        })
        print(json.dumps(result, indent=2))
        
        # Test pattern explanation
        print("\nTesting pattern explanation...")
        result = await expert.process({
            "action": "explain_pattern",
            "parameters": {
                "pattern": "hub_spoke",
                "min_connections": 3
            }
        })
        print(json.dumps(result, indent=2))
        
        # Test behavior prediction
        print("\nTesting behavior prediction...")
        result = await expert.process({
            "action": "predict_behavior",
            "parameters": {
                "timeframe": "next_6_hours",
                "modules": ["data_producer", "processor"]
            }
        })
        print(json.dumps(result, indent=2))
        
        # Test optimization
        print("\nTesting graph optimization...")
        result = await expert.process({
            "action": "optimize_graph",
            "parameters": {
                "goal": "reliability",
                "constraints": {
                    "max_connections_per_module": 10,
                    "preserve_existing": True
                }
            }
        })
        print(json.dumps(result, indent=2))
        
        await expert.stop()
    
    asyncio.run(test_llm_expert())