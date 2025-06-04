# Integration Scenario Test Framework Design

## Overview

This document outlines a flexible, extensible test framework for integration scenarios in the Claude Module Communicator ecosystem. The framework enables testing of complex multi-module interactions while maintaining simplicity for adding new scenarios.

## Architecture Overview

```
tests/integration_scenarios/
├── __init__.py
├── conftest.py                      # Pytest configuration & fixtures
├── base/                            # Framework foundation
│   ├── __init__.py
│   ├── scenario_test_base.py       # Base test class
│   ├── module_mock.py              # Module simulation
│   ├── message_validators.py       # Message validation
│   └── result_assertions.py        # Common assertions
├── fixtures/                        # Test data & mocks
│   ├── __init__.py
│   ├── module_responses/           # Canned module responses
│   ├── sample_data/                # Test input data
│   └── expected_results/           # Expected outputs
├── utils/                          # Testing utilities
│   ├── __init__.py
│   ├── workflow_runner.py          # Workflow execution
│   ├── module_registry.py          # Test module registry
│   ├── performance_tracker.py      # Performance metrics
│   └── report_generator.py         # Test reporting
├── categories/                     # Organized test categories
│   ├── __init__.py
│   ├── security/                   # Security-focused scenarios
│   │   ├── __init__.py
│   │   ├── test_satellite_firmware.py
│   │   ├── test_supply_chain.py
│   │   └── test_quantum_crypto.py
│   ├── document_processing/        # Document workflows
│   │   ├── __init__.py
│   │   ├── test_pdf_extraction.py
│   │   ├── test_table_detection.py
│   │   └── test_multi_format.py
│   ├── research_integration/       # Research & analysis
│   │   ├── __init__.py
│   │   ├── test_arxiv_search.py
│   │   ├── test_youtube_learning.py
│   │   └── test_paper_validation.py
│   ├── ml_workflows/               # ML/AI scenarios
│   │   ├── __init__.py
│   │   ├── test_model_training.py
│   │   ├── test_llm_orchestration.py
│   │   └── test_adversarial_defense.py
│   └── knowledge_management/       # Knowledge graph scenarios
│       ├── __init__.py
│       ├── test_graph_building.py
│       ├── test_semantic_search.py
│       └── test_relationship_discovery.py
└── integration/                    # Full integration tests
    ├── __init__.py
    ├── test_end_to_end.py         # Complete workflows
    ├── test_error_recovery.py      # Failure scenarios
    └── test_performance.py         # Performance benchmarks
```

## Core Components

### 1. Base Test Class (`scenario_test_base.py`)

```python
"""
Base class for all integration scenario tests
"""

import pytest
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class TestMessage:
    """Test message with validation"""
    from_module: str
    to_module: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate message structure"""
        return all([self.from_module, self.to_module, self.content])

class ScenarioTestBase(ABC):
    """Base class for scenario tests"""
    
    def setup_method(self):
        """Setup test environment"""
        self.modules = {}
        self.messages = []
        self.results = []
        self.performance_metrics = {}
    
    @abstractmethod
    def register_modules(self) -> Dict[str, Dict[str, Any]]:
        """Register modules for this scenario"""
        pass
    
    @abstractmethod
    def create_test_workflow(self) -> List[TestMessage]:
        """Create the test workflow"""
        pass
    
    @abstractmethod
    def assert_results(self, results: List[Dict[str, Any]]) -> None:
        """Assert expected results"""
        pass
    
    def run_scenario(self, mock_responses: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute the scenario with optional mocking"""
        # Implementation details...
        pass
```

### 2. Module Mock System (`module_mock.py`)

```python
"""
Flexible module mocking for testing
"""

from typing import Dict, Any, Callable, Optional
import asyncio

class ModuleMock:
    """Mock a module's behavior"""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.responses = {}
        self.call_history = []
        self.delay = 0
        self.error_rate = 0
    
    def set_response(self, task: str, response: Any) -> None:
        """Set canned response for a task"""
        self.responses[task] = response
    
    def set_dynamic_response(self, task: str, handler: Callable) -> None:
        """Set dynamic response handler"""
        self.responses[task] = handler
    
    def set_error(self, task: str, error: Exception) -> None:
        """Set error response"""
        self.responses[task] = error
    
    async def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message"""
        self.call_history.append(message)
        
        # Simulate processing delay
        if self.delay:
            await asyncio.sleep(self.delay)
        
        # Simulate errors
        if self.should_error():
            raise RuntimeError(f"Mock error in {self.module_name}")
        
        task = message.get('task', 'default')
        response = self.responses.get(task, {"status": "ok"})
        
        if callable(response):
            return response(message)
        elif isinstance(response, Exception):
            raise response
        else:
            return response
```

### 3. Workflow Runner (`workflow_runner.py`)

```python
"""
Execute test workflows with monitoring
"""

import asyncio
from typing import List, Dict, Any, Optional
import time

class WorkflowRunner:
    """Run workflows with instrumentation"""
    
    def __init__(self, module_registry: Dict[str, Any]):
        self.module_registry = module_registry
        self.message_log = []
        self.performance_data = []
    
    async def execute_workflow(
        self, 
        workflow: List[TestMessage],
        timeout: int = 30
    ) -> List[Dict[str, Any]]:
        """Execute a test workflow"""
        results = []
        
        for step, message in enumerate(workflow):
            start_time = time.time()
            
            try:
                # Log message
                self.message_log.append({
                    "step": step,
                    "message": message,
                    "timestamp": start_time
                })
                
                # Route to module
                module = self.module_registry.get(message.to_module)
                if not module:
                    raise ValueError(f"Module {message.to_module} not found")
                
                # Process message
                result = await asyncio.wait_for(
                    module.process(message.content),
                    timeout=timeout
                )
                
                # Track performance
                duration = time.time() - start_time
                self.performance_data.append({
                    "step": step,
                    "module": message.to_module,
                    "duration": duration
                })
                
                results.append({
                    "step": step,
                    "from": message.from_module,
                    "to": message.to_module,
                    "result": result,
                    "duration": duration
                })
                
            except asyncio.TimeoutError:
                results.append({
                    "step": step,
                    "error": "timeout",
                    "module": message.to_module
                })
            except Exception as e:
                results.append({
                    "step": step,
                    "error": str(e),
                    "module": message.to_module
                })
        
        return results
```

### 4. Common Assertions (`result_assertions.py`)

```python
"""
Common assertions for scenario testing
"""

from typing import List, Dict, Any
import pytest

class ScenarioAssertions:
    """Reusable assertions for scenarios"""
    
    @staticmethod
    def assert_workflow_completed(results: List[Dict[str, Any]], expected_steps: int):
        """Assert all workflow steps completed"""
        assert len(results) == expected_steps, f"Expected {expected_steps} steps, got {len(results)}"
        
        for i, result in enumerate(results):
            assert result.get("step") == i, f"Step {i} missing or out of order"
            assert "error" not in result, f"Step {i} failed: {result.get('error')}"
    
    @staticmethod
    def assert_module_called(results: List[Dict[str, Any]], module_name: str, times: int = 1):
        """Assert a module was called expected number of times"""
        calls = [r for r in results if r.get("to") == module_name]
        assert len(calls) == times, f"Expected {module_name} called {times} times, got {len(calls)}"
    
    @staticmethod
    def assert_data_flow(results: List[Dict[str, Any]], key: str, from_step: int, to_step: int):
        """Assert data flows correctly between steps"""
        source_data = results[from_step]["result"].get(key)
        assert source_data is not None, f"Key '{key}' not found in step {from_step}"
        
        target_data = results[to_step]["result"].get(key)
        assert target_data == source_data, f"Data mismatch: {key} not propagated correctly"
    
    @staticmethod
    def assert_performance(results: List[Dict[str, Any]], max_duration: float):
        """Assert performance requirements"""
        total_duration = sum(r.get("duration", 0) for r in results)
        assert total_duration <= max_duration, f"Workflow took {total_duration}s, max allowed {max_duration}s"
```

## Example Test Implementation

```python
"""
Example: Testing satellite firmware vulnerability assessment
"""

import pytest
from tests.integration_scenarios.base import ScenarioTestBase, TestMessage
from tests.integration_scenarios.utils import ModuleMock
from tests.integration_scenarios.base import ScenarioAssertions

class TestSatelliteFirmwareVulnerability(ScenarioTestBase):
    """Test satellite firmware vulnerability assessment workflow"""
    
    def register_modules(self):
        """Register required modules"""
        return {
            "marker": ModuleMock("marker"),
            "sparta": ModuleMock("sparta"),
            "arxiv": ModuleMock("arxiv"),
            "llm_call": ModuleMock("llm_call"),
            "test_reporter": ModuleMock("test_reporter")
        }
    
    def create_test_workflow(self):
        """Create test workflow"""
        return [
            TestMessage(
                from_module="coordinator",
                to_module="marker",
                content={
                    "task": "extract_firmware_documentation",
                    "pdf_path": "test_firmware.pdf"
                }
            ),
            TestMessage(
                from_module="marker",
                to_module="sparta",
                content={
                    "task": "analyze_vulnerabilities",
                    "firmware_type": "satellite"
                }
            ),
            TestMessage(
                from_module="sparta",
                to_module="arxiv",
                content={
                    "task": "search_vulnerability_research"
                }
            ),
            TestMessage(
                from_module="arxiv",
                to_module="llm_call",
                content={
                    "task": "analyze_attack_vectors"
                }
            ),
            TestMessage(
                from_module="llm_call",
                to_module="test_reporter",
                content={
                    "task": "generate_report"
                }
            )
        ]
    
    def assert_results(self, results):
        """Assert expected outcomes"""
        # Basic workflow completion
        ScenarioAssertions.assert_workflow_completed(results, 5)
        
        # Module interactions
        ScenarioAssertions.assert_module_called(results, "marker", 1)
        ScenarioAssertions.assert_module_called(results, "sparta", 1)
        
        # Data flow
        assert results[0]["result"].get("firmware_specs") is not None
        assert results[1]["result"].get("cwe_matches") is not None
        assert len(results[1]["result"]["cwe_matches"]) > 0
        
        # Performance
        ScenarioAssertions.assert_performance(results, max_duration=10.0)
    
    @pytest.mark.integration
    async def test_successful_workflow(self):
        """Test successful vulnerability assessment"""
        # Setup mock responses
        self.modules["marker"].set_response("extract_firmware_documentation", {
            "firmware_specs": {"version": "2.1", "components": ["boot", "crypto"]},
            "interfaces": ["serial", "radio"]
        })
        
        self.modules["sparta"].set_response("analyze_vulnerabilities", {
            "cwe_matches": [
                {"cwe_id": "CWE-119", "severity": "high"},
                {"cwe_id": "CWE-327", "severity": "critical"}
            ]
        })
        
        # Run scenario
        results = await self.run_scenario()
        
        # Assert results
        self.assert_results(results)
    
    @pytest.mark.integration
    async def test_with_module_failure(self):
        """Test graceful handling of module failure"""
        # Setup failure
        self.modules["sparta"].set_error(
            "analyze_vulnerabilities",
            RuntimeError("SPARTA database unavailable")
        )
        
        # Run scenario
        results = await self.run_scenario()
        
        # Assert partial completion
        assert len(results) >= 2
        assert results[1].get("error") == "SPARTA database unavailable"
```

## Key Features

### 1. Flexibility
- Easy to add new test categories
- Simple module mocking
- Configurable workflows

### 2. Reusability
- Common base classes
- Shared assertions
- Test fixtures

### 3. Observability
- Performance tracking
- Message logging
- Detailed reporting

### 4. Scalability
- Parallel test execution
- Category-based organization
- Integration with pytest

### 5. Maintainability
- Clear structure
- Separation of concerns
- Comprehensive documentation

## Usage Patterns

### Adding a New Scenario Test

1. Choose appropriate category directory
2. Create test file following naming convention
3. Inherit from `ScenarioTestBase`
4. Implement required methods
5. Use common assertions
6. Add appropriate pytest markers

### Running Tests

```bash
# Run all integration scenarios
pytest tests/integration_scenarios/

# Run specific category
pytest tests/integration_scenarios/categories/security/

# Run with performance tracking
pytest tests/integration_scenarios/ --benchmark

# Generate HTML report
pytest tests/integration_scenarios/ --html=report.html
```

### Extending the Framework

1. Add new assertion methods to `ScenarioAssertions`
2. Create specialized mock behaviors in `ModuleMock`
3. Implement custom runners for specific patterns
4. Add new test categories as needed

## Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Test names should describe what's being tested
3. **Coverage**: Test both success and failure paths
4. **Performance**: Include performance assertions
5. **Documentation**: Comment complex test logic
6. **Reuse**: Use common patterns and utilities

## Migration Strategy

1. Start with high-value scenarios
2. Gradually move scenarios from `/scenarios` to `/tests/integration_scenarios`
3. Enhance with proper assertions and mocking
4. Add performance benchmarks
5. Generate comprehensive reports