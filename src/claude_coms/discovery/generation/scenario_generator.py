"""
Scenario Generator - Creates new test scenarios from discovered patterns

Automatically generates integration test scenarios based on research findings.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import random
from textwrap import dedent, indent

from ..research.research_agent import ResearchFinding
from ..analysis.optimization_analyzer import InteractionPattern, OptimizationScore


@dataclass
class ScenarioTemplate:
    """Template for generating scenarios"""
    name: str
    category: str
    base_modules: List[str]
    workflow_type: str  # sequential, parallel, event_driven, hybrid
    complexity: int  # 1-5
    template_code: str


@dataclass 
class GeneratedScenario:
    """A generated test scenario"""
    name: str
    description: str
    category: str
    modules: List[str]
    workflow_steps: List[Dict[str, Any]]
    test_code: str
    optimization_notes: List[str]
    source_patterns: List[str]
    generation_timestamp: datetime = field(default_factory=datetime.now)


class ScenarioGenerator:
    """Generates new test scenarios from patterns and research"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("tests/integration_scenarios/generated")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Available modules in the ecosystem
        self.available_modules = [
            "marker", "sparta", "arangodb", "arxiv", "youtube_transcripts",
            "llm_call", "test_reporter", "unsloth", "chat", "mcp_screenshot",
            "claude_max_proxy", "rl_commons"
        ]
        
        # Scenario templates based on common patterns
        self.templates = self._initialize_templates()
        
        # Module capabilities for intelligent matching
        self.module_capabilities = {
            "marker": ["pdf_extraction", "document_processing", "table_extraction"],
            "sparta": ["security_analysis", "vulnerability_scanning", "compliance"],
            "arangodb": ["graph_storage", "relationship_mapping", "knowledge_base"],
            "arxiv": ["research_papers", "academic_search", "literature_review"],
            "youtube_transcripts": ["video_analysis", "tutorial_extraction", "talks"],
            "llm_call": ["text_generation", "analysis", "summarization", "validation"],
            "test_reporter": ["report_generation", "visualization", "metrics"],
            "unsloth": ["model_training", "fine_tuning", "optimization"],
            "chat": ["user_interaction", "conversation", "feedback"],
            "mcp_screenshot": ["visual_capture", "ui_analysis", "diagram_extraction"],
            "claude_max_proxy": ["multi_model", "llm_orchestration", "validation"],
            "rl_commons": ["optimization", "reward_calculation", "policy_learning"]
        }
        
        self.generated_count = 0
    
    async def generate_from_research(
        self,
        findings: List[ResearchFinding],
        optimization_scores: Optional[List[OptimizationScore]] = None,
        max_scenarios: int = 5
    ) -> List[GeneratedScenario]:
        """
        Generate scenarios from research findings
        
        Args:
            findings: Research findings with patterns
            optimization_scores: Optional optimization analysis results
            max_scenarios: Maximum number of scenarios to generate
            
        Returns:
            List of generated scenarios
        """
        generated_scenarios = []
        
        # Group findings by pattern type
        pattern_groups = self._group_findings_by_pattern(findings)
        
        # Generate scenarios for each pattern group
        for pattern_type, pattern_findings in pattern_groups.items():
            if len(generated_scenarios) >= max_scenarios:
                break
                
            # Select best findings for this pattern
            best_findings = sorted(
                pattern_findings,
                key=lambda f: f.relevance_score,
                reverse=True
            )[:3]
            
            # Generate scenario
            scenario = await self._generate_scenario_from_pattern(
                pattern_type,
                best_findings,
                optimization_scores
            )
            
            if scenario:
                generated_scenarios.append(scenario)
        
        # Generate hybrid scenarios combining patterns
        if len(generated_scenarios) < max_scenarios:
            hybrid_scenarios = await self._generate_hybrid_scenarios(
                findings,
                max_scenarios - len(generated_scenarios)
            )
            generated_scenarios.extend(hybrid_scenarios)
        
        return generated_scenarios
    
    async def generate_from_pattern(
        self,
        pattern: InteractionPattern,
        optimization_score: OptimizationScore
    ) -> GeneratedScenario:
        """Generate a scenario from a specific pattern with optimizations"""
        # Map pattern to appropriate template
        template = self._select_template_for_pattern(pattern)
        
        # Apply optimizations based on score
        optimized_steps = self._apply_optimizations(
            pattern.steps,
            optimization_score.improvements
        )
        
        # Generate test code
        test_code = self._generate_test_code(
            pattern.name,
            pattern.modules,
            optimized_steps,
            template
        )
        
        # Create scenario
        scenario = GeneratedScenario(
            name=f"Test{pattern.name.replace(' ', '')}",
            description=f"Auto-generated test for {pattern.name} with optimizations",
            category=self._determine_category(pattern.modules),
            modules=pattern.modules,
            workflow_steps=optimized_steps,
            test_code=test_code,
            optimization_notes=[imp["description"] for imp in optimization_score.improvements],
            source_patterns=[pattern.name]
        )
        
        return scenario
    
    def _initialize_templates(self) -> Dict[str, ScenarioTemplate]:
        """Initialize scenario templates"""
        templates = {}
        
        # Sequential processing template
        templates["sequential"] = ScenarioTemplate(
            name="Sequential Processing",
            category="general",
            base_modules=["input", "processor", "output"],
            workflow_type="sequential",
            complexity=2,
            template_code=self._get_sequential_template()
        )
        
        # Parallel research template
        templates["parallel_research"] = ScenarioTemplate(
            name="Parallel Research",
            category="research_integration",
            base_modules=["arxiv", "youtube_transcripts", "perplexity"],
            workflow_type="parallel",
            complexity=3,
            template_code=self._get_parallel_research_template()
        )
        
        # ML pipeline template
        templates["ml_pipeline"] = ScenarioTemplate(
            name="ML Pipeline",
            category="ml_workflows",
            base_modules=["data_source", "unsloth", "llm_call", "test_reporter"],
            workflow_type="sequential",
            complexity=4,
            template_code=self._get_ml_pipeline_template()
        )
        
        # Security analysis template
        templates["security_analysis"] = ScenarioTemplate(
            name="Security Analysis",
            category="security",
            base_modules=["marker", "sparta", "llm_call", "arangodb"],
            workflow_type="hybrid",
            complexity=4,
            template_code=self._get_security_template()
        )
        
        # Event-driven template
        templates["event_driven"] = ScenarioTemplate(
            name="Event Driven Processing",
            category="general",
            base_modules=["event_source", "processor", "event_sink"],
            workflow_type="event_driven",
            complexity=3,
            template_code=self._get_event_driven_template()
        )
        
        return templates
    
    def _group_findings_by_pattern(
        self,
        findings: List[ResearchFinding]
    ) -> Dict[str, List[ResearchFinding]]:
        """Group findings by discovered patterns"""
        pattern_groups = {}
        
        for finding in findings:
            for pattern in finding.patterns_found:
                if pattern not in pattern_groups:
                    pattern_groups[pattern] = []
                pattern_groups[pattern].append(finding)
        
        return pattern_groups
    
    async def _generate_scenario_from_pattern(
        self,
        pattern_type: str,
        findings: List[ResearchFinding],
        optimization_scores: Optional[List[OptimizationScore]]
    ) -> Optional[GeneratedScenario]:
        """Generate a scenario from a pattern type and findings"""
        # Map pattern to modules
        modules = self._map_pattern_to_modules(pattern_type, findings)
        if len(modules) < 2:
            return None
        
        # Determine workflow type
        workflow_type = self._determine_workflow_type(pattern_type)
        
        # Create workflow steps
        workflow_steps = self._create_workflow_steps(modules, pattern_type, findings)
        
        # Generate name and description
        name = self._generate_scenario_name(pattern_type, modules)
        description = self._generate_scenario_description(pattern_type, findings)
        
        # Select appropriate template
        template = self._select_template_for_pattern_type(pattern_type, workflow_type)
        
        # Generate test code
        test_code = self._generate_test_code(name, modules, workflow_steps, template)
        
        # Extract optimization notes
        optimization_notes = []
        if optimization_scores:
            for score in optimization_scores:
                if pattern_type in str(score.pattern_name).lower():
                    optimization_notes.extend([imp["description"] for imp in score.improvements[:2]])
        
        return GeneratedScenario(
            name=name,
            description=description,
            category=self._determine_category(modules),
            modules=modules,
            workflow_steps=workflow_steps,
            test_code=test_code,
            optimization_notes=optimization_notes,
            source_patterns=[pattern_type] + [f.title[:30] for f in findings[:2]]
        )
    
    async def _generate_hybrid_scenarios(
        self,
        findings: List[ResearchFinding],
        count: int
    ) -> List[GeneratedScenario]:
        """Generate hybrid scenarios combining multiple patterns"""
        hybrid_scenarios = []
        
        # Find complementary patterns
        pattern_combinations = [
            ("cache", "parallel"),
            ("circuit_breaker", "retry"),
            ("event_driven", "stream"),
            ("batch", "async_processing")
        ]
        
        for combo in pattern_combinations[:count]:
            if len(hybrid_scenarios) >= count:
                break
                
            # Find findings with both patterns
            relevant_findings = [
                f for f in findings
                if any(p in f.patterns_found for p in combo)
            ]
            
            if relevant_findings:
                scenario = await self._generate_hybrid_scenario(combo, relevant_findings)
                if scenario:
                    hybrid_scenarios.append(scenario)
        
        return hybrid_scenarios
    
    async def _generate_hybrid_scenario(
        self,
        pattern_combo: Tuple[str, str],
        findings: List[ResearchFinding]
    ) -> Optional[GeneratedScenario]:
        """Generate a hybrid scenario from pattern combination"""
        # Select diverse modules
        modules = self._select_diverse_modules(4, findings)
        
        # Create hybrid workflow
        workflow_steps = []
        
        # Add caching step if in combo
        if "cache" in pattern_combo:
            workflow_steps.append({
                "to_module": "arangodb",
                "content": {"task": "check_cache", "key": "scenario_data"},
                "metadata": {"pattern": "cache", "conditional": True}
            })
        
        # Add parallel steps
        if "parallel" in pattern_combo:
            parallel_modules = modules[:3] if len(modules) >= 3 else modules
            for mod in parallel_modules:
                workflow_steps.append({
                    "to_module": mod,
                    "content": {"task": f"process_{mod}", "parallel": True},
                    "metadata": {"pattern": "parallel", "group": 1}
                })
        
        # Add resilience patterns
        if "circuit_breaker" in pattern_combo or "retry" in pattern_combo:
            workflow_steps.append({
                "to_module": "llm_call",
                "content": {
                    "task": "analyze_with_resilience",
                    "retry_policy": {"max_attempts": 3, "backoff": "exponential"},
                    "circuit_breaker": {"threshold": 5, "timeout": 30}
                },
                "metadata": {"pattern": "resilience"}
            })
        
        # Generate final aggregation step
        workflow_steps.append({
            "to_module": "test_reporter",
            "content": {"task": "aggregate_results", "format": "comprehensive"},
            "metadata": {"pattern": "aggregation"}
        })
        
        name = f"TestHybrid{''.join(p.title() for p in pattern_combo)}"
        description = f"Hybrid scenario combining {' and '.join(pattern_combo)} patterns"
        
        test_code = self._generate_test_code(
            name,
            modules,
            workflow_steps,
            self.templates.get("sequential")  # Use sequential as base
        )
        
        return GeneratedScenario(
            name=name,
            description=description,
            category="integration",
            modules=modules,
            workflow_steps=workflow_steps,
            test_code=test_code,
            optimization_notes=[
                f"Implements {pattern_combo[0]} for performance",
                f"Uses {pattern_combo[1]} for reliability"
            ],
            source_patterns=list(pattern_combo)
        )
    
    def _map_pattern_to_modules(
        self,
        pattern_type: str,
        findings: List[ResearchFinding]
    ) -> List[str]:
        """Map a pattern type to appropriate modules"""
        # Pattern to module mapping
        pattern_modules = {
            "pipeline": ["marker", "sparta", "llm_call", "test_reporter"],
            "parallel": ["arxiv", "youtube_transcripts", "llm_call"],
            "event_driven": ["mcp_screenshot", "llm_call", "arangodb"],
            "circuit_breaker": ["claude_max_proxy", "llm_call", "test_reporter"],
            "cache": ["arangodb", "llm_call", "marker"],
            "batch": ["marker", "unsloth", "test_reporter"],
            "stream": ["youtube_transcripts", "llm_call", "arangodb"],
            "ml_pipeline": ["marker", "unsloth", "llm_call", "test_reporter"],
            "security": ["sparta", "marker", "llm_call", "arangodb"]
        }
        
        # Get base modules for pattern
        base_modules = pattern_modules.get(pattern_type, ["llm_call", "test_reporter"])
        
        # Add modules mentioned in findings
        for finding in findings[:2]:  # Look at top 2 findings
            content_lower = finding.content.lower()
            for module in self.available_modules:
                if module in content_lower and module not in base_modules:
                    base_modules.append(module)
        
        return base_modules[:5]  # Limit to 5 modules
    
    def _determine_workflow_type(self, pattern_type: str) -> str:
        """Determine workflow type from pattern"""
        if "parallel" in pattern_type:
            return "parallel"
        elif "event" in pattern_type or "stream" in pattern_type:
            return "event_driven"
        elif "pipeline" in pattern_type:
            return "sequential"
        else:
            return "hybrid"
    
    def _create_workflow_steps(
        self,
        modules: List[str],
        pattern_type: str,
        findings: List[ResearchFinding]
    ) -> List[Dict[str, Any]]:
        """Create workflow steps based on modules and pattern"""
        steps = []
        
        # Extract tasks from findings
        tasks = self._extract_tasks_from_findings(findings)
        
        if self._determine_workflow_type(pattern_type) == "parallel":
            # Create parallel steps
            for i, module in enumerate(modules[:-1]):  # Last module for aggregation
                steps.append({
                    "from_module": "coordinator",
                    "to_module": module,
                    "content": {
                        "task": tasks[i] if i < len(tasks) else f"analyze_{pattern_type}",
                        "parallel_group": 1
                    },
                    "metadata": {"step": i + 1, "pattern": pattern_type}
                })
            
            # Aggregation step
            steps.append({
                "from_module": modules[0],
                "to_module": modules[-1],
                "content": {"task": "aggregate_results"},
                "metadata": {"step": len(modules), "pattern": "aggregation"}
            })
        else:
            # Sequential steps
            for i, module in enumerate(modules):
                from_module = "coordinator" if i == 0 else modules[i-1]
                steps.append({
                    "from_module": from_module,
                    "to_module": module,
                    "content": {
                        "task": tasks[i] if i < len(tasks) else f"process_{pattern_type}"
                    },
                    "metadata": {"step": i + 1, "pattern": pattern_type}
                })
        
        return steps
    
    def _extract_tasks_from_findings(self, findings: List[ResearchFinding]) -> List[str]:
        """Extract task names from research findings"""
        tasks = []
        
        # Common task patterns in research
        task_keywords = {
            "extract": "extract_data",
            "analyze": "analyze_content",
            "search": "search_information",
            "validate": "validate_results",
            "generate": "generate_output",
            "train": "train_model",
            "optimize": "optimize_performance",
            "store": "store_results"
        }
        
        for finding in findings[:5]:
            content_lower = finding.content.lower()
            for keyword, task in task_keywords.items():
                if keyword in content_lower:
                    tasks.append(task)
                    break
        
        return tasks
    
    def _generate_scenario_name(self, pattern_type: str, modules: List[str]) -> str:
        """Generate a descriptive scenario name"""
        # Clean pattern type
        pattern_words = pattern_type.replace("_", " ").title().replace(" ", "")
        
        # Get primary module
        primary_module = modules[0].title() if modules else "Generic"
        
        # Generate unique suffix
        self.generated_count += 1
        
        return f"Test{pattern_words}{primary_module}V{self.generated_count}"
    
    def _generate_scenario_description(
        self,
        pattern_type: str,
        findings: List[ResearchFinding]
    ) -> str:
        """Generate scenario description from findings"""
        # Get key insights from findings
        insights = []
        for finding in findings[:2]:
            if finding.source == "arxiv":
                insights.append(f"Based on research: {finding.title[:50]}")
            elif finding.source == "youtube":
                insights.append(f"Inspired by: {finding.title[:50]}")
        
        description = f"Tests {pattern_type.replace('_', ' ')} pattern. "
        if insights:
            description += " ".join(insights)
        
        return description
    
    def _select_template_for_pattern_type(
        self,
        pattern_type: str,
        workflow_type: str
    ) -> ScenarioTemplate:
        """Select appropriate template for pattern"""
        # Try to find specific template
        if pattern_type in ["ml_pipeline", "security"]:
            return self.templates.get(pattern_type, self.templates["sequential"])
        
        # Map workflow type to template
        if workflow_type == "parallel":
            return self.templates["parallel_research"]
        elif workflow_type == "event_driven":
            return self.templates["event_driven"]
        else:
            return self.templates["sequential"]
    
    def _select_template_for_pattern(self, pattern: InteractionPattern) -> ScenarioTemplate:
        """Select template for an interaction pattern"""
        # Check for specific patterns
        if any(m in ["unsloth", "llm_call"] for m in pattern.modules):
            return self.templates["ml_pipeline"]
        elif "sparta" in pattern.modules:
            return self.templates["security_analysis"]
        elif pattern.flow_type == "parallel":
            return self.templates["parallel_research"]
        elif pattern.flow_type == "event_driven":
            return self.templates["event_driven"]
        else:
            return self.templates["sequential"]
    
    def _apply_optimizations(
        self,
        steps: List[Dict[str, Any]],
        improvements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply optimization improvements to workflow steps"""
        optimized_steps = steps.copy()
        
        for improvement in improvements:
            if improvement["type"] == "parallelization":
                # Mark independent steps for parallel execution
                optimized_steps = self._parallelize_steps(optimized_steps)
            elif improvement["type"] == "caching":
                # Add cache check step
                cache_step = {
                    "to_module": "arangodb",
                    "content": {"task": "check_cache", "ttl": 3600},
                    "metadata": {"optimization": "cache", "step": 0}
                }
                optimized_steps.insert(0, cache_step)
            elif improvement["type"] == "batching":
                # Modify steps to support batching
                for step in optimized_steps:
                    if "content" in step:
                        step["content"]["batch_size"] = 10
        
        return optimized_steps
    
    def _parallelize_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert sequential steps to parallel where possible"""
        # Simple heuristic: steps with no data dependencies can be parallel
        parallel_steps = []
        
        for i, step in enumerate(steps):
            step_copy = step.copy()
            # Mark middle steps as parallel (keep first and last sequential)
            if 0 < i < len(steps) - 1:
                step_copy["metadata"] = step_copy.get("metadata", {})
                step_copy["metadata"]["parallel_group"] = 1
            parallel_steps.append(step_copy)
        
        return parallel_steps
    
    def _determine_category(self, modules: List[str]) -> str:
        """Determine test category from modules"""
        if any(m in ["sparta", "cwe"] for m in modules):
            return "security"
        elif any(m in ["marker", "pdf"] for m in modules):
            return "document_processing"
        elif any(m in ["arxiv", "youtube_transcripts"] for m in modules):
            return "research_integration"
        elif any(m in ["unsloth", "llm_call", "claude_max_proxy"] for m in modules):
            return "ml_workflows"
        elif "arangodb" in modules:
            return "knowledge_management"
        else:
            return "general"
    
    def _select_diverse_modules(self, count: int, findings: List[ResearchFinding]) -> List[str]:
        """Select diverse modules based on findings"""
        selected = []
        categories_used = set()
        
        # Try to get one module from each category
        for module in self.available_modules:
            if len(selected) >= count:
                break
                
            # Get module category
            capabilities = self.module_capabilities.get(module, [])
            if capabilities:
                category = capabilities[0].split("_")[0]
                if category not in categories_used:
                    selected.append(module)
                    categories_used.add(category)
        
        # Fill remaining with random modules
        remaining = [m for m in self.available_modules if m not in selected]
        while len(selected) < count and remaining:
            module = random.choice(remaining)
            selected.append(module)
            remaining.remove(module)
        
        return selected
    
    def _generate_test_code(
        self,
        name: str,
        modules: List[str],
        steps: List[Dict[str, Any]],
        template: ScenarioTemplate
    ) -> str:
        """Generate complete test code"""
        # Base imports
        imports = dedent("""
        import pytest
        from tests.integration_scenarios.base.scenario_test_base import ScenarioTestBase, TestMessage
        from tests.integration_scenarios.base.result_assertions import ScenarioAssertions
        """).strip()
        
        # Class definition
        class_def = f"""
class {name}(ScenarioTestBase):
    \"\"\"Auto-generated test scenario
    
    Pattern: {template.name}
    Modules: {', '.join(modules)}
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    \"\"\"
    
    def register_modules(self):
        \"\"\"Register modules for this scenario\"\"\"
        return {{}}  # Modules provided by fixtures
    """
        
        # Workflow definition
        workflow_def = self._generate_workflow_method(steps)
        
        # Assertions
        assertions = self._generate_assertions_method(len(steps), modules)
        
        # Test methods
        test_methods = self._generate_test_methods(name, modules, template.category)
        
        # Combine all parts
        full_code = f"{imports}\n\n\n{class_def}\n{workflow_def}\n{assertions}\n{test_methods}"
        
        return full_code
    
    def _generate_workflow_method(self, steps: List[Dict[str, Any]]) -> str:
        """Generate create_test_workflow method"""
        method_start = """
    def create_test_workflow(self):
        \"\"\"Define the test workflow\"\"\"
        return ["""
        
        step_strings = []
        for step in steps:
            step_str = """
            TestMessage(
                from_module="{from_module}",
                to_module="{to_module}",
                content={content},
                metadata={metadata}
            )""".format(
                from_module=step.get("from_module", "coordinator"),
                to_module=step["to_module"],
                content=json.dumps(step.get("content", {}), indent=20).replace("\n", "\n                "),
                metadata=json.dumps(step.get("metadata", {}), indent=20).replace("\n", "\n                ")
            )
            step_strings.append(step_str)
        
        method_end = """
        ]"""
        
        return method_start + ",".join(step_strings) + method_end
    
    def _generate_assertions_method(self, num_steps: int, modules: List[str]) -> str:
        """Generate assert_results method"""
        return f"""
    def assert_results(self, results):
        \"\"\"Assert expected outcomes\"\"\"
        # Verify workflow completion
        ScenarioAssertions.assert_workflow_completed(results, {num_steps})
        
        # Verify no errors
        ScenarioAssertions.assert_no_errors(results)
        
        # Verify modules were called
        {self._generate_module_assertions(modules)}
        
        # TODO: Add pattern-specific assertions"""
    
    def _generate_module_assertions(self, modules: List[str]) -> str:
        """Generate module call assertions"""
        assertions = []
        for module in modules[:3]:  # First 3 modules
            assertions.append(
                f'ScenarioAssertions.assert_module_called(results, "{module}")'
            )
        return "\n        ".join(assertions)
    
    def _generate_test_methods(self, name: str, modules: List[str], category: str) -> str:
        """Generate test methods"""
        return f"""
    @pytest.mark.integration
    @pytest.mark.{category}
    @pytest.mark.generated
    async def test_successful_execution(self, mock_modules, workflow_runner):
        \"\"\"Test successful scenario execution\"\"\"
        # Setup mock responses
        {self._generate_mock_setup(modules)}
        
        # Configure runner
        workflow_runner.module_registry = mock_modules.mocks
        
        # Execute scenario
        result = await self.run_scenario()
        
        # Verify success
        assert result["success"] is True
        self.assert_results(result["results"])
    
    @pytest.mark.integration
    @pytest.mark.{category}
    @pytest.mark.generated
    async def test_with_optimization(self, mock_modules, workflow_runner):
        \"\"\"Test scenario with performance optimizations\"\"\"
        # TODO: Implement optimization test
        pass"""
    
    def _generate_mock_setup(self, modules: List[str]) -> str:
        """Generate mock setup code"""
        setups = []
        
        # Generate mock setup for each module
        for module in modules[:3]:
            if module == "marker":
                setup = """mock_modules.get_mock("marker").set_response(
            "extract_data", {"content": "extracted", "status": "success"}
        )"""
            elif module == "llm_call":
                setup = """mock_modules.get_mock("llm_call").set_response(
            "analyze_content", {"analysis": "complete", "score": 0.85}
        )"""
            elif module == "arangodb":
                setup = """mock_modules.get_mock("arangodb").set_response(
            "store_results", {"id": "doc_123", "stored": True}
        )"""
            else:
                setup = f"""mock_modules.get_mock("{module}").set_response(
            "process", {{"status": "success", "data": "processed"}}
        )"""
            setups.append(setup)
        
        return "\n        ".join(setups)
    
    def save_scenario(self, scenario: GeneratedScenario) -> Path:
        """Save generated scenario to file"""
        # Determine file path
        category_dir = self.output_dir / scenario.category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"test_{scenario.name.lower()}.py"
        filepath = category_dir / filename
        
        # Add header to code
        header = f'''"""
{scenario.description}

Generated from patterns: {', '.join(scenario.source_patterns[:3])}
Optimizations applied: {', '.join(scenario.optimization_notes[:2]) if scenario.optimization_notes else 'None'}

THIS IS AN AUTO-GENERATED FILE - Modifications may be overwritten
"""

'''
        
        # Write file
        with open(filepath, 'w') as f:
            f.write(header + scenario.test_code)
        
        # Also save metadata
        metadata_file = category_dir / f"{filepath.stem}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                "name": scenario.name,
                "description": scenario.description,
                "category": scenario.category,
                "modules": scenario.modules,
                "workflow_steps": scenario.workflow_steps,
                "optimization_notes": scenario.optimization_notes,
                "source_patterns": scenario.source_patterns,
                "generated_at": scenario.generation_timestamp.isoformat(),
                "file_path": str(filepath)
            }, f, indent=2)
        
        return filepath
    
    # Template methods
    def _get_sequential_template(self) -> str:
        return "sequential_template"
    
    def _get_parallel_research_template(self) -> str:
        return "parallel_research_template"
    
    def _get_ml_pipeline_template(self) -> str:
        return "ml_pipeline_template"
    
    def _get_security_template(self) -> str:
        return "security_template"
    
    def _get_event_driven_template(self) -> str:
        return "event_driven_template"


if __name__ == "__main__":
    # Test the generator
    from ..research.research_agent import ResearchFinding
    
    async def test_generator():
        generator = ScenarioGenerator()
        
        # Create test findings
        findings = [
            ResearchFinding(
                source="arxiv",
                title="Optimizing Microservices with Caching",
                content="We show that intelligent caching reduces latency by 60%...",
                relevance_score=0.9,
                patterns_found=["cache", "microservice_communication"]
            ),
            ResearchFinding(
                source="youtube",
                title="Parallel Processing in Modern Systems",
                content="This talk covers parallel processing patterns...",
                relevance_score=0.85,
                patterns_found=["parallel", "performance_optimization"]
            )
        ]
        
        # Generate scenarios
        scenarios = await generator.generate_from_research(findings, max_scenarios=2)
        
        print(f"Generated {len(scenarios)} scenarios:")
        for scenario in scenarios:
            print(f"\n{scenario.name}:")
            print(f"  Description: {scenario.description}")
            print(f"  Modules: {', '.join(scenario.modules)}")
            print(f"  Steps: {len(scenario.workflow_steps)}")
            
            # Save scenario
            filepath = generator.save_scenario(scenario)
            print(f"  Saved to: {filepath}")
    
    asyncio.run(test_generator())