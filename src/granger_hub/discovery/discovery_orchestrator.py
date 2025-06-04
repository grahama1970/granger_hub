"""
Discovery Orchestrator - Coordinates the entire discovery process

Manages research, analysis, generation, and learning cycles.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import schedule
import time
from dataclasses import dataclass, field

from .research.research_agent import ResearchAgent, ResearchFinding
from .analysis.optimization_analyzer import OptimizationAnalyzer, InteractionPattern
from .analysis.pattern_recognizer import PatternRecognizer
from .generation.scenario_generator import ScenarioGenerator, GeneratedScenario
from .learning.evolution_engine import EvolutionEngine

from loguru import logger


@dataclass
class DiscoveryRun:
    """Records a single discovery run"""
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    findings_count: int = 0
    patterns_discovered: int = 0
    scenarios_generated: int = 0
    scenarios_saved: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


class DiscoveryOrchestrator:
    """Orchestrates the discovery, analysis, and generation process"""
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        auto_save: bool = True,
        enable_learning: bool = True
    ):
        self.data_dir = data_dir or Path("data/discovery")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.auto_save = auto_save
        self.enable_learning = enable_learning
        
        # Initialize components
        self.research_agent = ResearchAgent(cache_dir=self.data_dir / "research_cache")
        self.optimization_analyzer = OptimizationAnalyzer()
        self.pattern_recognizer = PatternRecognizer()
        self.scenario_generator = ScenarioGenerator(output_dir=Path("tests/integration_scenarios/generated"))
        
        if self.enable_learning:
            self.evolution_engine = EvolutionEngine(data_dir=self.data_dir / "learning")
        else:
            self.evolution_engine = None
        
        # Discovery state
        self.current_run: Optional[DiscoveryRun] = None
        self.run_history: List[DiscoveryRun] = []
        self.is_running = False
        
        # Configuration
        self.config = {
            "research_categories": ["optimization", "reliability", "security", "ml_patterns"],
            "max_scenarios_per_run": 10,
            "min_relevance_score": 0.7,
            "enable_hybrid_scenarios": True,
            "parallel_analysis": True
        }
        
        # Load history
        self._load_run_history()
    
    async def run_discovery_cycle(
        self,
        categories: Optional[List[str]] = None,
        force_refresh: bool = False
    ) -> DiscoveryRun:
        """
        Run a complete discovery cycle
        
        Args:
            categories: Specific categories to research (None = configured defaults)
            force_refresh: Force fresh research instead of using cache
            
        Returns:
            DiscoveryRun with results
        """
        if self.is_running:
            logger.warning("Discovery cycle already running")
            return None
        
        self.is_running = True
        run_id = f"discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_run = DiscoveryRun(run_id=run_id, start_time=datetime.now())
        
        logger.info(f"Starting discovery cycle {run_id}")
        
        try:
            # Phase 1: Research
            logger.info("Phase 1: Conducting research...")
            findings = await self._conduct_research(categories, force_refresh)
            self.current_run.findings_count = len(findings)
            logger.info(f"Found {len(findings)} research items")
            
            # Phase 2: Pattern Recognition
            logger.info("Phase 2: Recognizing patterns...")
            patterns = await self._recognize_patterns(findings)
            self.current_run.patterns_discovered = len(patterns)
            logger.info(f"Discovered {len(patterns)} patterns")
            
            # Phase 3: Optimization Analysis
            logger.info("Phase 3: Analyzing optimizations...")
            optimization_scores = await self._analyze_optimizations(patterns)
            logger.info(f"Analyzed {len(optimization_scores)} patterns for optimization")
            
            # Phase 4: Scenario Generation
            logger.info("Phase 4: Generating scenarios...")
            scenarios = await self._generate_scenarios(findings, patterns, optimization_scores)
            self.current_run.scenarios_generated = len(scenarios)
            logger.info(f"Generated {len(scenarios)} new scenarios")
            
            # Phase 5: Save and Learn
            if self.auto_save:
                logger.info("Phase 5: Saving scenarios...")
                saved_paths = await self._save_scenarios(scenarios)
                self.current_run.scenarios_saved = saved_paths
            
            if self.enable_learning and self.evolution_engine:
                logger.info("Phase 6: Learning from results...")
                await self._learn_from_results(findings, patterns, scenarios)
            
            # Calculate metrics
            self.current_run.metrics = self._calculate_metrics(findings, patterns, scenarios)
            
        except Exception as e:
            logger.error(f"Error in discovery cycle: {str(e)}")
            self.current_run.errors.append(str(e))
            raise
        finally:
            self.current_run.end_time = datetime.now()
            self.run_history.append(self.current_run)
            self._save_run_history()
            self.is_running = False
            
            # Log summary
            duration = (self.current_run.end_time - self.current_run.start_time).total_seconds()
            logger.info(f"Discovery cycle {run_id} completed in {duration:.1f}s")
            logger.info(f"Results: {self.current_run.findings_count} findings, "
                       f"{self.current_run.patterns_discovered} patterns, "
                       f"{self.current_run.scenarios_generated} scenarios")
        
        return self.current_run
    
    async def _conduct_research(
        self,
        categories: Optional[List[str]],
        force_refresh: bool
    ) -> List[ResearchFinding]:
        """Conduct research phase"""
        categories = categories or self.config["research_categories"]
        
        findings = await self.research_agent.conduct_research(
            categories=categories,
            force_refresh=force_refresh
        )
        
        # Filter by relevance
        min_score = self.config["min_relevance_score"]
        relevant_findings = [f for f in findings if f.relevance_score >= min_score]
        
        logger.info(f"Filtered {len(relevant_findings)} relevant findings from {len(findings)} total")
        
        return relevant_findings
    
    async def _recognize_patterns(self, findings: List[ResearchFinding]) -> List[InteractionPattern]:
        """Recognize patterns from findings"""
        if not hasattr(self, 'pattern_recognizer') or not self.pattern_recognizer:
            # Simple pattern extraction if recognizer not available
            patterns = []
            
            # Group findings by pattern type
            pattern_groups = {}
            for finding in findings:
                for pattern in finding.patterns_found:
                    if pattern not in pattern_groups:
                        pattern_groups[pattern] = []
                    pattern_groups[pattern].append(finding)
            
            # Create interaction patterns
            for pattern_type, pattern_findings in pattern_groups.items():
                if len(pattern_findings) >= 2:  # Need at least 2 findings
                    # Determine modules from findings
                    modules = self._extract_modules_from_findings(pattern_findings)
                    
                    pattern = InteractionPattern(
                        name=f"{pattern_type.replace('_', ' ').title()} Pattern",
                        modules=modules[:5],  # Limit to 5 modules
                        flow_type=self._determine_flow_type(pattern_type),
                        steps=self._create_pattern_steps(modules, pattern_type)
                    )
                    patterns.append(pattern)
            
            return patterns
        
        # Use actual pattern recognizer if available
        return await self.pattern_recognizer.recognize_patterns(findings)
    
    async def _analyze_optimizations(
        self,
        patterns: List[InteractionPattern]
    ) -> List[Any]:
        """Analyze patterns for optimization potential"""
        if self.config["parallel_analysis"]:
            # Analyze patterns in parallel
            tasks = [
                self.optimization_analyzer.analyze_pattern(pattern)
                for pattern in patterns
            ]
            scores = await asyncio.gather(*tasks)
        else:
            # Sequential analysis
            scores = []
            for pattern in patterns:
                score = await self.optimization_analyzer.analyze_pattern(pattern)
                scores.append(score)
        
        # Sort by optimization potential
        scores.sort(key=lambda s: s.overall_score, reverse=True)
        
        return scores
    
    async def _generate_scenarios(
        self,
        findings: List[ResearchFinding],
        patterns: List[InteractionPattern],
        optimization_scores: List[Any]
    ) -> List[GeneratedScenario]:
        """Generate new test scenarios"""
        scenarios = []
        
        # Generate from research findings
        research_scenarios = await self.scenario_generator.generate_from_research(
            findings=findings,
            optimization_scores=optimization_scores,
            max_scenarios=self.config["max_scenarios_per_run"] // 2
        )
        scenarios.extend(research_scenarios)
        
        # Generate from specific patterns with optimizations
        pattern_scenarios = []
        for i, (pattern, score) in enumerate(zip(patterns[:5], optimization_scores[:5])):
            scenario = await self.scenario_generator.generate_from_pattern(pattern, score)
            pattern_scenarios.append(scenario)
        scenarios.extend(pattern_scenarios)
        
        # Apply learning if available
        if self.evolution_engine:
            scenarios = await self.evolution_engine.evolve_scenarios(scenarios)
        
        return scenarios[:self.config["max_scenarios_per_run"]]
    
    async def _save_scenarios(self, scenarios: List[GeneratedScenario]) -> List[str]:
        """Save generated scenarios"""
        saved_paths = []
        
        for scenario in scenarios:
            try:
                path = self.scenario_generator.save_scenario(scenario)
                saved_paths.append(str(path))
                logger.info(f"Saved scenario: {scenario.name} to {path}")
            except Exception as e:
                logger.error(f"Failed to save scenario {scenario.name}: {str(e)}")
                self.current_run.errors.append(f"Save error: {scenario.name}")
        
        return saved_paths
    
    async def _learn_from_results(
        self,
        findings: List[ResearchFinding],
        patterns: List[InteractionPattern],
        scenarios: List[GeneratedScenario]
    ):
        """Learn from the discovery results"""
        if not self.evolution_engine:
            return
        
        # Record successful patterns
        for pattern in patterns:
            await self.evolution_engine.record_pattern_success(pattern)
        
        # Learn from generated scenarios
        for scenario in scenarios:
            await self.evolution_engine.learn_from_scenario(scenario)
        
        # Update research strategies
        successful_queries = [f.metadata.get("query") for f in findings if f.relevance_score > 0.8]
        await self.evolution_engine.update_research_strategies(successful_queries)
    
    def _calculate_metrics(
        self,
        findings: List[ResearchFinding],
        patterns: List[InteractionPattern],
        scenarios: List[GeneratedScenario]
    ) -> Dict[str, Any]:
        """Calculate run metrics"""
        return {
            "average_finding_relevance": sum(f.relevance_score for f in findings) / len(findings) if findings else 0,
            "pattern_diversity": len(set(p.flow_type for p in patterns)),
            "module_coverage": len(set(m for s in scenarios for m in s.modules)),
            "optimization_patterns_used": sum(len(s.optimization_notes) for s in scenarios),
            "unique_patterns_found": len(set(p for f in findings for p in f.patterns_found)),
            "scenarios_per_pattern": len(scenarios) / len(patterns) if patterns else 0
        }
    
    def _extract_modules_from_findings(self, findings: List[ResearchFinding]) -> List[str]:
        """Extract relevant modules from findings"""
        modules = []
        module_keywords = {
            "marker": ["pdf", "document", "extraction"],
            "sparta": ["security", "vulnerability", "cwe"],
            "arxiv": ["research", "paper", "academic"],
            "llm_call": ["ai", "analysis", "generation"],
            "arangodb": ["graph", "storage", "knowledge"],
            "unsloth": ["training", "model", "fine-tune"],
            "youtube_transcripts": ["video", "tutorial", "talk"]
        }
        
        for finding in findings:
            content_lower = finding.content.lower()
            for module, keywords in module_keywords.items():
                if any(kw in content_lower for kw in keywords) and module not in modules:
                    modules.append(module)
        
        # Always include some core modules
        if "llm_call" not in modules:
            modules.append("llm_call")
        if "test_reporter" not in modules:
            modules.append("test_reporter")
        
        return modules
    
    def _determine_flow_type(self, pattern_type: str) -> str:
        """Determine flow type from pattern"""
        if "parallel" in pattern_type:
            return "parallel"
        elif "event" in pattern_type or "async" in pattern_type:
            return "event_driven"
        elif "pipeline" in pattern_type or "sequential" in pattern_type:
            return "sequential"
        else:
            return "hybrid"
    
    def _create_pattern_steps(self, modules: List[str], pattern_type: str) -> List[Dict[str, Any]]:
        """Create basic steps for a pattern"""
        steps = []
        
        for i, module in enumerate(modules):
            step = {
                "from_module": "coordinator" if i == 0 else modules[i-1],
                "to_module": module,
                "content": {"task": f"process_{pattern_type}"}
            }
            steps.append(step)
        
        return steps
    
    def _load_run_history(self):
        """Load run history from disk"""
        history_file = self.data_dir / "run_history.json"
        if history_file.exists():
            with open(history_file, 'r') as f:
                data = json.load(f)
                # Convert to DiscoveryRun objects
                self.run_history = []
                for run_data in data:
                    run = DiscoveryRun(
                        run_id=run_data["run_id"],
                        start_time=datetime.fromisoformat(run_data["start_time"]),
                        end_time=datetime.fromisoformat(run_data["end_time"]) if run_data.get("end_time") else None,
                        findings_count=run_data.get("findings_count", 0),
                        patterns_discovered=run_data.get("patterns_discovered", 0),
                        scenarios_generated=run_data.get("scenarios_generated", 0),
                        scenarios_saved=run_data.get("scenarios_saved", []),
                        errors=run_data.get("errors", []),
                        metrics=run_data.get("metrics", {})
                    )
                    self.run_history.append(run)
    
    def _save_run_history(self):
        """Save run history to disk"""
        history_file = self.data_dir / "run_history.json"
        data = []
        
        for run in self.run_history[-100:]:  # Keep last 100 runs
            data.append({
                "run_id": run.run_id,
                "start_time": run.start_time.isoformat(),
                "end_time": run.end_time.isoformat() if run.end_time else None,
                "findings_count": run.findings_count,
                "patterns_discovered": run.patterns_discovered,
                "scenarios_generated": run.scenarios_generated,
                "scenarios_saved": run.scenarios_saved,
                "errors": run.errors,
                "metrics": run.metrics
            })
        
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def schedule_discovery(self):
        """Schedule discovery runs"""
        # Daily full discovery at 2 AM
        schedule.every().day.at("02:00").do(
            lambda: asyncio.run(self.run_discovery_cycle())
        )
        
        # Quick discovery every 6 hours
        schedule.every(6).hours.do(
            lambda: asyncio.run(self.run_discovery_cycle(
                categories=["optimization"],  # Just optimization
                force_refresh=False  # Use cache
            ))
        )
        
        logger.info("Discovery scheduled: Daily at 2 AM, Quick scan every 6 hours")
    
    def run_scheduler(self):
        """Run the scheduler (blocking)"""
        logger.info("Starting discovery scheduler...")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get discovery statistics"""
        if not self.run_history:
            return {"message": "No discovery runs yet"}
        
        total_runs = len(self.run_history)
        successful_runs = len([r for r in self.run_history if not r.errors])
        total_scenarios = sum(r.scenarios_generated for r in self.run_history)
        total_findings = sum(r.findings_count for r in self.run_history)
        
        recent_runs = self.run_history[-10:]
        avg_scenarios = sum(r.scenarios_generated for r in recent_runs) / len(recent_runs)
        avg_duration = sum(
            (r.end_time - r.start_time).total_seconds() 
            for r in recent_runs if r.end_time
        ) / len(recent_runs)
        
        return {
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "success_rate": successful_runs / total_runs,
            "total_scenarios_generated": total_scenarios,
            "total_findings_processed": total_findings,
            "average_scenarios_per_run": avg_scenarios,
            "average_run_duration_seconds": avg_duration,
            "last_run": self.run_history[-1].run_id if self.run_history else None,
            "last_run_time": self.run_history[-1].start_time.isoformat() if self.run_history else None
        }


if __name__ == "__main__":
    # Test the orchestrator
    async def test_orchestrator():
        orchestrator = DiscoveryOrchestrator(enable_learning=False)  # Disable learning for test
        
        # Run a discovery cycle
        logger.info("Running test discovery cycle...")
        run = await orchestrator.run_discovery_cycle(
            categories=["optimization", "ml_patterns"],
            force_refresh=False
        )
        
        # Print results
        print(f"\nDiscovery Run: {run.run_id}")
        print(f"Findings: {run.findings_count}")
        print(f"Patterns: {run.patterns_discovered}")
        print(f"Scenarios: {run.scenarios_generated}")
        print(f"Saved: {len(run.scenarios_saved)}")
        
        if run.errors:
            print(f"Errors: {run.errors}")
        
        print(f"\nMetrics: {json.dumps(run.metrics, indent=2)}")
        
        # Show statistics
        stats = orchestrator.get_statistics()
        print(f"\nStatistics: {json.dumps(stats, indent=2)}")
    
    # Run test
    asyncio.run(test_orchestrator())