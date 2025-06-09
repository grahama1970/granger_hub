# Integration Scenarios Test Framework

## Overview

This framework provides a flexible, extensible system for testing complex multi-module integration scenarios in the Granger Hub ecosystem. It enables testing of real-world workflows where multiple modules interact to accomplish complex tasks.

## Quick Start

### Running Tests

```bash
# Run all integration scenarios
pytest tests/integration_scenarios/

# Run specific category
pytest tests/integration_scenarios/categories/security/

# Run with markers
pytest -m security  # Security scenarios only
pytest -m "integration and not slow"  # Fast integration tests

# Run specific test
pytest tests/integration_scenarios/categories/security/test_satellite_firmware.py::TestSatelliteFirmwareVulnerability::test_successful_workflow

# Generate HTML report
pytest tests/integration_scenarios/ --html=report.html --self-contained-html
```

### Writing a New Test

1. **Choose the appropriate category** under `categories/`:
   - `security/` - Security-focused scenarios
   - `document_processing/` - PDF/document workflows
   - `research_integration/` - ArXiv/YouTube research
   - `ml_workflows/` - ML/AI scenarios
   - `knowledge_management/` - ArangoDB/graph scenarios

2. **Create your test class**:

```python
from tests.integration_scenarios.base.scenario_test_base import ScenarioTestBase, TestMessage
from tests.integration_scenarios.base.result_assertions import ScenarioAssertions

class TestYourScenario(ScenarioTestBase):
    """Test description"""
    
    def register_modules(self):
        """Modules are provided by fixtures"""
        return {}
    
    def create_test_workflow(self):
        """Define your workflow steps"""
        return [
            TestMessage(
                from_module="coordinator",
                to_module="module_name",
                content={"task": "task_name", "param": "value"},
                metadata={"step": 1, "description": "What this step does"}
            ),
            # Add more steps...
        ]
    
    def assert_results(self, results):
        """Assert expected outcomes"""
        ScenarioAssertions.assert_workflow_completed(results, expected_steps)
        # Add your assertions
```

3. **Add test methods**:

```python
@pytest.mark.integration
@pytest.mark.your_category
async def test_successful_case(self, mock_modules, workflow_runner):
    """Test successful execution"""
    # Setup mocks
    mock_modules.get_mock("module_name").set_response(
        "task_name",
        {"result": "success", "data": "value"}
    )
    
    # Configure runner
    workflow_runner.module_registry = mock_modules.mocks
    
    # Run scenario
    result = await self.run_scenario()
    
    # Assert success
    assert result["success"] is True
    self.assert_results(result["results"])
```

## Framework Structure

### Base Classes

- **`ScenarioTestBase`** - Base class for all scenario tests
  - Provides workflow execution
  - Performance tracking
  - Error handling
  - Result collection

- **`TestMessage`** - Message definition for workflows
  - Validated structure
  - Metadata support
  - Type safety

### Utilities

- **`ModuleMock`** - Flexible module mocking
  - Canned responses
  - Dynamic handlers
  - Error simulation
  - Delay simulation
  - Call tracking

- **`ScenarioAssertions`** - Common assertions
  - Workflow completion
  - Module interactions
  - Data flow
  - Performance
  - Error handling

- **`WorkflowRunner`** - Workflow execution engine
  - Sequential execution
  - Timeout handling
  - Performance metrics
  - Hook support

- **`MessageValidator`** - Message validation
  - Schema validation
  - Type checking
  - Custom rules

## Mock Module Features

### Basic Response
```python
mock.set_response("task_name", {"status": "success"})
```

### Dynamic Response
```python
mock.set_dynamic_response("task_name", 
    lambda msg: {"result": msg["param"] * 2}
)
```

### Error Simulation
```python
mock.set_error("task_name", RuntimeError("Service unavailable"))
```

### Sequential Responses
```python
mock.set_sequence("task_name", [
    {"status": "processing"},
    {"status": "complete", "result": "done"}
])
```

### Response with Delays
```python
mock.set_response("task_name", {"status": "ok"}, delay=2.0)
```

### Error Rate Simulation
```python
mock.set_response("task_name", {"status": "ok"}, error_rate=0.1)  # 10% failure
```

## Common Assertions

### Workflow Assertions
```python
# Complete workflow
ScenarioAssertions.assert_workflow_completed(results, 5)

# No errors
ScenarioAssertions.assert_no_errors(results)

# Partial completion
ScenarioAssertions.assert_partial_completion(results, completed=3, total=5)
```

### Module Assertions
```python
# Module called
ScenarioAssertions.assert_module_called(results, "marker", times=1)

# Module sequence
ScenarioAssertions.assert_module_sequence(results, ["marker", "sparta", "arxiv"])
```

### Data Flow Assertions
```python
# Data propagation
ScenarioAssertions.assert_data_flow(results, "document_id", from_step=1, to_step=2)

# Result contains
ScenarioAssertions.assert_result_contains(results, step=0, {"status": "success"})
```

### Performance Assertions
```python
# Total duration
ScenarioAssertions.assert_performance(results, max_total_duration=10.0)

# Step duration
ScenarioAssertions.assert_performance(results, max_step_duration=2.0)
```

### Error Assertions
```python
# Error at step
ScenarioAssertions.assert_error_at_step(results, step=2, error_contains="timeout")
```

## Fixtures

### `mock_modules`
Provides pre-configured mock modules for all projects:
- marker, sparta, arangodb, arxiv, youtube_transcripts
- llm_call, test_reporter, unsloth, chat, mcp_screenshot

### `workflow_runner`
Standard workflow runner with mock modules

### `parallel_runner`
Parallel execution capability

### `message_validator`
Message validation with common schemas

### `sample_responses`
Pre-defined response templates

### `performance_monitor`
Performance measurement utilities

## Best Practices

1. **Test Organization**
   - One scenario per test class
   - Group related tests in categories
   - Use descriptive test names

2. **Mock Setup**
   - Setup mocks before running scenario
   - Use realistic response data
   - Test both success and failure paths

3. **Assertions**
   - Use provided assertion utilities
   - Check workflow completion first
   - Verify data flow between steps
   - Include performance checks

4. **Error Testing**
   - Test module failures
   - Test timeout scenarios
   - Test partial completions
   - Verify error propagation

5. **Performance**
   - Set reasonable timeouts
   - Test with delays
   - Monitor resource usage
   - Use performance fixtures

## Advanced Features

### Parallel Execution
```python
async def test_parallel_workflow(self, parallel_runner):
    """Test with parallel step execution"""
    result = await parallel_runner.execute_workflow(
        workflow,
        parallel_groups=[[0, 1], [2, 3, 4]]  # Steps that can run in parallel
    )
```

### Custom Hooks
```python
workflow_runner.add_hook("pre_step", lambda step, message: 
    print(f"Starting step {step}")
)
```

### Context Sharing
```python
# Modules can share context between steps
workflow_runner.context["shared_data"] = "value"
```

### Performance Tracking
```python
metrics = workflow_runner.get_metrics()
print(f"Total duration: {metrics.total_duration}s")
print(f"Average step: {metrics.to_dict()['average_step_duration']}s")
```

## Debugging

### Print Workflow Summary
```python
result = await self.run_scenario()
self.print_workflow_summary()  # Detailed execution trace
```

### Get Call History
```python
mock_modules.print_call_summary()  # All module calls
mock.get_call_history("task_name")  # Specific task calls
```

### Execution Trace
```python
trace = workflow_runner.get_execution_trace()
print(json.dumps(trace, indent=2))
```

## Migration from Old Scenarios

1. Copy scenario logic to new test class
2. Convert to TestMessage format
3. Add proper assertions
4. Setup module mocks
5. Add appropriate markers
6. Test both success and failure cases

## Contributing

1. Follow the existing patterns
2. Add comprehensive docstrings
3. Include both positive and negative test cases
4. Update this README if adding new features
5. Ensure all tests pass before submitting