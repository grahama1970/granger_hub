"""
Evolution Engine - Learns and improves from discovery results

Implements continuous learning to improve pattern recognition and scenario generation.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import numpy as np
from collections import defaultdict

from ..generation.scenario_generator import GeneratedScenario
from ..analysis.optimization_analyzer import InteractionPattern


@dataclass
class PatternPerformance:
    """Tracks performance of a pattern over time"""
    pattern_name: str
    success_count: int = 0
    failure_count: int = 0
    total_uses: int = 0
    average_score: float = 0.0
    last_used: Optional[datetime] = None
    module_combinations: Dict[str, int] = field(default_factory=dict)


@dataclass
class LearningState:
    """Current state of the learning system"""
    total_scenarios_analyzed: int = 0
    successful_patterns: Set[str] = field(default_factory=set)
    failed_patterns: Set[str] = field(default_factory=set)
    pattern_scores: Dict[str, float] = field(default_factory=dict)
    module_affinities: Dict[str, Dict[str, float]] = field(default_factory=dict)
    research_query_effectiveness: Dict[str, float] = field(default_factory=dict)
    last_update: datetime = field(default_factory=datetime.now)


class EvolutionEngine:
    """Learns from discovery results to improve future generations"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("data/learning")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Learning parameters
        self.learning_rate = 0.1
        self.decay_factor = 0.95  # Decay old patterns
        self.min_confidence_threshold = 0.3
        
        # Pattern performance tracking
        self.pattern_performance: Dict[str, PatternPerformance] = {}
        
        # Module relationship learning
        self.module_graph = defaultdict(lambda: defaultdict(float))
        
        # Scenario success tracking
        self.scenario_feedback: Dict[str, Dict[str, Any]] = {}
        
        # Current learning state
        self.state = self._load_state()
        
        # Evolution strategies
        self.mutation_rate = 0.1
        self.crossover_rate = 0.3
    
    async def record_pattern_success(
        self,
        pattern: InteractionPattern,
        score: float = 1.0
    ):
        """Record successful use of a pattern"""
        pattern_key = self._get_pattern_key(pattern)
        
        if pattern_key not in self.pattern_performance:
            self.pattern_performance[pattern_key] = PatternPerformance(
                pattern_name=pattern.name
            )
        
        perf = self.pattern_performance[pattern_key]
        perf.success_count += 1
        perf.total_uses += 1
        perf.average_score = (
            (perf.average_score * (perf.total_uses - 1) + score) / perf.total_uses
        )
        perf.last_used = datetime.now()
        
        # Track module combinations
        module_combo = "_".join(sorted(pattern.modules))
        perf.module_combinations[module_combo] = perf.module_combinations.get(module_combo, 0) + 1
        
        # Update module affinities
        self._update_module_affinities(pattern.modules, score)
        
        # Update state
        self.state.successful_patterns.add(pattern_key)
        self.state.pattern_scores[pattern_key] = perf.average_score
        
        # Save state periodically
        if perf.total_uses % 10 == 0:
            self._save_state()
    
    async def learn_from_scenario(
        self,
        scenario: GeneratedScenario,
        execution_results: Optional[Dict[str, Any]] = None
    ):
        """Learn from a generated scenario"""
        # Extract patterns from scenario
        patterns = scenario.source_patterns
        
        # Update pattern usage
        for pattern in patterns:
            if pattern in self.state.pattern_scores:
                # Decay old patterns
                self.state.pattern_scores[pattern] *= self.decay_factor
        
        # If we have execution results, learn from them
        if execution_results:
            success = execution_results.get("success", False)
            performance_score = execution_results.get("performance_score", 0.5)
            
            # Update scenario feedback
            self.scenario_feedback[scenario.name] = {
                "success": success,
                "performance": performance_score,
                "timestamp": datetime.now().isoformat()
            }
            
            # Learn from success/failure
            if success:
                # Reinforce successful patterns
                for pattern in patterns:
                    self.state.pattern_scores[pattern] = min(
                        1.0,
                        self.state.pattern_scores.get(pattern, 0.5) + self.learning_rate
                    )
            else:
                # Penalize failed patterns
                for pattern in patterns:
                    self.state.pattern_scores[pattern] = max(
                        0.0,
                        self.state.pattern_scores.get(pattern, 0.5) - self.learning_rate
                    )
        
        self.state.total_scenarios_analyzed += 1
    
    async def evolve_scenarios(
        self,
        scenarios: List[GeneratedScenario]
    ) -> List[GeneratedScenario]:
        """Apply evolutionary strategies to improve scenarios"""
        evolved = []
        
        for scenario in scenarios:
            # Apply mutations based on learning
            if np.random.random() < self.mutation_rate:
                evolved_scenario = await self._mutate_scenario(scenario)
                evolved.append(evolved_scenario)
            else:
                evolved.append(scenario)
        
        # Apply crossover to create hybrid scenarios
        if len(evolved) >= 2 and np.random.random() < self.crossover_rate:
            hybrid = await self._crossover_scenarios(evolved[0], evolved[1])
            evolved.append(hybrid)
        
        return evolved
    
    async def update_research_strategies(
        self,
        successful_queries: List[str]
    ):
        """Update effectiveness of research queries"""
        for query in successful_queries:
            current_score = self.state.research_query_effectiveness.get(query, 0.5)
            # Increase effectiveness score
            self.state.research_query_effectiveness[query] = min(
                1.0,
                current_score + self.learning_rate
            )
        
        # Decay unused queries
        for query, score in list(self.state.research_query_effectiveness.items()):
            if query not in successful_queries:
                new_score = score * self.decay_factor
                if new_score < self.min_confidence_threshold:
                    del self.state.research_query_effectiveness[query]
                else:
                    self.state.research_query_effectiveness[query] = new_score
    
    def get_recommended_patterns(self, count: int = 5) -> List[str]:
        """Get recommended patterns based on learning"""
        # Sort patterns by score
        sorted_patterns = sorted(
            self.state.pattern_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [pattern for pattern, score in sorted_patterns[:count]]
    
    def get_module_recommendations(
        self,
        base_module: str,
        count: int = 3
    ) -> List[str]:
        """Get recommended modules to pair with a base module"""
        if base_module not in self.module_graph:
            return []
        
        # Sort by affinity score
        affinities = self.module_graph[base_module]
        sorted_modules = sorted(
            affinities.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [module for module, score in sorted_modules[:count]]
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from learning process"""
        insights = {
            "total_scenarios_analyzed": self.state.total_scenarios_analyzed,
            "successful_patterns_count": len(self.state.successful_patterns),
            "failed_patterns_count": len(self.state.failed_patterns),
            "top_patterns": self.get_recommended_patterns(3),
            "learning_progress": self._calculate_learning_progress(),
            "module_insights": self._get_module_insights(),
            "pattern_evolution": self._get_pattern_evolution()
        }
        
        return insights
    
    async def _mutate_scenario(
        self,
        scenario: GeneratedScenario
    ) -> GeneratedScenario:
        """Apply mutations to a scenario based on learning"""
        mutated = GeneratedScenario(
            name=f"{scenario.name}_evolved",
            description=f"{scenario.description} (evolved)",
            category=scenario.category,
            modules=scenario.modules.copy(),
            workflow_steps=scenario.workflow_steps.copy(),
            test_code=scenario.test_code,
            optimization_notes=scenario.optimization_notes.copy(),
            source_patterns=scenario.source_patterns + ["evolution"]
        )
        
        # Module mutation - replace low-performing modules
        if len(mutated.modules) > 2:
            # Find module with lowest affinity
            min_affinity = float('inf')
            min_module = None
            
            for module in mutated.modules:
                avg_affinity = np.mean([
                    self.module_graph[module].get(other, 0)
                    for other in mutated.modules if other != module
                ])
                if avg_affinity < min_affinity:
                    min_affinity = avg_affinity
                    min_module = module
            
            # Replace with recommended module
            if min_module:
                recommendations = self.get_module_recommendations(
                    mutated.modules[0],
                    count=5
                )
                for rec in recommendations:
                    if rec not in mutated.modules:
                        idx = mutated.modules.index(min_module)
                        mutated.modules[idx] = rec
                        break
        
        # Add optimization based on successful patterns
        if self.state.successful_patterns:
            mutated.optimization_notes.append(
                f"Evolved using patterns: {', '.join(list(self.state.successful_patterns)[:2])}"
            )
        
        return mutated
    
    async def _crossover_scenarios(
        self,
        scenario1: GeneratedScenario,
        scenario2: GeneratedScenario
    ) -> GeneratedScenario:
        """Create hybrid scenario from two parents"""
        # Combine modules
        all_modules = list(set(scenario1.modules + scenario2.modules))
        
        # Select diverse subset
        selected_modules = []
        categories_used = set()
        
        for module in all_modules:
            if len(selected_modules) >= 5:
                break
            # Simple category extraction
            category = module.split("_")[0]
            if category not in categories_used:
                selected_modules.append(module)
                categories_used.add(category)
        
        # Combine workflow steps
        steps1 = scenario1.workflow_steps[:len(scenario1.workflow_steps)//2]
        steps2 = scenario2.workflow_steps[len(scenario2.workflow_steps)//2:]
        
        hybrid = GeneratedScenario(
            name=f"TestHybrid{scenario1.name[4:]}_{scenario2.name[4:]}",
            description=f"Hybrid of {scenario1.name} and {scenario2.name}",
            category="integration",
            modules=selected_modules,
            workflow_steps=steps1 + steps2,
            test_code="",  # Will be regenerated
            optimization_notes=[
                f"Crossover from {scenario1.name}",
                f"Crossover from {scenario2.name}"
            ],
            source_patterns=scenario1.source_patterns + scenario2.source_patterns
        )
        
        return hybrid
    
    def _update_module_affinities(self, modules: List[str], score: float):
        """Update module relationship scores"""
        # Update pairwise affinities
        for i, module1 in enumerate(modules):
            for module2 in modules[i+1:]:
                # Symmetric update
                self.module_graph[module1][module2] += score * self.learning_rate
                self.module_graph[module2][module1] += score * self.learning_rate
                
                # Normalize
                self.module_graph[module1][module2] = min(
                    1.0,
                    self.module_graph[module1][module2]
                )
                self.module_graph[module2][module1] = min(
                    1.0,
                    self.module_graph[module2][module1]
                )
    
    def _get_pattern_key(self, pattern: InteractionPattern) -> str:
        """Generate unique key for pattern"""
        return f"{pattern.flow_type}_{len(pattern.modules)}_{pattern.name[:20]}"
    
    def _calculate_learning_progress(self) -> float:
        """Calculate overall learning progress"""
        if not self.state.pattern_scores:
            return 0.0
        
        # Average pattern scores weighted by recency
        total_score = 0
        total_weight = 0
        
        for pattern, perf in self.pattern_performance.items():
            if perf.last_used:
                age_days = (datetime.now() - perf.last_used).days
                weight = np.exp(-age_days / 30)  # Decay over 30 days
                total_score += perf.average_score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.5
    
    def _get_module_insights(self) -> Dict[str, Any]:
        """Get insights about module relationships"""
        # Find strongest module pairs
        strong_pairs = []
        
        for module1, affinities in self.module_graph.items():
            for module2, score in affinities.items():
                if score > 0.7:
                    strong_pairs.append({
                        "modules": [module1, module2],
                        "affinity": score
                    })
        
        # Sort by affinity
        strong_pairs.sort(key=lambda x: x["affinity"], reverse=True)
        
        return {
            "strong_module_pairs": strong_pairs[:5],
            "module_usage_diversity": len(self.module_graph)
        }
    
    def _get_pattern_evolution(self) -> List[Dict[str, Any]]:
        """Track how patterns evolved over time"""
        evolution = []
        
        for pattern_key, perf in self.pattern_performance.items():
            if perf.total_uses > 5:  # Minimum uses
                evolution.append({
                    "pattern": pattern_key,
                    "uses": perf.total_uses,
                    "success_rate": perf.success_count / perf.total_uses,
                    "current_score": self.state.pattern_scores.get(pattern_key, 0),
                    "trend": "improving" if perf.average_score > 0.7 else "declining"
                })
        
        return sorted(evolution, key=lambda x: x["uses"], reverse=True)[:10]
    
    def _load_state(self) -> LearningState:
        """Load learning state from disk"""
        state_file = self.data_dir / "learning_state.json"
        
        if state_file.exists():
            with open(state_file, 'r') as f:
                data = json.load(f)
                
            state = LearningState(
                total_scenarios_analyzed=data.get("total_scenarios_analyzed", 0),
                successful_patterns=set(data.get("successful_patterns", [])),
                failed_patterns=set(data.get("failed_patterns", [])),
                pattern_scores=data.get("pattern_scores", {}),
                module_affinities=data.get("module_affinities", {}),
                research_query_effectiveness=data.get("research_query_effectiveness", {}),
                last_update=datetime.fromisoformat(data.get("last_update", datetime.now().isoformat()))
            )
            
            # Load pattern performance
            perf_file = self.data_dir / "pattern_performance.json"
            if perf_file.exists():
                with open(perf_file, 'r') as f:
                    perf_data = json.load(f)
                    
                for key, data in perf_data.items():
                    self.pattern_performance[key] = PatternPerformance(
                        pattern_name=data["pattern_name"],
                        success_count=data["success_count"],
                        failure_count=data["failure_count"],
                        total_uses=data["total_uses"],
                        average_score=data["average_score"],
                        last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
                        module_combinations=data.get("module_combinations", {})
                    )
            
            return state
        
        return LearningState()
    
    def _save_state(self):
        """Save learning state to disk"""
        # Save main state
        state_data = {
            "total_scenarios_analyzed": self.state.total_scenarios_analyzed,
            "successful_patterns": list(self.state.successful_patterns),
            "failed_patterns": list(self.state.failed_patterns),
            "pattern_scores": self.state.pattern_scores,
            "module_affinities": dict(self.module_graph),
            "research_query_effectiveness": self.state.research_query_effectiveness,
            "last_update": datetime.now().isoformat()
        }
        
        state_file = self.data_dir / "learning_state.json"
        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2)
        
        # Save pattern performance
        perf_data = {}
        for key, perf in self.pattern_performance.items():
            perf_data[key] = {
                "pattern_name": perf.pattern_name,
                "success_count": perf.success_count,
                "failure_count": perf.failure_count,
                "total_uses": perf.total_uses,
                "average_score": perf.average_score,
                "last_used": perf.last_used.isoformat() if perf.last_used else None,
                "module_combinations": perf.module_combinations
            }
        
        perf_file = self.data_dir / "pattern_performance.json"
        with open(perf_file, 'w') as f:
            json.dump(perf_data, f, indent=2)


if __name__ == "__main__":
    # Test evolution engine
    import asyncio
    
    async def test_evolution():
        engine = EvolutionEngine()
        
        # Create test pattern
        pattern = InteractionPattern(
            name="Test Pipeline Pattern",
            modules=["marker", "llm_call", "test_reporter"],
            flow_type="sequential",
            steps=[]
        )
        
        # Record some successes
        await engine.record_pattern_success(pattern, score=0.9)
        await engine.record_pattern_success(pattern, score=0.85)
        
        # Get insights
        insights = engine.get_learning_insights()
        print("Learning Insights:")
        print(json.dumps(insights, indent=2))
        
        # Get recommendations
        print(f"\nRecommended patterns: {engine.get_recommended_patterns(3)}")
        print(f"Modules to pair with 'marker': {engine.get_module_recommendations('marker')}")
    
    asyncio.run(test_evolution())