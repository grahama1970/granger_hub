"""
Hub-specific prompts for Claude Module Communicator.

This module contains prompts tailored for the module communication hub,
including module orchestration, communication patterns, and integration tasks.
"""

from .prompts import Prompt, get_prompt_registry
from typing import List


def register_hub_prompts():
    """Register all hub-specific prompts with the global registry."""
    registry = get_prompt_registry()
    
    # Module Orchestration Prompts
    registry.register(Prompt(
        name="orchestrate_modules",
        description="Orchestrate communication between multiple modules",
        template="""You are orchestrating communication between modules in the Claude Module Communicator system.

Task: {{ task_description }}

Available Modules:
{% for module in modules %}
- {{ module.name }}: {{ module.description }}
  Capabilities: {{ module.capabilities | join(', ') }}
{% endfor %}

Requirements:
{{ requirements }}

Please analyze the task and determine:
1. Which modules need to be involved
2. The sequence of module interactions
3. The data flow between modules
4. Any potential integration challenges

Provide a detailed orchestration plan.""",
        category="orchestration",
        tags=["modules", "communication", "planning"],
        parameters={
            "task_description": {
                "type": "string",
                "description": "Description of the task to orchestrate"
            },
            "modules": {
                "type": "array",
                "description": "List of available modules with their metadata"
            },
            "requirements": {
                "type": "string",
                "description": "Specific requirements or constraints"
            }
        },
        required_params=["task_description", "modules"],
        examples=[
            """Example: Orchestrate a data processing pipeline that involves:
1. PDF extraction (Marker module)
2. Data transformation (Transform module)
3. Storage in ArangoDB (Database module)"""
        ]
    ))
    
    registry.register(Prompt(
        name="analyze_module_compatibility",
        description="Analyze compatibility between two modules",
        template="""Analyze the compatibility between two modules for integration.

Source Module:
- Name: {{ source.name }}
- Input Schema: {{ source.input_schema | tojson }}
- Output Schema: {{ source.output_schema | tojson }}
- Protocol: {{ source.protocol }}

Target Module:
- Name: {{ target.name }}
- Input Schema: {{ target.input_schema | tojson }}
- Output Schema: {{ target.output_schema | tojson }}
- Protocol: {{ target.protocol }}

Integration Goal: {{ integration_goal }}

Please analyze:
1. Schema compatibility (can output of source feed into target?)
2. Protocol compatibility (do they speak the same language?)
3. Data transformation requirements
4. Potential bottlenecks or issues
5. Recommended adapters or middleware

Provide a compatibility report with recommendations.""",
        category="analysis",
        tags=["compatibility", "integration", "modules"],
        parameters={
            "source": {
                "type": "object",
                "description": "Source module metadata"
            },
            "target": {
                "type": "object",
                "description": "Target module metadata"
            },
            "integration_goal": {
                "type": "string",
                "description": "What the integration should achieve"
            }
        },
        required_params=["source", "target", "integration_goal"]
    ))
    
    # Communication Pattern Prompts
    registry.register(Prompt(
        name="design_communication_pattern",
        description="Design a communication pattern for a specific use case",
        template="""Design an optimal communication pattern for the following scenario:

Use Case: {{ use_case }}

Participants:
{% for participant in participants %}
- {{ participant.name }} ({{ participant.type }}): {{ participant.role }}
{% endfor %}

Requirements:
- Throughput: {{ requirements.throughput }}
- Latency: {{ requirements.latency }}
- Reliability: {{ requirements.reliability }}
- Scalability: {{ requirements.scalability }}

Constraints:
{{ constraints }}

Consider the following patterns:
1. Request-Response
2. Publish-Subscribe
3. Message Queue
4. Event Streaming
5. Hybrid approaches

Recommend the best pattern with justification and implementation details.""",
        category="patterns",
        tags=["communication", "architecture", "design"],
        parameters={
            "use_case": {
                "type": "string",
                "description": "Description of the use case"
            },
            "participants": {
                "type": "array",
                "description": "List of participating modules/services"
            },
            "requirements": {
                "type": "object",
                "description": "Performance and reliability requirements"
            },
            "constraints": {
                "type": "string",
                "description": "Any constraints or limitations"
            }
        },
        required_params=["use_case", "participants", "requirements"]
    ))
    
    # Integration Task Prompts
    registry.register(Prompt(
        name="generate_integration_code",
        description="Generate code to integrate two modules",
        template="""Generate Python code to integrate two modules.

Source Module: {{ source_module }}
Target Module: {{ target_module }}
Integration Type: {{ integration_type }}

Source Output Format:
```python
{{ source_output_example }}
```

Target Input Format:
```python
{{ target_input_example }}
```

Additional Requirements:
{{ requirements }}

Generate:
1. Data transformation function
2. Error handling
3. Async/await if needed
4. Type hints
5. Docstrings
6. Basic tests

The code should be production-ready and follow best practices.""",
        category="integration",
        tags=["code-generation", "integration", "modules"],
        parameters={
            "source_module": {
                "type": "string",
                "description": "Name of the source module"
            },
            "target_module": {
                "type": "string",
                "description": "Name of the target module"
            },
            "integration_type": {
                "type": "string",
                "description": "Type of integration (direct, queued, event-based)"
            },
            "source_output_example": {
                "type": "string",
                "description": "Example of source module output"
            },
            "target_input_example": {
                "type": "string",
                "description": "Example of target module input"
            },
            "requirements": {
                "type": "string",
                "description": "Additional requirements"
            }
        },
        required_params=["source_module", "target_module", "integration_type"]
    ))
    
    # Troubleshooting Prompts
    registry.register(Prompt(
        name="debug_module_communication",
        description="Debug communication issues between modules",
        template="""Help debug a communication issue between modules.

Error Description: {{ error_description }}

Module A:
- Name: {{ module_a.name }}
- Status: {{ module_a.status }}
- Last Message: {{ module_a.last_message }}
- Error Log: {{ module_a.error_log }}

Module B:
- Name: {{ module_b.name }}
- Status: {{ module_b.status }}
- Last Message: {{ module_b.last_message }}
- Error Log: {{ module_b.error_log }}

Communication Log:
{{ communication_log }}

System State:
- Active Modules: {{ system_state.active_modules }}
- Message Queue Size: {{ system_state.queue_size }}
- Failed Messages: {{ system_state.failed_messages }}

Please:
1. Identify the root cause
2. Suggest immediate fixes
3. Recommend preventive measures
4. Provide debugging commands/code

Focus on practical solutions.""",
        category="troubleshooting",
        tags=["debugging", "communication", "errors"],
        parameters={
            "error_description": {
                "type": "string",
                "description": "Description of the error"
            },
            "module_a": {
                "type": "object",
                "description": "First module information"
            },
            "module_b": {
                "type": "object",
                "description": "Second module information"
            },
            "communication_log": {
                "type": "string",
                "description": "Recent communication log entries"
            },
            "system_state": {
                "type": "object",
                "description": "Current system state"
            }
        },
        required_params=["error_description", "module_a", "module_b"]
    ))
    
    # Optimization Prompts
    registry.register(Prompt(
        name="optimize_module_pipeline",
        description="Optimize a module processing pipeline",
        template="""Optimize the following module processing pipeline for better performance.

Current Pipeline:
{% for step in pipeline_steps %}
{{ loop.index }}. {{ step.module }} ({{ step.duration_ms }}ms)
   - Input: {{ step.input_size }}
   - Output: {{ step.output_size }}
   - CPU: {{ step.cpu_usage }}%
   - Memory: {{ step.memory_mb }}MB
{% endfor %}

Total Duration: {{ total_duration_ms }}ms
Bottlenecks: {{ bottlenecks | join(', ') }}

Goals:
- Target Latency: {{ target_latency_ms }}ms
- Max Memory: {{ max_memory_mb }}MB
- Throughput: {{ target_throughput }} items/sec

Available Optimizations:
- Parallel processing
- Caching
- Batch operations
- Module fusion
- Data compression
- Load balancing

Provide specific optimization recommendations with expected improvements.""",
        category="optimization",
        tags=["performance", "pipeline", "optimization"],
        parameters={
            "pipeline_steps": {
                "type": "array",
                "description": "List of pipeline steps with metrics"
            },
            "total_duration_ms": {
                "type": "number",
                "description": "Total pipeline duration in milliseconds"
            },
            "bottlenecks": {
                "type": "array",
                "description": "Identified bottlenecks"
            },
            "target_latency_ms": {
                "type": "number",
                "description": "Target latency in milliseconds"
            },
            "max_memory_mb": {
                "type": "number",
                "description": "Maximum memory in megabytes"
            },
            "target_throughput": {
                "type": "number",
                "description": "Target throughput"
            }
        },
        required_params=["pipeline_steps", "total_duration_ms", "target_latency_ms"]
    ))
    
    # Module Discovery Prompts
    registry.register(Prompt(
        name="discover_module_capabilities",
        description="Discover and document module capabilities",
        template="""Analyze the following module to discover its full capabilities.

Module Information:
- Name: {{ module_name }}
- Type: {{ module_type }}
- Version: {{ module_version }}

Available Methods:
{% for method in methods %}
- {{ method.name }}({{ method.params | join(', ') }}): {{ method.description }}
{% endfor %}

Sample Interactions:
{{ sample_interactions }}

Documentation Snippets:
{{ documentation }}

Please provide:
1. Complete capability matrix
2. Input/output specifications
3. Performance characteristics
4. Integration points
5. Best practices for usage
6. Potential use cases

Format as structured documentation.""",
        category="discovery",
        tags=["modules", "capabilities", "documentation"],
        parameters={
            "module_name": {
                "type": "string",
                "description": "Name of the module"
            },
            "module_type": {
                "type": "string",
                "description": "Type of module (MCP, REST, CLI, etc.)"
            },
            "module_version": {
                "type": "string",
                "description": "Module version"
            },
            "methods": {
                "type": "array",
                "description": "List of available methods"
            },
            "sample_interactions": {
                "type": "string",
                "description": "Examples of module interactions"
            },
            "documentation": {
                "type": "string",
                "description": "Available documentation"
            }
        },
        required_params=["module_name", "module_type", "methods"]
    ))
    
    # Scenario Generation Prompts
    registry.register(Prompt(
        name="generate_integration_scenario",
        description="Generate integration test scenarios",
        template="""Generate comprehensive integration test scenarios for the module ecosystem.

Modules Available:
{% for module in modules %}
- {{ module }}: {{ module_descriptions[module] }}
{% endfor %}

Focus Area: {{ focus_area }}
Complexity Level: {{ complexity_level }}

Generate {{ num_scenarios }} test scenarios that:
1. Test real-world use cases
2. Cover edge cases
3. Validate error handling
4. Check performance under load
5. Verify data integrity

Each scenario should include:
- Name and description
- Participating modules
- Test steps
- Expected outcomes
- Success criteria
- Potential failure points

Format as executable test cases.""",
        category="testing",
        tags=["scenarios", "testing", "integration"],
        parameters={
            "modules": {
                "type": "array",
                "description": "List of available modules"
            },
            "module_descriptions": {
                "type": "object",
                "description": "Module descriptions"
            },
            "focus_area": {
                "type": "string",
                "description": "Area to focus on (security, performance, reliability)"
            },
            "complexity_level": {
                "type": "string",
                "description": "Complexity level (simple, moderate, complex)"
            },
            "num_scenarios": {
                "type": "integer",
                "description": "Number of scenarios to generate"
            }
        },
        required_params=["modules", "focus_area", "num_scenarios"]
    ))


def get_hub_prompt_examples() -> List[dict]:
    """Get example usage for hub prompts."""
    return [
        {
            "prompt": "orchestrate_modules",
            "example": {
                "task_description": "Process PDF documents and store extracted data",
                "modules": [
                    {
                        "name": "marker",
                        "description": "PDF to Markdown converter",
                        "capabilities": ["pdf_extraction", "table_detection"]
                    },
                    {
                        "name": "arangodb",
                        "description": "Graph database",
                        "capabilities": ["store", "query", "graph_traversal"]
                    }
                ],
                "requirements": "Preserve document structure and relationships"
            }
        },
        {
            "prompt": "optimize_module_pipeline",
            "example": {
                "pipeline_steps": [
                    {
                        "module": "pdf_extractor",
                        "duration_ms": 2000,
                        "input_size": "10MB",
                        "output_size": "1MB",
                        "cpu_usage": 80,
                        "memory_mb": 512
                    },
                    {
                        "module": "nlp_processor",
                        "duration_ms": 5000,
                        "input_size": "1MB",
                        "output_size": "500KB",
                        "cpu_usage": 95,
                        "memory_mb": 1024
                    }
                ],
                "total_duration_ms": 7000,
                "bottlenecks": ["nlp_processor"],
                "target_latency_ms": 3000,
                "max_memory_mb": 2048,
                "target_throughput": 10
            }
        }
    ]


# Auto-register prompts when module is imported
register_hub_prompts()


if __name__ == "__main__":
    # Validation with real data
    print(f"Validating {__file__}...")
    
    # Get registry and verify prompts are registered
    registry = get_prompt_registry()
    
    # Expected prompts
    expected_prompts = [
        "orchestrate_modules",
        "analyze_module_compatibility",
        "design_communication_pattern",
        "generate_integration_code",
        "debug_module_communication",
        "optimize_module_pipeline",
        "discover_module_capabilities",
        "generate_integration_scenario"
    ]
    
    # Verify all prompts are registered
    for prompt_name in expected_prompts:
        prompt = registry.get_prompt(prompt_name)
        assert prompt is not None, f"Prompt {prompt_name} not found"
        print(f"✓ {prompt_name}: {prompt.description}")
    
    # Test rendering a prompt
    orchestrate_prompt = registry.get_prompt("orchestrate_modules")
    rendered = orchestrate_prompt.render(
        task_description="Test orchestration",
        modules=[
            {
                "name": "test_module",
                "description": "Test module",
                "capabilities": ["test", "validate"]
            }
        ],
        requirements="Must be fast"
    )
    assert "Test orchestration" in rendered, "Prompt rendering failed"
    
    # Verify categories
    categories = registry.list_categories()
    expected_categories = [
        "orchestration", "analysis", "patterns", "integration",
        "troubleshooting", "optimization", "discovery", "testing"
    ]
    for cat in expected_categories:
        assert cat in categories, f"Category {cat} not found"
    
    print(f"\n📊 Summary:")
    print(f"  - Total prompts: {len(registry.list_prompts())}")
    print(f"  - Categories: {len(categories)}")
    print(f"  - Tags: {len(registry.list_tags())}")
    
    print("\n✅ Validation passed")