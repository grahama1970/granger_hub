"""
Comprehensive tests for the Self-Improvement System
"""

import pytest
import asyncio
from pathlib import Path
import json
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.claude_coms.discovery.self_improvement_engine import (
    SelfImprovementEngine,
    ProjectAnalysis,
    ImprovementProposal
)
from src.claude_coms.discovery.discovery_orchestrator import DiscoveryRun


class TestSelfImprovementEngine:
    """Test the self-improvement engine"""
    
    @pytest.fixture
    def engine(self, tmp_path):
        """Create engine with test workspace"""
        # Create mock project structure
        test_workspace = tmp_path / "workspace"
        test_workspace.mkdir()
        
        # Create hub project
        hub_path = test_workspace / "claude-module-communicator"
        hub_path.mkdir()
        (hub_path / "src").mkdir()
        (hub_path / "tests").mkdir()
        (hub_path / "docs").mkdir()
        
        # Create spoke projects
        spokes = ["marker", "sparta", "arangodb"]
        for spoke in spokes:
            spoke_path = test_workspace / spoke
            spoke_path.mkdir()
            (spoke_path / "src").mkdir()
            (spoke_path / "tests").mkdir()
        
        engine = SelfImprovementEngine(workspace_root=test_workspace)
        return engine
    
    @pytest.mark.asyncio
    async def test_analyze_ecosystem(self, engine):
        """Test ecosystem analysis"""
        # Run analysis
        analyses = await engine.analyze_ecosystem()
        
        # Verify hub was analyzed
        assert "hub" in analyses
        assert analyses["hub"].project_name == "claude-module-communicator"
        assert analyses["hub"].role == "hub"
        
        # Verify some spokes were analyzed
        assert len(analyses) >= 2  # At least hub + 1 spoke
        
        # Check analysis properties
        for name, analysis in analyses.items():
            assert isinstance(analysis, ProjectAnalysis)
            assert analysis.test_coverage >= 0
            assert analysis.test_coverage <= 1
            assert isinstance(analysis.integration_points, list)
            assert isinstance(analysis.last_commit, datetime)
    
    @pytest.mark.asyncio
    async def test_discover_improvements(self, engine):
        """Test improvement discovery"""
        # Mock the discovery system
        with patch.object(engine.discovery, 'run_discovery_cycle') as mock_discovery:
            # Create mock discovery run
            mock_run = DiscoveryRun(
                run_id="test_run",
                start_time=datetime.now(),
                end_time=datetime.now(),
                findings_count=5,
                patterns_discovered=3,
                scenarios_generated=2,
                scenarios_saved=["test_scenario.py"]
            )
            mock_discovery.return_value = mock_run
            
            # Mock current patterns extraction
            with patch.object(engine, '_extract_current_patterns') as mock_patterns:
                mock_patterns.return_value = []
                
                # Run discovery
                proposals = await engine.discover_improvements()
                
                # Verify proposals were generated
                assert isinstance(proposals, list)
                assert all(isinstance(p, ImprovementProposal) for p in proposals)
                
                # Verify discovery was called
                mock_discovery.assert_called_once()
    
    def test_create_integration_proposal(self, engine):
        """Test integration gap proposal creation"""
        proposal = engine._create_integration_gap_proposal("marker", "arangodb")
        
        assert proposal.id.startswith("IMPROVE_")
        assert "marker" in proposal.title
        assert "arangodb" in proposal.title
        assert proposal.category == "integration"
        assert proposal.priority == "high"
        assert len(proposal.implementation_steps) > 0
        assert len(proposal.expected_benefits) > 0
        assert "marker" in proposal.affected_projects
        assert "arangodb" in proposal.affected_projects
    
    def test_create_performance_proposal(self, engine):
        """Test performance improvement proposal"""
        bottleneck = {
            "project": "test_project",
            "issue": "high_latency",
            "metric": 500
        }
        
        proposal = engine._create_performance_improvement(bottleneck)
        
        assert proposal.category == "performance"
        assert proposal.priority == "high"
        assert "test_project" in proposal.affected_projects
        assert "500ms" in proposal.rationale
        assert any("caching" in step.lower() for step in proposal.implementation_steps)
    
    @pytest.mark.asyncio
    async def test_generate_improvement_tasks(self, engine, tmp_path):
        """Test task file generation"""
        # Create test proposals
        proposals = [
            ImprovementProposal(
                id="IMPROVE_001",
                title="Test Integration",
                priority="high",
                category="integration",
                affected_projects=["marker", "arangodb"],
                description="Test description",
                rationale="Test rationale",
                implementation_steps=["Step 1", "Step 2"],
                expected_benefits=["Benefit 1"],
                estimated_effort="2 days",
                test_scenarios=["test_scenario"],
                metrics_to_track=["metric1"]
            )
        ]
        
        engine.proposals = proposals
        
        # Generate tasks
        output_dir = tmp_path / "tasks"
        files = await engine.generate_improvement_tasks(output_dir)
        
        # Verify files were created
        assert len(files) == 2  # 1 proposal + 1 summary
        assert any("IMPROVE_001" in str(f) for f in files)
        assert any("SUMMARY" in str(f) for f in files)
        
        # Verify content
        task_file = next(f for f in files if "IMPROVE_001" in str(f))
        content = task_file.read_text()
        
        assert "Test Integration" in content
        assert "high" in content
        assert "Step 1" in content
        assert "Benefit 1" in content
    
    def test_prioritize_improvements(self, engine):
        """Test improvement prioritization"""
        proposals = [
            ImprovementProposal(
                id="P1",
                title="Performance Fix",
                priority="",
                category="performance",
                affected_projects=["a", "b", "c"],
                description="",
                rationale="",
                implementation_steps=[],
                expected_benefits=[],
                estimated_effort="2 hours",
                test_scenarios=[],
                metrics_to_track=[]
            ),
            ImprovementProposal(
                id="P2",
                title="Documentation",
                priority="",
                category="documentation",
                affected_projects=["a"],
                description="",
                rationale="",
                implementation_steps=[],
                expected_benefits=[],
                estimated_effort="1 day",
                test_scenarios=[],
                metrics_to_track=[]
            ),
            ImprovementProposal(
                id="P3",
                title="Reliability Fix",
                priority="",
                category="reliability",
                affected_projects=["a", "b"],
                description="",
                rationale="",
                implementation_steps=[],
                expected_benefits=[],
                estimated_effort="3 hours",
                test_scenarios=[],
                metrics_to_track=[]
            )
        ]
        
        prioritized = engine._prioritize_improvements(proposals)
        
        # Verify priorities were assigned
        assert all(p.priority in ["high", "medium", "low"] for p in prioritized)
        
        # Verify reliability is prioritized
        assert prioritized[0].category in ["reliability", "performance"]
        
        # Verify documentation is lower priority
        doc_proposal = next(p for p in prioritized if p.category == "documentation")
        assert doc_proposal.priority in ["medium", "low"]
    
    @pytest.mark.asyncio
    async def test_analyze_project_test_coverage(self, engine, tmp_path):
        """Test project test coverage calculation"""
        # Create project with tests
        project_path = tmp_path / "test_project"
        project_path.mkdir()
        
        src_dir = project_path / "src"
        src_dir.mkdir()
        (src_dir / "module1.py").write_text("# code")
        (src_dir / "module2.py").write_text("# code")
        
        test_dir = project_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_module1.py").write_text("# test")
        
        # Calculate coverage
        coverage = await engine._get_test_coverage(project_path)
        
        # Should be 0.5 (1 test file for 2 source files)
        assert coverage == 0.5
    
    @pytest.mark.asyncio
    async def test_integration_gap_detection(self, engine):
        """Test detection of missing integrations"""
        # Get spoke pairs
        pairs = engine._get_spoke_pairs()
        
        assert len(pairs) > 0
        assert all(len(pair) == 2 for pair in pairs)
        
        # Important pairs should be included
        assert ("marker", "arangodb") in pairs
        assert ("sparta", "test_reporter") in pairs
    
    def test_generate_task_markdown_format(self, engine):
        """Test markdown generation format"""
        proposal = ImprovementProposal(
            id="TEST_001",
            title="Test Proposal",
            priority="high",
            category="integration",
            affected_projects=["project1", "project2"],
            description="This is a test proposal",
            rationale="Testing is important",
            implementation_steps=["Do this", "Then that"],
            expected_benefits=["Better testing", "More confidence"],
            estimated_effort="1 day",
            test_scenarios=["scenario1", "scenario2"],
            metrics_to_track=["coverage", "performance"]
        )
        
        markdown = engine._generate_task_markdown(proposal)
        
        # Verify all sections are present
        assert "# Test Proposal" in markdown
        assert "**Task ID**: TEST_001" in markdown
        assert "**Priority**: high" in markdown
        assert "## Overview" in markdown
        assert "## Rationale" in markdown
        assert "## Implementation Steps" in markdown
        assert "1. Do this" in markdown
        assert "2. Then that" in markdown
        assert "## Expected Benefits" in markdown
        assert "- Better testing" in markdown
        assert "## Test Scenarios" in markdown
        assert "## Metrics to Track" in markdown
        assert "## Acceptance Criteria" in markdown
    
    @pytest.mark.asyncio
    async def test_full_self_improvement_cycle(self, engine, tmp_path):
        """Test complete self-improvement cycle"""
        # Mock discovery
        with patch.object(engine.discovery, 'run_discovery_cycle') as mock_discovery:
            mock_run = DiscoveryRun(
                run_id="full_cycle_test",
                start_time=datetime.now(),
                end_time=datetime.now(),
                findings_count=10,
                patterns_discovered=5,
                scenarios_generated=3,
                scenarios_saved=[]
            )
            mock_discovery.return_value = mock_run
            
            # Run full cycle
            # 1. Analyze ecosystem
            analyses = await engine.analyze_ecosystem()
            assert len(analyses) > 0
            
            # 2. Discover improvements
            proposals = await engine.discover_improvements()
            assert len(proposals) > 0
            
            # 3. Generate task files
            output_dir = tmp_path / "output"
            files = await engine.generate_improvement_tasks(output_dir)
            assert len(files) > 0
            
            # Verify output structure
            assert output_dir.exists()
            assert any(f.name.startswith("IMPROVE_") for f in output_dir.iterdir())
            assert (output_dir / "IMPROVEMENT_PROPOSALS_SUMMARY.md").exists()


class TestSelfImprovementIntegration:
    """Integration tests with discovery system"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_discovery_integration(self, tmp_path):
        """Test integration with discovery system"""
        engine = SelfImprovementEngine(workspace_root=tmp_path)
        
        # Create mock scenario metadata
        scenario_metadata = {
            "name": "TestOptimizedPattern",
            "description": "A test pattern",
            "modules": ["marker", "llm_call", "arangodb"],
            "optimization_notes": ["Uses caching", "Parallel processing"]
        }
        
        # Create metadata file
        scenario_dir = tmp_path / "scenarios"
        scenario_dir.mkdir()
        metadata_file = scenario_dir / "test_scenario_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(scenario_metadata, f)
        
        # Test pattern improvement creation
        with patch.object(engine, '_extract_current_patterns') as mock_patterns:
            mock_patterns.return_value = []  # No current patterns
            
            proposal = engine._create_pattern_improvement(scenario_metadata)
            
            assert proposal is not None
            assert "TestOptimizedPattern" in proposal.title
            assert all(m in proposal.affected_projects for m in ["marker", "llm_call", "arangodb"])
            assert "Uses caching" in proposal.expected_benefits


class TestPerformanceAndReliability:
    """Test performance and reliability aspects"""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_large_ecosystem_analysis(self, tmp_path):
        """Test with many projects"""
        # Create many mock projects
        workspace = tmp_path / "large_workspace"
        workspace.mkdir()
        
        for i in range(20):
            project = workspace / f"project_{i}"
            project.mkdir()
            (project / "src").mkdir()
            (project / "tests").mkdir()
        
        engine = SelfImprovementEngine(workspace_root=workspace)
        
        # Time the analysis
        start = datetime.now()
        analyses = await engine.analyze_ecosystem()
        duration = (datetime.now() - start).total_seconds()
        
        # Should complete reasonably fast
        assert duration < 10.0  # 10 seconds max
        assert len(analyses) >= 1  # At least hub
    
    @pytest.mark.asyncio
    async def test_error_handling(self, tmp_path):
        """Test error handling in analysis"""
        engine = SelfImprovementEngine(workspace_root=tmp_path / "nonexistent")
        
        # Should handle missing workspace gracefully
        analyses = await engine.analyze_ecosystem()
        
        # Should still return some results
        assert isinstance(analyses, dict)
        
        # Test with corrupted project
        workspace = tmp_path / "corrupted"
        workspace.mkdir()
        
        engine = SelfImprovementEngine(workspace_root=workspace)
        
        # Create project with invalid structure
        bad_project = workspace / "bad_project"
        bad_project.write_text("not a directory")
        
        # Should handle gracefully
        analyses = await engine.analyze_ecosystem()
        assert isinstance(analyses, dict)


@pytest.mark.asyncio
async def test_improvement_task_validation():
    """Validate generated improvement tasks"""
    from src.claude_coms.discovery.self_improvement_engine import run_self_improvement
    
    with patch('src.claude_coms.discovery.self_improvement_engine.SelfImprovementEngine') as MockEngine:
        mock_engine = MockEngine.return_value
        mock_engine.analyze_ecosystem = AsyncMock(return_value={})
        mock_engine.discover_improvements = AsyncMock(return_value=[
            ImprovementProposal(
                id="VAL_001",
                title="Validation Test",
                priority="high",
                category="testing",
                affected_projects=["test"],
                description="Test",
                rationale="Test",
                implementation_steps=["Test"],
                expected_benefits=["Test"],
                estimated_effort="1 hour",
                test_scenarios=["test"],
                metrics_to_track=["test"]
            )
        ])
        mock_engine.generate_improvement_tasks = AsyncMock(return_value=[Path("test.md")])
        
        # Run improvement
        proposals = await run_self_improvement()
        
        # Verify mocks were called
        mock_engine.analyze_ecosystem.assert_called_once()
        mock_engine.discover_improvements.assert_called_once()
        mock_engine.generate_improvement_tasks.assert_called_once()


if __name__ == "__main__":
    # Run with test reporter integration
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--cov=src.claude_coms.discovery.self_improvement_engine",
        "--cov-report=html",
        "--cov-report=term"
    ])