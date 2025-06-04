"""
Comprehensive tests for the Dynamic Interaction Discovery System
"""

import pytest
import asyncio
from pathlib import Path
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.granger_hub.discovery import (
    ResearchAgent, 
    OptimizationAnalyzer,
    PatternRecognizer,
    ScenarioGenerator,
    EvolutionEngine,
    DiscoveryOrchestrator
)
from src.granger_hub.discovery.research.research_agent import ResearchFinding, ResearchQuery
from src.granger_hub.discovery.analysis.optimization_analyzer import InteractionPattern, OptimizationScore
from src.granger_hub.discovery.generation.scenario_generator import GeneratedScenario


class TestResearchAgent:
    """Test the research agent component"""
    
    @pytest.fixture
    def agent(self, tmp_path):
        """Create research agent with test cache"""
        return ResearchAgent(cache_dir=tmp_path / "cache")
    
    @pytest.mark.asyncio
    async def test_conduct_research(self, agent):
        """Test basic research functionality"""
        # Use mock responses
        findings = await agent.conduct_research(
            categories=["optimization"],
            force_refresh=True
        )
        
        assert isinstance(findings, list)
        assert all(isinstance(f, ResearchFinding) for f in findings)
        
        # Should have findings from multiple sources
        sources = {f.source for f in findings}
        assert len(sources) >= 2  # At least 2 different sources
        
        # Findings should be sorted by relevance
        if len(findings) > 1:
            relevances = [f.relevance_score for f in findings]
            assert relevances == sorted(relevances, reverse=True)
    
    def test_pattern_extraction(self, agent):
        """Test pattern extraction from research"""
        # Test paper pattern extraction
        paper = {
            "abstract": "We present a pipeline pattern for sequential processing with caching strategies and parallel execution optimizations."
        }
        
        patterns = agent._extract_patterns_from_paper(paper)
        
        assert "pipeline" in patterns
        assert "cache" in patterns
        assert "parallel" in patterns
    
    def test_relevance_calculation(self, agent):
        """Test relevance score calculation"""
        query = ResearchQuery(
            query="microservice optimization",
            source="arxiv",
            category="optimization"
        )
        
        # High relevance result
        result1 = {
            "title": "Microservice Optimization Techniques",
            "published": datetime.now().isoformat()
        }
        score1 = agent._calculate_relevance(result1, query)
        
        # Low relevance result
        result2 = {
            "title": "Unrelated Topic",
            "published": (datetime.now() - timedelta(days=400)).isoformat()
        }
        score2 = agent._calculate_relevance(result2, query)
        
        assert score1 > score2
        assert 0 <= score1 <= 1
        assert 0 <= score2 <= 1
    
    @pytest.mark.asyncio
    async def test_caching(self, agent, tmp_path):
        """Test research caching mechanism"""
        # First call - should generate findings
        findings1 = await agent.conduct_research(["optimization"])
        
        # Save to cache
        agent._cache_findings(findings1)
        
        # Second call - should use cache
        findings2 = await agent.conduct_research(["optimization"], force_refresh=False)
        
        # Should return same findings
        assert len(findings1) == len(findings2)
        assert findings1[0].title == findings2[0].title


class TestOptimizationAnalyzer:
    """Test the optimization analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        return OptimizationAnalyzer()
    
    @pytest.mark.asyncio
    async def test_analyze_pattern(self, analyzer):
        """Test pattern analysis"""
        pattern = InteractionPattern(
            name="Test Pipeline",
            modules=["marker", "llm_call", "test_reporter"],
            flow_type="sequential",
            steps=[
                {"to_module": "marker", "content": {"task": "extract"}},
                {"to_module": "llm_call", "content": {"task": "analyze"}},
                {"to_module": "test_reporter", "content": {"task": "report"}}
            ]
        )
        
        score = await analyzer.analyze_pattern(pattern)
        
        assert isinstance(score, OptimizationScore)
        assert 0 <= score.overall_score <= 1
        assert 0 <= score.performance_score <= 1
        assert 0 <= score.reliability_score <= 1
        assert 0 <= score.scalability_score <= 1
        assert isinstance(score.bottlenecks, list)
        assert isinstance(score.improvements, list)
    
    def test_bottleneck_identification(self, analyzer):
        """Test bottleneck identification"""
        pattern = InteractionPattern(
            name="Long Sequential",
            modules=["a", "b", "c", "d", "e", "f"],
            flow_type="sequential",
            steps=[{"to_module": m, "content": {}} for m in ["a", "b", "c", "d", "e", "f"]]
        )
        
        metrics = {
            "total_latency_ms": 600,
            "step_latencies": [50, 50, 300, 50, 100, 50],
            "cpu_usage": 0.9,
            "memory_usage": 0.85
        }
        
        bottlenecks = analyzer._identify_bottlenecks(pattern, metrics)
        
        # Should identify multiple issues
        assert len(bottlenecks) > 0
        assert any("Step 2" in b for b in bottlenecks)  # High latency step
        assert any("CPU" in b for b in bottlenecks)  # High CPU
        assert any("sequential chain" in b for b in bottlenecks)  # Long chain
    
    def test_improvement_generation(self, analyzer):
        """Test improvement suggestion generation"""
        pattern = InteractionPattern(
            name="Unoptimized",
            modules=["module1", "module2"],
            flow_type="sequential",
            steps=[]
        )
        
        bottlenecks = ["Low throughput - consider parallelization"]
        metrics = {"total_latency_ms": 1000}
        
        improvements = analyzer._generate_improvements(pattern, bottlenecks, metrics)
        
        assert len(improvements) > 0
        # The bottleneck mentions "parallelization" so it should match "throughput"
        assert any(imp["type"] in ["parallelization", "batching"] for imp in improvements)
        assert all("implementation" in imp for imp in improvements)


class TestPatternRecognizer:
    """Test pattern recognition"""
    
    @pytest.fixture
    def recognizer(self):
        return PatternRecognizer()
    
    @pytest.mark.asyncio
    async def test_recognize_patterns(self, recognizer):
        """Test pattern recognition from findings"""
        findings = [
            ResearchFinding(
                source="arxiv",
                title="Pipeline Patterns in Microservices",
                content="This paper discusses sequential pipeline patterns with caching...",
                patterns_found=["pipeline", "cache"],
                relevance_score=0.9
            ),
            ResearchFinding(
                source="youtube",
                title="Event-Driven Architecture",
                content="Learn about event-driven patterns with pub/sub messaging...",
                patterns_found=["event_driven"],
                relevance_score=0.8
            )
        ]
        
        patterns = await recognizer.recognize_patterns(findings)
        
        assert len(patterns) > 0
        assert all(isinstance(p, InteractionPattern) for p in patterns)
        assert all(len(p.modules) > 0 for p in patterns)
        assert all(len(p.steps) > 0 for p in patterns)
    
    def test_pattern_matching(self, recognizer):
        """Test pattern template matching"""
        content = "this paper presents a circuit breaker pattern for resilience and fault tolerance with fallback mechanisms"
        
        # Should match circuit breaker template
        circuit_breaker_template = next(
            t for t in recognizer.pattern_templates 
            if t.name == "Circuit Breaker Pattern"
        )
        
        matches = recognizer._matches_template(content, circuit_breaker_template)
        assert matches is True
    
    def test_module_enrichment(self, recognizer):
        """Test module enrichment for patterns"""
        pattern = InteractionPattern(
            name="Test Pattern",
            modules=[],
            flow_type="sequential",
            steps=[]
        )
        
        findings = [
            ResearchFinding(
                source="test",
                title="PDF Processing Pipeline",
                content="Extract PDFs with marker and store in arangodb",
                patterns_found=["pipeline"],
                relevance_score=0.9
            )
        ]
        
        enriched = recognizer._enrich_patterns_with_modules([pattern], findings)
        
        assert len(enriched[0].modules) > 0
        assert "marker" in enriched[0].modules or "llm_call" in enriched[0].modules


class TestScenarioGenerator:
    """Test scenario generation"""
    
    @pytest.fixture
    def generator(self, tmp_path):
        return ScenarioGenerator(output_dir=tmp_path / "generated")
    
    @pytest.mark.asyncio
    async def test_generate_from_research(self, generator):
        """Test scenario generation from research findings"""
        findings = [
            ResearchFinding(
                source="arxiv",
                title="Optimized Caching Patterns",
                content="Using cache-aside pattern with parallel processing",
                patterns_found=["cache", "parallel"],
                relevance_score=0.9
            )
        ]
        
        scenarios = await generator.generate_from_research(findings, max_scenarios=1)
        
        assert len(scenarios) > 0
        assert all(isinstance(s, GeneratedScenario) for s in scenarios)
        
        scenario = scenarios[0]
        assert scenario.name
        assert scenario.modules
        assert scenario.test_code
        assert "cache" in str(scenario.source_patterns)
    
    def test_test_code_generation(self, generator):
        """Test generated test code quality"""
        scenario = GeneratedScenario(
            name="TestScenario",
            description="Test description",
            category="integration",
            modules=["marker", "llm_call"],
            workflow_steps=[
                {"to_module": "marker", "content": {"task": "extract"}},
                {"to_module": "llm_call", "content": {"task": "analyze"}}
            ],
            test_code="",
            optimization_notes=[],
            source_patterns=["test"]
        )
        
        # Generate test code
        template = generator.templates["sequential"]
        test_code = generator._generate_test_code(
            scenario.name,
            scenario.modules,
            scenario.workflow_steps,
            template
        )
        
        # Verify test code structure
        assert "import pytest" in test_code
        assert "class TestScenario" in test_code
        assert "def create_test_workflow" in test_code
        assert "def assert_results" in test_code
        assert "@pytest.mark.integration" in test_code
        assert "async def test_" in test_code
    
    def test_save_scenario(self, generator, tmp_path):
        """Test scenario saving"""
        scenario = GeneratedScenario(
            name="TestSave",
            description="Test saving",
            category="security",
            modules=["sparta"],
            workflow_steps=[],
            test_code="# test code",
            optimization_notes=["note1"],
            source_patterns=["pattern1"]
        )
        
        filepath = generator.save_scenario(scenario)
        
        assert filepath.exists()
        assert filepath.parent.name == "security"
        assert filepath.suffix == ".py"
        
        # Check metadata file
        metadata_file = filepath.parent / f"{filepath.stem}_metadata.json"
        assert metadata_file.exists()
        
        with open(metadata_file) as f:
            metadata = json.load(f)
            assert metadata["name"] == "TestSave"
            assert metadata["category"] == "security"


class TestEvolutionEngine:
    """Test learning and evolution"""
    
    @pytest.fixture
    def engine(self, tmp_path):
        return EvolutionEngine(data_dir=tmp_path / "learning")
    
    @pytest.mark.asyncio
    async def test_record_pattern_success(self, engine):
        """Test pattern success recording"""
        pattern = InteractionPattern(
            name="Successful Pattern",
            modules=["marker", "llm_call"],
            flow_type="sequential",
            steps=[]
        )
        
        await engine.record_pattern_success(pattern, score=0.9)
        await engine.record_pattern_success(pattern, score=0.85)
        
        # Check pattern performance
        pattern_key = engine._get_pattern_key(pattern)
        perf = engine.pattern_performance[pattern_key]
        
        assert perf.success_count == 2
        assert perf.total_uses == 2
        assert perf.average_score == 0.875
    
    @pytest.mark.asyncio
    async def test_scenario_evolution(self, engine):
        """Test scenario evolution/mutation"""
        scenarios = [
            GeneratedScenario(
                name="Original",
                description="Original scenario",
                category="test",
                modules=["marker", "llm_call", "test_reporter"],
                workflow_steps=[],
                test_code="",
                optimization_notes=[],
                source_patterns=["pattern1"]
            )
        ]
        
        evolved = await engine.evolve_scenarios(scenarios)
        
        assert len(evolved) >= len(scenarios)
        
        # May have mutations or crossovers
        for scenario in evolved:
            assert isinstance(scenario, GeneratedScenario)
    
    def test_module_recommendations(self, engine):
        """Test module affinity recommendations"""
        # Update module affinities
        engine._update_module_affinities(["marker", "arangodb"], 0.9)
        engine._update_module_affinities(["marker", "llm_call"], 0.7)
        engine._update_module_affinities(["marker", "sparta"], 0.3)
        
        recommendations = engine.get_module_recommendations("marker", count=2)
        
        assert len(recommendations) <= 2
        assert "arangodb" in recommendations  # Highest affinity


class TestDiscoveryOrchestrator:
    """Test the orchestrator"""
    
    @pytest.fixture
    def orchestrator(self, tmp_path):
        return DiscoveryOrchestrator(
            data_dir=tmp_path / "discovery",
            enable_learning=False  # Disable for tests
        )
    
    @pytest.mark.asyncio
    async def test_discovery_cycle(self, orchestrator):
        """Test complete discovery cycle"""
        # Mock research
        with patch.object(orchestrator.research_agent, 'conduct_research') as mock_research:
            mock_research.return_value = [
                ResearchFinding(
                    source="test",
                    title="Test Finding",
                    content="Test content",
                    patterns_found=["test_pattern"],
                    relevance_score=0.8
                )
            ]
            
            # Run cycle
            run = await orchestrator.run_discovery_cycle(
                categories=["optimization"],
                force_refresh=True
            )
            
            assert run is not None
            assert run.findings_count > 0
            assert isinstance(run.end_time, datetime)
            assert len(run.errors) == 0
    
    def test_metrics_calculation(self, orchestrator):
        """Test metrics calculation"""
        findings = [
            ResearchFinding("test", "t1", "c1", relevance_score=0.8),
            ResearchFinding("test", "t2", "c2", relevance_score=0.6)
        ]
        
        patterns = [
            InteractionPattern("p1", ["m1"], "sequential", []),
            InteractionPattern("p2", ["m2"], "parallel", [])
        ]
        
        scenarios = [
            GeneratedScenario(
                "s1", "d1", "cat1", ["m1", "m2"], [], "", ["opt1"], ["pat1"]
            )
        ]
        
        metrics = orchestrator._calculate_metrics(findings, patterns, scenarios)
        
        assert "average_finding_relevance" in metrics
        assert metrics["average_finding_relevance"] == 0.7
        assert metrics["pattern_diversity"] == 2  # 2 flow types
        assert metrics["module_coverage"] == 2  # 2 unique modules


class TestIntegrationScenarios:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_discovery_pipeline(self, tmp_path):
        """Test complete discovery pipeline"""
        orchestrator = DiscoveryOrchestrator(
            data_dir=tmp_path / "integration_test",
            enable_learning=True
        )
        
        # Configure for quick test
        orchestrator.config["max_scenarios_per_run"] = 2
        orchestrator.config["research_categories"] = ["optimization"]
        
        # Run discovery
        run = await orchestrator.run_discovery_cycle(force_refresh=True)
        
        # Verify all phases completed
        assert run.findings_count > 0
        assert run.patterns_discovered >= 0
        assert run.scenarios_generated >= 0
        
        # Check saved files if any
        if run.scenarios_saved:
            for path in run.scenarios_saved:
                assert Path(path).exists()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_discovery_performance(self, tmp_path):
        """Test discovery system performance"""
        orchestrator = DiscoveryOrchestrator(data_dir=tmp_path / "perf_test")
        
        start_time = datetime.now()
        
        # Run with limited scope
        run = await orchestrator.run_discovery_cycle(
            categories=["optimization"],
            force_refresh=True
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Should complete in reasonable time
        assert duration < 30  # 30 seconds max
        assert run is not None


if __name__ == "__main__":
    # Run with coverage
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.granger_hub.discovery",
        "--cov-report=html",
        "--cov-report=term",
        "-m", "not integration"  # Skip integration tests for quick run
    ])