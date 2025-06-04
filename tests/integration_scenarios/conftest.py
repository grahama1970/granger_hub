"""
Pytest configuration and fixtures for integration scenario tests
"""

import pytest
import asyncio
from typing import Dict, Any, List
import os
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from tests.integration_scenarios.base.module_mock import ModuleMock, ModuleMockGroup
from tests.integration_scenarios.base.message_validators import create_standard_validator
from tests.integration_scenarios.utils.workflow_runner import WorkflowRunner, ParallelWorkflowRunner


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_modules() -> ModuleMockGroup:
    """Provide a group of mock modules"""
    group = ModuleMockGroup()
    
    # Add common modules
    modules = [
        "marker", "sparta", "arangodb", "arxiv", "youtube_transcripts",
        "llm_call", "test_reporter", "unsloth", "chat", "mcp_screenshot"
    ]
    
    for module in modules:
        group.add_mock(module)
    
    return group


@pytest.fixture
def workflow_runner(mock_modules) -> WorkflowRunner:
    """Provide a workflow runner with mock modules"""
    return WorkflowRunner(mock_modules.mocks)


@pytest.fixture
def parallel_runner(mock_modules) -> ParallelWorkflowRunner:
    """Provide a parallel workflow runner"""
    return ParallelWorkflowRunner(mock_modules.mocks)


@pytest.fixture
def message_validator():
    """Provide a standard message validator"""
    return create_standard_validator()


@pytest.fixture
def sample_pdf_path(tmp_path) -> str:
    """Create a sample PDF path for testing"""
    pdf_path = tmp_path / "test_document.pdf"
    pdf_path.write_bytes(b"")  # Empty PDF for testing
    return str(pdf_path)


@pytest.fixture
def sample_responses() -> Dict[str, Dict[str, Any]]:
    """Provide sample module responses for testing"""
    return {
        "marker": {
            "extract_pdf": {
                "status": "success",
                "content": "# Document Title\n\nExtracted content...",
                "tables": [],
                "metadata": {"pages": 10}
            },
            "extract_firmware_documentation": {
                "firmware_specs": {
                    "version": "2.1",
                    "components": ["bootloader", "crypto", "comms"]
                },
                "interfaces": ["serial", "radio", "debug"],
                "dependencies": ["crypto_lib_v1.2"],
                "update_mechanisms": ["OTA", "serial"]
            }
        },
        "sparta": {
            "analyze_vulnerabilities": {
                "cwe_matches": [
                    {"cwe_id": "CWE-119", "severity": "high", "description": "Buffer overflow"},
                    {"cwe_id": "CWE-327", "severity": "critical", "description": "Broken crypto"}
                ],
                "vulnerability_scores": {"total": 8.5, "exploitability": 7.0},
                "mitigation_controls": ["input_validation", "secure_boot"]
            }
        },
        "arxiv": {
            "search": {
                "papers": [
                    {
                        "title": "Security Analysis of Satellite Systems",
                        "authors": ["Smith, J.", "Doe, A."],
                        "abstract": "We analyze security...",
                        "url": "https://arxiv.org/abs/2024.12345"
                    }
                ],
                "total_results": 42
            }
        },
        "llm_call": {
            "analyze": {
                "analysis": "Based on the vulnerabilities found...",
                "risk_level": "high",
                "recommendations": ["patch_firmware", "enable_secure_boot"]
            }
        },
        "test_reporter": {
            "generate_report": {
                "report_path": "/tmp/report_12345.html",
                "summary": "Critical vulnerabilities found",
                "status": "completed"
            }
        }
    }


@pytest.fixture
def performance_monitor():
    """Provide a performance monitoring context manager"""
    class PerformanceMonitor:
        def __init__(self):
            self.measurements = {}
        
        def measure(self, name: str):
            import time
            
            class Timer:
                def __init__(self, monitor, name):
                    self.monitor = monitor
                    self.name = name
                    self.start = None
                
                def __enter__(self):
                    self.start = time.time()
                    return self
                
                def __exit__(self, *args):
                    duration = time.time() - self.start
                    self.monitor.measurements[self.name] = duration
            
            return Timer(self, name)
        
        def assert_performance(self, name: str, max_duration: float):
            assert name in self.measurements, f"No measurement for '{name}'"
            duration = self.measurements[name]
            assert duration <= max_duration, f"{name} took {duration:.2f}s, max allowed {max_duration}s"
    
    return PerformanceMonitor()


# Pytest markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers", 
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", 
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", 
        "security: mark test as security-related"
    )
    config.addinivalue_line(
        "markers", 
        "document_processing: mark test as document processing related"
    )
    config.addinivalue_line(
        "markers", 
        "ml_workflow: mark test as ML/AI workflow related"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location"""
    for item in items:
        # Add markers based on test file location
        if "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        elif "document_processing" in str(item.fspath):
            item.add_marker(pytest.mark.document_processing)
        elif "ml_workflows" in str(item.fspath):
            item.add_marker(pytest.mark.ml_workflow)
        
        # Mark all tests in integration_scenarios as integration tests
        if "integration_scenarios" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# Async test support
@pytest.fixture
def async_test():
    """Helper for running async tests"""
    def _run(coro):
        return asyncio.run(coro)
    return _run


# Test data fixtures
@pytest.fixture
def security_test_data():
    """Provide security-related test data"""
    return {
        "cwe_list": [
            "CWE-119", "CWE-120", "CWE-121", "CWE-122",
            "CWE-306", "CWE-327", "CWE-415", "CWE-416"
        ],
        "threat_actors": [
            "nation_state", "cybercriminal", "insider_threat"
        ],
        "firmware_types": [
            "embedded_satellite", "ground_station", "payload_processor"
        ]
    }


@pytest.fixture
def document_test_data(tmp_path):
    """Provide document processing test data"""
    # Create test PDFs
    test_pdfs = []
    for i in range(3):
        pdf_path = tmp_path / f"test_doc_{i}.pdf"
        pdf_path.write_bytes(b"PDF content")
        test_pdfs.append(str(pdf_path))
    
    return {
        "pdf_paths": test_pdfs,
        "expected_formats": ["markdown", "json", "html"],
        "table_confidence_threshold": 0.95
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test"""
    yield
    # Cleanup code here if needed


# Report generation
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Add custom information to terminal summary"""
    if hasattr(terminalreporter, 'stats'):
        passed = len(terminalreporter.stats.get('passed', []))
        failed = len(terminalreporter.stats.get('failed', []))
        skipped = len(terminalreporter.stats.get('skipped', []))
        
        terminalreporter.section("Integration Scenario Test Summary")
        terminalreporter.write_line(f"Passed: {passed}")
        terminalreporter.write_line(f"Failed: {failed}")
        terminalreporter.write_line(f"Skipped: {skipped}")
        
        # Add performance summary if available
        if hasattr(config, '_performance_data'):
            terminalreporter.section("Performance Summary")
            for test, duration in config._performance_data.items():
                terminalreporter.write_line(f"{test}: {duration:.2f}s")