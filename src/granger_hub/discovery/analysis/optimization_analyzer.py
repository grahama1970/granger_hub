"""
Optimization Analyzer using RL Commons principles
Module: optimization_analyzer.py

Analyzes interaction patterns for optimization potential.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from pathlib import Path
import json

# Import RL Commons components (would be actual imports in production)
try:
    from rl_commons import RewardFunction, PolicyOptimizer, PerformanceMetrics
except ImportError:
    # Mock for development
    RewardFunction = None
    PolicyOptimizer = None
    PerformanceMetrics = None


@dataclass
class InteractionPattern:
    """Represents an interaction pattern to analyze"""
    name: str
    modules: List[str]
    flow_type: str  # sequential, parallel, event_driven, hybrid
    steps: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationScore:
    """Optimization analysis results"""
    pattern_name: str
    overall_score: float  # 0-1, higher is better
    performance_score: float
    reliability_score: float
    scalability_score: float
    bottlenecks: List[str] = field(default_factory=list)
    improvements: List[Dict[str, Any]] = field(default_factory=list)
    rl_rewards: Dict[str, float] = field(default_factory=dict)
    analysis_timestamp: datetime = field(default_factory=datetime.now)


class OptimizationAnalyzer:
    """Analyzes patterns using RL Commons for optimization potential"""
    
    def __init__(self, rl_commons_path: Optional[Path] = None):
        self.rl_commons_path = rl_commons_path or Path("/home/graham/workspace/experiments/rl_commons")
        
        # Define reward functions for different optimization goals
        self.reward_functions = {
            "latency": self._latency_reward,
            "throughput": self._throughput_reward,
            "reliability": self._reliability_reward,
            "resource_efficiency": self._resource_efficiency_reward,
            "scalability": self._scalability_reward
        }
        
        # Performance baselines from RL Commons
        self.performance_baselines = {
            "latency_ms": 100,  # Target latency
            "throughput_rps": 1000,  # Requests per second
            "error_rate": 0.001,  # 0.1% error rate
            "cpu_usage": 0.7,  # 70% CPU utilization
            "memory_usage": 0.8  # 80% memory utilization
        }
        
        # Optimization strategies learned from RL
        self.optimization_strategies = {
            "caching": {"impact": 0.4, "cost": 0.1},
            "parallelization": {"impact": 0.6, "cost": 0.3},
            "batching": {"impact": 0.3, "cost": 0.05},
            "circuit_breaking": {"impact": 0.2, "cost": 0.1},
            "load_balancing": {"impact": 0.5, "cost": 0.2},
            "async_processing": {"impact": 0.5, "cost": 0.15},
            "connection_pooling": {"impact": 0.3, "cost": 0.1},
            "compression": {"impact": 0.2, "cost": 0.05}
        }
    
    async def analyze_pattern(
        self, 
        pattern: InteractionPattern,
        metrics: Optional[Dict[str, Any]] = None
    ) -> OptimizationScore:
        """
        Analyze an interaction pattern for optimization potential
        
        Args:
            pattern: The interaction pattern to analyze
            metrics: Optional performance metrics from actual execution
            
        Returns:
            OptimizationScore with analysis results
        """
        # Simulate pattern execution if no metrics provided
        if not metrics:
            metrics = await self._simulate_pattern_execution(pattern)
        
        # Calculate individual scores
        performance_score = self._calculate_performance_score(pattern, metrics)
        reliability_score = self._calculate_reliability_score(pattern, metrics)
        scalability_score = self._calculate_scalability_score(pattern, metrics)
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(pattern, metrics)
        
        # Generate improvement suggestions
        improvements = self._generate_improvements(pattern, bottlenecks, metrics)
        
        # Calculate RL rewards
        rl_rewards = self._calculate_rl_rewards(pattern, metrics)
        
        # Overall score is weighted combination
        overall_score = (
            0.4 * performance_score +
            0.3 * reliability_score +
            0.3 * scalability_score
        )
        
        return OptimizationScore(
            pattern_name=pattern.name,
            overall_score=overall_score,
            performance_score=performance_score,
            reliability_score=reliability_score,
            scalability_score=scalability_score,
            bottlenecks=bottlenecks,
            improvements=improvements,
            rl_rewards=rl_rewards
        )
    
    async def compare_patterns(
        self,
        patterns: List[InteractionPattern]
    ) -> List[Tuple[InteractionPattern, OptimizationScore]]:
        """Compare multiple patterns and rank by optimization potential"""
        results = []
        
        # Analyze all patterns
        for pattern in patterns:
            score = await self.analyze_pattern(pattern)
            results.append((pattern, score))
        
        # Sort by overall score
        results.sort(key=lambda x: x[1].overall_score, reverse=True)
        
        return results
    
    async def _simulate_pattern_execution(
        self, 
        pattern: InteractionPattern
    ) -> Dict[str, Any]:
        """Simulate pattern execution to estimate metrics"""
        # Base metrics
        metrics = {
            "total_latency_ms": 0,
            "throughput_rps": 1000,
            "error_rate": 0.001,
            "cpu_usage": 0.5,
            "memory_usage": 0.6,
            "step_latencies": []
        }
        
        # Estimate based on pattern characteristics
        if pattern.flow_type == "sequential":
            # Sequential adds latencies
            for step in pattern.steps:
                step_latency = self._estimate_step_latency(step)
                metrics["total_latency_ms"] += step_latency
                metrics["step_latencies"].append(step_latency)
            metrics["throughput_rps"] = 1000 / (metrics["total_latency_ms"] / 100)
            
        elif pattern.flow_type == "parallel":
            # Parallel takes max latency
            step_latencies = [self._estimate_step_latency(step) for step in pattern.steps]
            metrics["total_latency_ms"] = max(step_latencies)
            metrics["step_latencies"] = step_latencies
            metrics["throughput_rps"] = 1000 / (metrics["total_latency_ms"] / 100) * 0.8
            metrics["cpu_usage"] = min(0.9, 0.5 + len(pattern.steps) * 0.1)
            
        elif pattern.flow_type == "event_driven":
            # Event-driven has low latency but potential queuing
            metrics["total_latency_ms"] = len(pattern.steps) * 20
            metrics["throughput_rps"] = 2000  # Higher throughput
            metrics["error_rate"] = 0.002  # Slightly higher error rate
            
        # Add some randomness
        for key in ["total_latency_ms", "throughput_rps", "cpu_usage"]:
            if key in metrics and isinstance(metrics[key], (int, float)):
                metrics[key] *= np.random.uniform(0.9, 1.1)
        
        return metrics
    
    def _estimate_step_latency(self, step: Dict[str, Any]) -> float:
        """Estimate latency for a single step"""
        base_latency = 50  # Base 50ms
        
        # Adjust based on operation type
        task = step.get("content", {}).get("task", "")
        
        if "llm" in task.lower() or "analyze" in task.lower():
            base_latency *= 3  # LLM calls are slower
        elif "database" in task.lower() or "store" in task.lower():
            base_latency *= 1.5  # DB operations
        elif "search" in task.lower():
            base_latency *= 2  # Search operations
        
        return base_latency
    
    def _calculate_performance_score(
        self, 
        pattern: InteractionPattern,
        metrics: Dict[str, Any]
    ) -> float:
        """Calculate performance score based on latency and throughput"""
        latency = metrics.get("total_latency_ms", 1000)
        throughput = metrics.get("throughput_rps", 100)
        
        # Normalize against baselines
        latency_score = max(0, 1 - (latency / self.performance_baselines["latency_ms"]) / 2)
        throughput_score = min(1, throughput / self.performance_baselines["throughput_rps"])
        
        # Check for optimization opportunities
        optimization_bonus = 0
        if pattern.flow_type == "sequential" and len(pattern.steps) > 3:
            optimization_bonus = 0.1  # Can be parallelized
        
        return min(1.0, (latency_score + throughput_score) / 2 + optimization_bonus)
    
    def _calculate_reliability_score(
        self,
        pattern: InteractionPattern,
        metrics: Dict[str, Any]
    ) -> float:
        """Calculate reliability score based on error handling"""
        error_rate = metrics.get("error_rate", 0.01)
        
        # Base score from error rate
        error_score = max(0, 1 - error_rate * 100)
        
        # Check for reliability patterns
        reliability_bonus = 0
        pattern_str = str(pattern.steps).lower()
        
        if "retry" in pattern_str:
            reliability_bonus += 0.1
        if "circuit" in pattern_str or "breaker" in pattern_str:
            reliability_bonus += 0.15
        if "fallback" in pattern_str:
            reliability_bonus += 0.1
        if "timeout" in pattern_str:
            reliability_bonus += 0.05
        
        return min(1.0, error_score + reliability_bonus)
    
    def _calculate_scalability_score(
        self,
        pattern: InteractionPattern,
        metrics: Dict[str, Any]
    ) -> float:
        """Calculate scalability score based on resource usage"""
        cpu_usage = metrics.get("cpu_usage", 0.8)
        memory_usage = metrics.get("memory_usage", 0.8)
        
        # Lower resource usage = better scalability
        cpu_score = max(0, 1 - cpu_usage)
        memory_score = max(0, 1 - memory_usage)
        
        # Architecture bonus
        architecture_bonus = 0
        if pattern.flow_type in ["parallel", "event_driven"]:
            architecture_bonus = 0.2
        
        # Check for scalability patterns
        if any("pool" in str(step).lower() for step in pattern.steps):
            architecture_bonus += 0.1
        if any("cache" in str(step).lower() for step in pattern.steps):
            architecture_bonus += 0.1
        
        return min(1.0, (cpu_score + memory_score) / 2 + architecture_bonus)
    
    def _identify_bottlenecks(
        self,
        pattern: InteractionPattern,
        metrics: Dict[str, Any]
    ) -> List[str]:
        """Identify performance bottlenecks in the pattern"""
        bottlenecks = []
        
        # Latency bottlenecks
        if pattern.flow_type == "sequential":
            step_latencies = metrics.get("step_latencies", [])
            if step_latencies:
                max_latency = max(step_latencies)
                avg_latency = sum(step_latencies) / len(step_latencies)
                if max_latency > avg_latency * 2:
                    bottlenecks.append(f"Step {step_latencies.index(max_latency)} has 2x average latency")
        
        # Throughput bottlenecks
        throughput = metrics.get("throughput_rps", 1000)
        if throughput < self.performance_baselines["throughput_rps"] * 0.5:
            bottlenecks.append("Low throughput - consider parallelization")
        
        # Resource bottlenecks
        if metrics.get("cpu_usage", 0) > 0.8:
            bottlenecks.append("High CPU usage - optimize compute-intensive operations")
        if metrics.get("memory_usage", 0) > 0.8:
            bottlenecks.append("High memory usage - consider pagination or streaming")
        
        # Pattern-specific bottlenecks
        if pattern.flow_type == "sequential" and len(pattern.steps) > 5:
            bottlenecks.append("Long sequential chain - identify parallelization opportunities")
        
        # Module-specific bottlenecks
        slow_modules = ["llm_call", "arxiv", "youtube_transcripts"]
        for i, step in enumerate(pattern.steps):
            if any(module in step.get("to_module", "") for module in slow_modules):
                if pattern.flow_type == "sequential":
                    bottlenecks.append(f"Step {i} uses slow module in sequential flow")
        
        return bottlenecks
    
    def _generate_improvements(
        self,
        pattern: InteractionPattern,
        bottlenecks: List[str],
        metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate specific improvement suggestions"""
        improvements = []
        
        # Based on bottlenecks
        if any("sequential" in b.lower() for b in bottlenecks):
            improvements.append({
                "type": "parallelization",
                "description": "Convert independent sequential steps to parallel execution",
                "impact": self.optimization_strategies["parallelization"]["impact"],
                "implementation": "Use ParallelWorkflowRunner with step groups",
                "estimated_improvement": "40-60% latency reduction"
            })
        
        if any("throughput" in b.lower() for b in bottlenecks):
            improvements.append({
                "type": "batching",
                "description": "Batch multiple requests together",
                "impact": self.optimization_strategies["batching"]["impact"],
                "implementation": "Implement request batching with configurable window",
                "estimated_improvement": "2-3x throughput increase"
            })
        
        # Based on pattern analysis
        steps_str = str(pattern.steps).lower()
        if "cache" not in steps_str:
            improvements.append({
                "type": "caching",
                "description": "Add caching layer for repeated operations",
                "impact": self.optimization_strategies["caching"]["impact"],
                "implementation": "Redis cache with TTL based on data volatility",
                "estimated_improvement": "30-50% latency reduction for cache hits"
            })
        
        if "circuit" not in steps_str and len(pattern.modules) > 3:
            improvements.append({
                "type": "circuit_breaking",
                "description": "Add circuit breakers for external service calls",
                "impact": self.optimization_strategies["circuit_breaking"]["impact"],
                "implementation": "Hystrix-style circuit breaker with fallback",
                "estimated_improvement": "Prevent cascade failures"
            })
        
        # Advanced optimizations
        if pattern.flow_type == "sequential" and metrics.get("total_latency_ms", 0) > 500:
            improvements.append({
                "type": "async_processing",
                "description": "Convert to async/event-driven architecture",
                "impact": self.optimization_strategies["async_processing"]["impact"],
                "implementation": "Use message queues for long-running operations",
                "estimated_improvement": "Improved responsiveness and scalability"
            })
        
        return improvements
    
    def _calculate_rl_rewards(
        self,
        pattern: InteractionPattern,
        metrics: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate RL-based rewards for the pattern"""
        rewards = {}
        
        # Apply each reward function
        for reward_name, reward_func in self.reward_functions.items():
            rewards[reward_name] = reward_func(pattern, metrics)
        
        # Calculate composite reward
        rewards["composite"] = sum(rewards.values()) / len(rewards)
        
        return rewards
    
    # Reward function implementations
    def _latency_reward(self, pattern: InteractionPattern, metrics: Dict[str, Any]) -> float:
        """Reward function for low latency"""
        latency = metrics.get("total_latency_ms", 1000)
        baseline = self.performance_baselines["latency_ms"]
        
        if latency <= baseline:
            return 1.0
        elif latency <= baseline * 2:
            return 0.5
        else:
            return max(0, 1 - (latency / baseline) / 10)
    
    def _throughput_reward(self, pattern: InteractionPattern, metrics: Dict[str, Any]) -> float:
        """Reward function for high throughput"""
        throughput = metrics.get("throughput_rps", 100)
        baseline = self.performance_baselines["throughput_rps"]
        
        return min(1.0, throughput / baseline)
    
    def _reliability_reward(self, pattern: InteractionPattern, metrics: Dict[str, Any]) -> float:
        """Reward function for reliability"""
        error_rate = metrics.get("error_rate", 0.01)
        baseline = self.performance_baselines["error_rate"]
        
        if error_rate <= baseline:
            return 1.0
        else:
            return max(0, 1 - (error_rate / baseline) / 5)
    
    def _resource_efficiency_reward(self, pattern: InteractionPattern, metrics: Dict[str, Any]) -> float:
        """Reward function for resource efficiency"""
        cpu = metrics.get("cpu_usage", 0.8)
        memory = metrics.get("memory_usage", 0.8)
        
        cpu_reward = max(0, 1 - cpu)
        memory_reward = max(0, 1 - memory)
        
        return (cpu_reward + memory_reward) / 2
    
    def _scalability_reward(self, pattern: InteractionPattern, metrics: Dict[str, Any]) -> float:
        """Reward function for scalability"""
        # Combination of architecture and resource efficiency
        architecture_score = 0.5  # Base
        
        if pattern.flow_type in ["parallel", "event_driven"]:
            architecture_score = 0.8
        
        resource_score = self._resource_efficiency_reward(pattern, metrics)
        
        return (architecture_score + resource_score) / 2
    
    def generate_optimization_report(
        self,
        scores: List[OptimizationScore]
    ) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        report = {
            "summary": {
                "patterns_analyzed": len(scores),
                "average_score": sum(s.overall_score for s in scores) / len(scores),
                "best_pattern": max(scores, key=lambda s: s.overall_score).pattern_name,
                "total_improvements": sum(len(s.improvements) for s in scores)
            },
            "patterns": []
        }
        
        for score in scores:
            pattern_report = {
                "name": score.pattern_name,
                "scores": {
                    "overall": score.overall_score,
                    "performance": score.performance_score,
                    "reliability": score.reliability_score,
                    "scalability": score.scalability_score
                },
                "bottlenecks": score.bottlenecks,
                "improvements": score.improvements,
                "rl_rewards": score.rl_rewards
            }
            report["patterns"].append(pattern_report)
        
        return report


if __name__ == "__main__":
    # Test the optimization analyzer
    async def test_analyzer():
        analyzer = OptimizationAnalyzer()
        
        # Create test patterns
        sequential_pattern = InteractionPattern(
            name="Sequential PDF Processing",
            modules=["marker", "sparta", "arxiv", "llm_call", "test_reporter"],
            flow_type="sequential",
            steps=[
                {"to_module": "marker", "content": {"task": "extract_pdf"}},
                {"to_module": "sparta", "content": {"task": "analyze_security"}},
                {"to_module": "arxiv", "content": {"task": "search_papers"}},
                {"to_module": "llm_call", "content": {"task": "analyze"}},
                {"to_module": "test_reporter", "content": {"task": "generate_report"}}
            ]
        )
        
        parallel_pattern = InteractionPattern(
            name="Parallel Research Analysis",
            modules=["arxiv", "youtube_transcripts", "perplexity", "llm_call"],
            flow_type="parallel",
            steps=[
                {"to_module": "arxiv", "content": {"task": "search"}},
                {"to_module": "youtube_transcripts", "content": {"task": "search"}},
                {"to_module": "perplexity", "content": {"task": "query"}}
            ]
        )
        
        # Analyze patterns
        scores = await analyzer.compare_patterns([sequential_pattern, parallel_pattern])
        
        # Print results
        for pattern, score in scores:
            print(f"\nPattern: {pattern.name}")
            print(f"Overall Score: {score.overall_score:.2f}")
            print(f"Bottlenecks: {', '.join(score.bottlenecks)}")
            print(f"Top Improvement: {score.improvements[0]['description'] if score.improvements else 'None'}")
    
    asyncio.run(test_analyzer())