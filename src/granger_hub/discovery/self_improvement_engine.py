"""
Self-Improvement Engine for Claude Module Communicator

Analyzes the hub and spoke projects to generate improvement proposals.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import subprocess
from collections import defaultdict

from loguru import logger

from .discovery_orchestrator import DiscoveryOrchestrator
from .analysis.optimization_analyzer import OptimizationScore
from .generation.scenario_generator import GeneratedScenario


@dataclass
class ProjectAnalysis:
    """Analysis of a project in the ecosystem"""
    project_name: str
    project_path: Path
    role: str  # hub, spoke, mcp_server
    modules_provided: List[str]
    integration_points: List[str]
    test_coverage: float
    last_commit: datetime
    open_issues: List[str]
    performance_metrics: Dict[str, float]
    improvement_opportunities: List[str]


@dataclass
class ImprovementProposal:
    """A proposed improvement for the ecosystem"""
    id: str
    title: str
    priority: str  # high, medium, low
    category: str  # integration, performance, reliability, documentation
    affected_projects: List[str]
    description: str
    rationale: str
    implementation_steps: List[str]
    expected_benefits: List[str]
    estimated_effort: str  # hours or days
    test_scenarios: List[str]
    metrics_to_track: List[str]
    generated_at: datetime = field(default_factory=datetime.now)


class SelfImprovementEngine:
    """Engine for continuous self-improvement of the ecosystem"""
    
    def __init__(self, workspace_root: Path = None):
        self.workspace_root = workspace_root or Path("/home/graham/workspace/experiments")
        self.discovery = DiscoveryOrchestrator()
        
        # Project definitions
        self.projects = {
            "hub": {
                "name": "granger_hub",
                "path": self.workspace_root / "granger_hub",
                "role": "hub"
            },
            "spokes": {
                "rl_commons": {"path": self.workspace_root / "rl_commons", "role": "optimization"},
                "sparta": {"path": self.workspace_root / "sparta", "role": "security"},
                "marker": {"path": self.workspace_root / "marker", "role": "document_processing"},
                "arangodb": {"path": self.workspace_root / "arangodb", "role": "storage"},
                "chat": {"path": self.workspace_root / "chat", "role": "interface"},
                "youtube_transcripts": {"path": self.workspace_root / "youtube_transcripts", "role": "research"},
                "claude_max_proxy": {"path": self.workspace_root / "claude_max_proxy", "role": "llm"},
                "arxiv-mcp-server": {"path": self.workspace_root.parent / "mcp-servers/arxiv-mcp-server", "role": "research"},
                "claude-test-reporter": {"path": self.workspace_root / "claude-test-reporter", "role": "testing"},
                "unsloth_wip": {"path": self.workspace_root / "unsloth_wip", "role": "ml"},
                "mcp-screenshot": {"path": self.workspace_root / "mcp-screenshot", "role": "visual"}
            }
        }
        
        # Analysis cache
        self.project_analyses: Dict[str, ProjectAnalysis] = {}
        self.proposals: List[ImprovementProposal] = []
        self.proposal_counter = 0
    
    async def analyze_ecosystem(self) -> Dict[str, ProjectAnalysis]:
        """Analyze all projects in the ecosystem"""
        logger.info("🔍 Analyzing ecosystem projects...")
        
        # Analyze hub
        hub_analysis = await self._analyze_project(
            "granger_hub",
            self.projects["hub"]["path"],
            "hub"
        )
        self.project_analyses["hub"] = hub_analysis
        
        # Analyze spokes
        for spoke_name, spoke_info in self.projects["spokes"].items():
            if spoke_info["path"].exists():
                analysis = await self._analyze_project(
                    spoke_name,
                    spoke_info["path"],
                    spoke_info["role"]
                )
                self.project_analyses[spoke_name] = analysis
        
        return self.project_analyses
    
    async def discover_improvements(self) -> List[ImprovementProposal]:
        """Discover improvement opportunities using the discovery system"""
        logger.info("🔬 Running discovery cycle for improvements...")
        
        # Run focused discovery on integration patterns
        discovery_run = await self.discovery.run_discovery_cycle(
            categories=["optimization", "reliability"],
            force_refresh=False
        )
        
        # Analyze current integration patterns
        current_patterns = await self._extract_current_patterns()
        
        # Compare with discovered patterns
        improvements = await self._generate_improvements_from_discovery(
            discovery_run,
            current_patterns
        )
        
        # Add ecosystem-specific improvements
        ecosystem_improvements = await self._analyze_ecosystem_gaps()
        improvements.extend(ecosystem_improvements)
        
        # Prioritize improvements
        improvements = self._prioritize_improvements(improvements)
        
        self.proposals = improvements
        return improvements
    
    async def generate_improvement_tasks(
        self,
        output_dir: Path = None
    ) -> List[Path]:
        """Generate improvement task files for human review"""
        output_dir = output_dir or Path("docs/tasks")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        for proposal in self.proposals:
            # Generate task filename
            filename = f"{proposal.id}_{proposal.title.replace(' ', '_').lower()}.md"
            filepath = output_dir / filename
            
            # Generate task content
            content = self._generate_task_markdown(proposal)
            
            # Write file
            with open(filepath, 'w') as f:
                f.write(content)
            
            generated_files.append(filepath)
            logger.info(f"📝 Generated task: {filename}")
        
        # Generate summary file
        summary_file = output_dir / "IMPROVEMENT_PROPOSALS_SUMMARY.md"
        with open(summary_file, 'w') as f:
            f.write(self._generate_summary_markdown())
        generated_files.append(summary_file)
        
        return generated_files
    
    async def _analyze_project(
        self,
        name: str,
        path: Path,
        role: str
    ) -> ProjectAnalysis:
        """Analyze a single project"""
        logger.debug(f"Analyzing project: {name}")
        
        # Get basic metrics
        test_coverage = await self._get_test_coverage(path)
        last_commit = await self._get_last_commit(path)
        open_issues = await self._get_open_issues(path)
        
        # Analyze integration points
        integration_points = await self._analyze_integration_points(path)
        
        # Get performance metrics from recent test runs
        performance_metrics = await self._get_performance_metrics(path)
        
        # Identify improvement opportunities
        opportunities = await self._identify_opportunities(
            name, path, test_coverage, integration_points
        )
        
        # Determine provided modules
        modules_provided = self._get_provided_modules(name, path)
        
        return ProjectAnalysis(
            project_name=name,
            project_path=path,
            role=role,
            modules_provided=modules_provided,
            integration_points=integration_points,
            test_coverage=test_coverage,
            last_commit=last_commit,
            open_issues=open_issues,
            performance_metrics=performance_metrics,
            improvement_opportunities=opportunities
        )
    
    async def _extract_current_patterns(self) -> List[Dict[str, Any]]:
        """Extract currently implemented integration patterns"""
        patterns = []
        
        # Analyze test scenarios
        test_dir = self.projects["hub"]["path"] / "tests/integration_scenarios"
        if test_dir.exists():
            for test_file in test_dir.rglob("test_*.py"):
                pattern = await self._extract_pattern_from_test(test_file)
                if pattern:
                    patterns.append(pattern)
        
        # Analyze actual module communications
        src_dir = self.projects["hub"]["path"] / "src"
        for py_file in src_dir.rglob("*.py"):
            file_patterns = await self._extract_patterns_from_code(py_file)
            patterns.extend(file_patterns)
        
        return patterns
    
    async def _generate_improvements_from_discovery(
        self,
        discovery_run,
        current_patterns: List[Dict[str, Any]]
    ) -> List[ImprovementProposal]:
        """Generate improvements based on discovery results"""
        improvements = []
        
        # Get generated scenarios from discovery
        scenario_files = discovery_run.scenarios_saved
        
        for scenario_file in scenario_files:
            # Load scenario metadata
            metadata_file = Path(scenario_file).parent / f"{Path(scenario_file).stem}_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Check if pattern is already implemented
                if not self._is_pattern_implemented(metadata, current_patterns):
                    improvement = self._create_pattern_improvement(metadata)
                    improvements.append(improvement)
        
        return improvements
    
    async def _analyze_ecosystem_gaps(self) -> List[ImprovementProposal]:
        """Analyze gaps in the ecosystem integration"""
        gaps = []
        
        # Check spoke-to-spoke communication
        spoke_pairs = self._get_spoke_pairs()
        for spoke1, spoke2 in spoke_pairs:
            if not self._has_integration_test(spoke1, spoke2):
                gap = self._create_integration_gap_proposal(spoke1, spoke2)
                gaps.append(gap)
        
        # Check performance bottlenecks
        bottlenecks = self._analyze_performance_bottlenecks()
        for bottleneck in bottlenecks:
            gap = self._create_performance_improvement(bottleneck)
            gaps.append(gap)
        
        # Check missing error handling
        error_gaps = self._analyze_error_handling()
        gaps.extend(error_gaps)
        
        # Check documentation gaps
        doc_gaps = self._analyze_documentation_gaps()
        gaps.extend(doc_gaps)
        
        return gaps
    
    def _prioritize_improvements(
        self,
        improvements: List[ImprovementProposal]
    ) -> List[ImprovementProposal]:
        """Prioritize improvements based on impact and effort"""
        # Score each improvement
        for improvement in improvements:
            score = 0
            
            # High priority for reliability and performance
            if improvement.category in ["reliability", "performance"]:
                score += 3
            
            # Medium priority for new integrations
            if improvement.category == "integration":
                score += 2
            
            # Consider number of affected projects
            score += len(improvement.affected_projects) * 0.5
            
            # Consider effort (lower effort = higher priority)
            if "hours" in improvement.estimated_effort:
                score += 1
            
            improvement.priority_score = score
        
        # Sort by priority score
        improvements.sort(key=lambda x: x.priority_score, reverse=True)
        
        # Assign priority labels
        for i, improvement in enumerate(improvements):
            if i < len(improvements) // 3:
                improvement.priority = "high"
            elif i < 2 * len(improvements) // 3:
                improvement.priority = "medium"
            else:
                improvement.priority = "low"
        
        return improvements
    
    def _generate_task_markdown(self, proposal: ImprovementProposal) -> str:
        """Generate markdown content for an improvement task"""
        content = f"""# {proposal.title}

**Task ID**: {proposal.id}  
**Priority**: {proposal.priority}  
**Category**: {proposal.category}  
**Generated**: {proposal.generated_at.strftime('%Y-%m-%d %H:%M')}  
**Estimated Effort**: {proposal.estimated_effort}

## Overview

{proposal.description}

## Rationale

{proposal.rationale}

## Affected Projects

{chr(10).join(f"- {proj}" for proj in proposal.affected_projects)}

## Implementation Steps

{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(proposal.implementation_steps))}

## Expected Benefits

{chr(10).join(f"- {benefit}" for benefit in proposal.expected_benefits)}

## Test Scenarios

The following test scenarios should be implemented to validate this improvement:

{chr(10).join(f"- {scenario}" for scenario in proposal.test_scenarios)}

## Metrics to Track

Monitor these metrics to measure the impact:

{chr(10).join(f"- {metric}" for metric in proposal.metrics_to_track)}

## Acceptance Criteria

- [ ] All implementation steps completed
- [ ] Test scenarios pass
- [ ] Performance metrics show improvement
- [ ] Documentation updated
- [ ] No regression in existing functionality

## Notes

This improvement was automatically generated by the Self-Improvement Engine based on:
- Discovery system findings
- Ecosystem analysis
- Performance metrics
- Integration gap analysis

---

**Status**: Proposed  
**Assignee**: TBD  
**Review**: Required before implementation
"""
        return content
    
    def _generate_summary_markdown(self) -> str:
        """Generate summary of all proposals"""
        high_priority = [p for p in self.proposals if p.priority == "high"]
        medium_priority = [p for p in self.proposals if p.priority == "medium"]
        low_priority = [p for p in self.proposals if p.priority == "low"]
        
        content = f"""# Improvement Proposals Summary

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview

Total proposals: {len(self.proposals)}
- High Priority: {len(high_priority)}
- Medium Priority: {len(medium_priority)}
- Low Priority: {len(low_priority)}

## High Priority Improvements

{self._format_proposal_list(high_priority)}

## Medium Priority Improvements

{self._format_proposal_list(medium_priority)}

## Low Priority Improvements

{self._format_proposal_list(low_priority)}

## Implementation Roadmap

### Phase 1 (Week 1-2)
Focus on high-priority reliability and performance improvements.

### Phase 2 (Week 3-4)
Implement new integration patterns discovered by the system.

### Phase 3 (Week 5-6)
Address documentation and testing gaps.

## Metrics Dashboard

Track these KPIs to measure improvement impact:
- Integration test coverage
- Average response time
- Error rate
- Module coupling score
- Documentation completeness

## Next Steps

1. Review and prioritize proposals
2. Assign tasks to team members
3. Create implementation branches
4. Track progress in project board
"""
        return content
    
    def _format_proposal_list(self, proposals: List[ImprovementProposal]) -> str:
        """Format a list of proposals for markdown"""
        if not proposals:
            return "*No proposals in this category*"
        
        lines = []
        for p in proposals:
            lines.append(
                f"### {p.id}: {p.title}\n"
                f"**Category**: {p.category} | "
                f"**Effort**: {p.estimated_effort} | "
                f"**Projects**: {', '.join(p.affected_projects[:3])}\n"
                f"{p.description[:200]}...\n"
            )
        
        return "\n".join(lines)
    
    # Helper methods for analysis
    async def _get_test_coverage(self, path: Path) -> float:
        """Get test coverage for a project"""
        # Simplified - in production would run actual coverage tools
        test_dir = path / "tests"
        if not test_dir.exists():
            return 0.0
        
        test_files = list(test_dir.rglob("test_*.py"))
        src_files = list((path / "src").rglob("*.py")) if (path / "src").exists() else []
        
        if not src_files:
            return 0.0
        
        # Simple heuristic: ratio of test files to source files
        return min(1.0, len(test_files) / len(src_files))
    
    async def _get_last_commit(self, path: Path) -> datetime:
        """Get last commit date for a project"""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ct"],
                cwd=path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                timestamp = int(result.stdout.strip())
                return datetime.fromtimestamp(timestamp)
        except:
            pass
        return datetime.now()
    
    async def _get_open_issues(self, path: Path) -> List[str]:
        """Get open issues (simplified - would integrate with GitHub API)"""
        # Check for TODO/FIXME in code
        issues = []
        for py_file in path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    for i, line in enumerate(f):
                        if "TODO" in line or "FIXME" in line:
                            issues.append(f"{py_file.name}:{i}: {line.strip()}")
            except:
                pass
        return issues[:10]  # Limit to 10
    
    async def _analyze_integration_points(self, path: Path) -> List[str]:
        """Analyze integration points in a project"""
        integration_points = []
        
        # Look for imports from other projects
        for py_file in path.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    
                # Check for imports from known projects
                for project in self.projects["spokes"].keys():
                    if f"from {project}" in content or f"import {project}" in content:
                        integration_points.append(f"{project}_import")
                
                # Check for MCP tool usage
                if "mcp" in content.lower():
                    integration_points.append("mcp_integration")
            except:
                pass
        
        return list(set(integration_points))
    
    async def _get_performance_metrics(self, path: Path) -> Dict[str, float]:
        """Get performance metrics from test results"""
        # Simplified - would parse actual test reports
        return {
            "avg_response_time_ms": 150,
            "p95_response_time_ms": 500,
            "error_rate": 0.02,
            "throughput_rps": 100
        }
    
    async def _identify_opportunities(
        self,
        name: str,
        path: Path,
        test_coverage: float,
        integration_points: List[str]
    ) -> List[str]:
        """Identify improvement opportunities for a project"""
        opportunities = []
        
        if test_coverage < 0.8:
            opportunities.append(f"Increase test coverage (current: {test_coverage:.1%})")
        
        if len(integration_points) < 2:
            opportunities.append("Add more integration points with other modules")
        
        if not (path / "docs").exists():
            opportunities.append("Add comprehensive documentation")
        
        return opportunities
    
    def _get_provided_modules(self, name: str, path: Path) -> List[str]:
        """Get modules provided by a project"""
        # Map project names to module names
        module_map = {
            "marker": ["marker"],
            "sparta": ["sparta"],
            "arangodb": ["arangodb"],
            "claude_max_proxy": ["llm_call", "claude_max_proxy"],
            "arxiv-mcp-server": ["arxiv"],
            "youtube_transcripts": ["youtube_transcripts"],
            "mcp-screenshot": ["mcp_screenshot"],
            "unsloth_wip": ["unsloth"],
            "claude-test-reporter": ["test_reporter"]
        }
        
        return module_map.get(name, [name])
    
    async def _extract_pattern_from_test(self, test_file: Path) -> Optional[Dict[str, Any]]:
        """Extract pattern information from a test file"""
        try:
            with open(test_file, 'r') as f:
                content = f.read()
                
            # Simple pattern extraction
            pattern = {
                "file": str(test_file),
                "type": "test",
                "modules": []
            }
            
            # Find module usage
            for project in self.projects["spokes"].keys():
                if project in content:
                    pattern["modules"].append(project)
            
            return pattern if pattern["modules"] else None
        except:
            return None
    
    async def _extract_patterns_from_code(self, py_file: Path) -> List[Dict[str, Any]]:
        """Extract integration patterns from code"""
        patterns = []
        # Simplified - would do actual AST analysis
        return patterns
    
    def _is_pattern_implemented(
        self,
        metadata: Dict[str, Any],
        current_patterns: List[Dict[str, Any]]
    ) -> bool:
        """Check if a pattern is already implemented"""
        # Check if modules combination exists
        new_modules = set(metadata.get("modules", []))
        
        for pattern in current_patterns:
            if set(pattern.get("modules", [])) == new_modules:
                return True
        
        return False
    
    def _create_pattern_improvement(
        self,
        metadata: Dict[str, Any]
    ) -> ImprovementProposal:
        """Create improvement proposal from discovered pattern"""
        self.proposal_counter += 1
        
        return ImprovementProposal(
            id=f"IMPROVE_{self.proposal_counter:03d}",
            title=f"Implement {metadata.get('name', 'New Pattern')}",
            priority="medium",
            category="integration",
            affected_projects=metadata.get("modules", []),
            description=f"Implement {metadata.get('description', 'discovered pattern')} "
                       f"using modules: {', '.join(metadata.get('modules', []))}",
            rationale="Pattern discovered by AI system shows optimization potential",
            implementation_steps=[
                "Review generated test scenario",
                "Implement integration in hub",
                "Add error handling",
                "Create integration tests",
                "Update documentation"
            ],
            expected_benefits=metadata.get("optimization_notes", ["Improved integration"]),
            estimated_effort="1-2 days",
            test_scenarios=[metadata.get("name", "test_scenario")],
            metrics_to_track=["response_time", "error_rate", "throughput"]
        )
    
    def _get_spoke_pairs(self) -> List[Tuple[str, str]]:
        """Get pairs of spokes that could integrate"""
        spokes = list(self.projects["spokes"].keys())
        pairs = []
        
        # Key integration pairs
        important_pairs = [
            ("marker", "arangodb"),  # Document to storage
            ("sparta", "test_reporter"),  # Security to reporting
            ("arxiv-mcp-server", "unsloth_wip"),  # Research to ML
            ("youtube_transcripts", "arangodb"),  # Video to storage
            ("claude_max_proxy", "test_reporter"),  # LLM to testing
        ]
        
        return important_pairs
    
    def _has_integration_test(self, spoke1: str, spoke2: str) -> bool:
        """Check if integration test exists between two spokes"""
        # Simplified - would check actual test files
        return False
    
    def _create_integration_gap_proposal(
        self,
        spoke1: str,
        spoke2: str
    ) -> ImprovementProposal:
        """Create proposal for missing integration"""
        self.proposal_counter += 1
        
        return ImprovementProposal(
            id=f"IMPROVE_{self.proposal_counter:03d}",
            title=f"Add {spoke1} ↔ {spoke2} Integration",
            priority="high",
            category="integration",
            affected_projects=[spoke1, spoke2, "granger_hub"],
            description=f"Create integration between {spoke1} and {spoke2} modules",
            rationale=f"No current integration tests between these critical modules",
            implementation_steps=[
                f"Define interface between {spoke1} and {spoke2}",
                "Create adapter in hub",
                "Implement message passing",
                "Add integration tests",
                "Document usage patterns"
            ],
            expected_benefits=[
                "Enable new use cases",
                "Improve data flow",
                "Reduce manual integration effort"
            ],
            estimated_effort="2-3 days",
            test_scenarios=[f"test_{spoke1}_{spoke2}_integration"],
            metrics_to_track=["integration_test_coverage", "api_calls", "latency"]
        )
    
    def _analyze_performance_bottlenecks(self) -> List[Dict[str, Any]]:
        """Analyze performance bottlenecks in the ecosystem"""
        bottlenecks = []
        
        # Check for sequential patterns that could be parallel
        for name, analysis in self.project_analyses.items():
            if analysis.performance_metrics.get("avg_response_time_ms", 0) > 200:
                bottlenecks.append({
                    "project": name,
                    "issue": "high_latency",
                    "metric": analysis.performance_metrics["avg_response_time_ms"]
                })
        
        return bottlenecks
    
    def _create_performance_improvement(
        self,
        bottleneck: Dict[str, Any]
    ) -> ImprovementProposal:
        """Create performance improvement proposal"""
        self.proposal_counter += 1
        
        return ImprovementProposal(
            id=f"IMPROVE_{self.proposal_counter:03d}",
            title=f"Optimize {bottleneck['project']} Performance",
            priority="high",
            category="performance",
            affected_projects=[bottleneck["project"]],
            description=f"Address {bottleneck['issue']} in {bottleneck['project']}",
            rationale=f"Current latency ({bottleneck['metric']}ms) exceeds target",
            implementation_steps=[
                "Profile current implementation",
                "Identify slow operations",
                "Implement caching strategy",
                "Add parallel processing",
                "Optimize database queries"
            ],
            expected_benefits=[
                "50% latency reduction",
                "Improved user experience",
                "Better scalability"
            ],
            estimated_effort="3-5 days",
            test_scenarios=["test_performance_improvement"],
            metrics_to_track=["response_time", "cpu_usage", "memory_usage"]
        )
    
    def _analyze_error_handling(self) -> List[ImprovementProposal]:
        """Analyze error handling gaps"""
        gaps = []
        # Simplified - would analyze actual error handling
        return gaps
    
    def _analyze_documentation_gaps(self) -> List[ImprovementProposal]:
        """Analyze documentation gaps"""
        gaps = []
        
        for name, analysis in self.project_analyses.items():
            if not (analysis.project_path / "docs").exists():
                self.proposal_counter += 1
                gap = ImprovementProposal(
                    id=f"IMPROVE_{self.proposal_counter:03d}",
                    title=f"Document {name} Integration",
                    priority="low",
                    category="documentation",
                    affected_projects=[name],
                    description=f"Add comprehensive documentation for {name}",
                    rationale="Missing documentation hinders adoption",
                    implementation_steps=[
                        "Create README with examples",
                        "Document API endpoints",
                        "Add integration guide",
                        "Include troubleshooting section"
                    ],
                    expected_benefits=["Easier onboarding", "Reduced support requests"],
                    estimated_effort="1 day",
                    test_scenarios=[],
                    metrics_to_track=["documentation_coverage"]
                )
                gaps.append(gap)
        
        return gaps


async def run_self_improvement():
    """Run the self-improvement process"""
    logger.info("🚀 Starting Self-Improvement Analysis")
    
    engine = SelfImprovementEngine()
    
    # Analyze ecosystem
    logger.info("📊 Analyzing ecosystem projects...")
    analyses = await engine.analyze_ecosystem()
    logger.info(f"✅ Analyzed {len(analyses)} projects")
    
    # Discover improvements
    logger.info("🔍 Discovering improvement opportunities...")
    proposals = await engine.discover_improvements()
    logger.info(f"✅ Generated {len(proposals)} improvement proposals")
    
    # Generate task files
    logger.info("📝 Generating improvement tasks...")
    task_files = await engine.generate_improvement_tasks()
    logger.info(f"✅ Created {len(task_files)} task files")
    
    # Print summary
    print("\n" + "="*60)
    print("🎯 Self-Improvement Summary")
    print("="*60)
    
    high_priority = [p for p in proposals if p.priority == "high"]
    print(f"\n🔴 High Priority Improvements ({len(high_priority)}):")
    for p in high_priority[:5]:
        print(f"  - {p.id}: {p.title}")
        print(f"    Affects: {', '.join(p.affected_projects[:3])}")
    
    print(f"\n📁 Task files generated in: docs/tasks/")
    print(f"📋 Review: docs/tasks/IMPROVEMENT_PROPOSALS_SUMMARY.md")
    
    return proposals


if __name__ == "__main__":
    asyncio.run(run_self_improvement())