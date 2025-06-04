"""
Test satellite firmware vulnerability assessment scenario
"""

import pytest
from tests.integration_scenarios.base.scenario_test_base import ScenarioTestBase, TestMessage
from tests.integration_scenarios.base.result_assertions import ScenarioAssertions


class TestSatelliteFirmwareVulnerability(ScenarioTestBase):
    """Test satellite firmware vulnerability assessment workflow"""
    
    def register_modules(self):
        """Use mock modules from conftest"""
        # Modules are provided by the mock_modules fixture
        # We'll get them from the workflow runner
        return {}
    
    def create_test_workflow(self):
        """Create test workflow for firmware vulnerability assessment"""
        return [
            TestMessage(
                from_module="coordinator",
                to_module="marker",
                content={
                    "task": "extract_firmware_documentation",
                    "pdf_path": "satellite_firmware_v2.1_spec.pdf",
                    "extract_code_blocks": True,
                    "extract_diagrams": True,
                    "focus_areas": [
                        "boot_sequence",
                        "update_mechanism", 
                        "cryptographic_functions",
                        "external_interfaces",
                        "memory_management"
                    ]
                },
                metadata={"step": 1, "description": "Extract firmware specifications"}
            ),
            TestMessage(
                from_module="marker",
                to_module="sparta",
                content={
                    "task": "analyze_vulnerabilities",
                    "firmware_type": "embedded_satellite",
                    "cwe_categories": [
                        "CWE-119", "CWE-120", "CWE-121", "CWE-122",
                        "CWE-306", "CWE-327", "CWE-415", "CWE-416"
                    ],
                    "check_mode": "comprehensive",
                    "include_space_specific": True
                },
                metadata={"step": 2, "description": "Check against CWE database"}
            ),
            TestMessage(
                from_module="sparta",
                to_module="arxiv",
                content={
                    "task": "search_vulnerability_research",
                    "search_queries_from_cwe_matches": True,
                    "additional_searches": [
                        "satellite firmware vulnerabilities",
                        "embedded systems space security",
                        "radiation effects firmware security"
                    ],
                    "categories": ["cs.CR", "cs.AR", "eess.SP"],
                    "max_papers": 20,
                    "sort_by": "relevance"
                },
                metadata={"step": 3, "description": "Research related vulnerabilities"}
            ),
            TestMessage(
                from_module="arxiv",
                to_module="llm_call",
                content={
                    "task": "analyze_attack_vectors",
                    "models": ["claude-3-opus", "gpt-4"],
                    "analysis_prompts": {
                        "attack_scenarios": "Generate realistic attack scenarios",
                        "risk_assessment": "Assess risk considering space constraints",
                        "exploit_likelihood": "Evaluate exploit likelihood"
                    },
                    "threat_actors": ["nation_state", "cybercriminal", "insider_threat"],
                    "validate_responses": True
                },
                metadata={"step": 4, "description": "Multi-model attack analysis"}
            ),
            TestMessage(
                from_module="llm_call",
                to_module="test_reporter",
                content={
                    "task": "generate_vulnerability_report",
                    "report_sections": [
                        "executive_summary",
                        "vulnerability_findings",
                        "attack_scenarios",
                        "risk_matrix",
                        "remediation_recommendations"
                    ],
                    "severity_scoring": "CVSS_3.1",
                    "include_poc": False
                },
                metadata={"step": 5, "description": "Generate final report"}
            )
        ]
    
    def assert_results(self, results):
        """Assert expected outcomes"""
        # Basic workflow completion
        ScenarioAssertions.assert_workflow_completed(results, 5)
        
        # Module interactions
        ScenarioAssertions.assert_module_called(results, "marker", 1)
        ScenarioAssertions.assert_module_called(results, "sparta", 1)
        ScenarioAssertions.assert_module_called(results, "arxiv", 1)
        ScenarioAssertions.assert_module_called(results, "llm_call", 1)
        ScenarioAssertions.assert_module_called(results, "test_reporter", 1)
        
        # Verify module sequence
        ScenarioAssertions.assert_module_sequence(results, [
            "marker", "sparta", "arxiv", "llm_call", "test_reporter"
        ])
        
        # Data flow assertions
        assert results[0]["result"].get("firmware_specs") is not None
        assert results[1]["result"].get("cwe_matches") is not None
        assert len(results[1]["result"]["cwe_matches"]) > 0
        
        # Performance requirements
        ScenarioAssertions.assert_performance(
            results, 
            max_total_duration=10.0,
            max_step_duration=3.0
        )
    
    @pytest.mark.integration
    @pytest.mark.security
    async def test_successful_workflow(self, mock_modules, workflow_runner, sample_responses):
        """Test successful vulnerability assessment workflow"""
        # Setup mock responses
        mock_modules.set_responses(sample_responses)
        
        # Additional specific responses for this test
        mock_modules.get_mock("arxiv").set_response(
            "search_vulnerability_research",
            {
                "research_papers": [
                    {"title": "Satellite Firmware Security Analysis", "relevance": 0.95},
                    {"title": "Space System Vulnerabilities", "relevance": 0.89}
                ],
                "attack_methods": ["buffer_overflow", "command_injection", "crypto_bypass"],
                "defense_strategies": ["secure_boot", "code_signing", "memory_protection"]
            }
        )
        
        mock_modules.get_mock("llm_call").set_response(
            "analyze_attack_vectors",
            {
                "attack_scenarios": [
                    {"scenario": "Remote code execution via buffer overflow", "likelihood": "high"},
                    {"scenario": "Cryptographic key extraction", "likelihood": "medium"}
                ],
                "risk_assessments": [
                    {"vulnerability": "CWE-119", "risk_level": "high", "cvss_score": 8.5},
                    {"vulnerability": "CWE-327", "risk_level": "critical", "cvss_score": 9.1}
                ],
                "exploit_likelihood": {"overall": "high", "timeline": "6-12 months"}
            }
        )
        
        # Set runner modules
        workflow_runner.module_registry = mock_modules.mocks
        
        # Run scenario
        result = await self.run_scenario()
        
        # Assert overall success
        assert result["success"] is True
        assert result["completed_steps"] == 5
        
        # Assert specific results
        self.assert_results(result["results"])
        
        # Verify mock calls
        mock_modules.get_mock("marker").assert_called("extract_firmware_documentation", 1)
        mock_modules.get_mock("sparta").assert_called("analyze_vulnerabilities", 1)
    
    @pytest.mark.integration
    @pytest.mark.security
    async def test_with_sparta_failure(self, mock_modules, workflow_runner):
        """Test handling of SPARTA module failure"""
        # Setup mocks
        mock_modules.get_mock("marker").set_response(
            "extract_firmware_documentation",
            {"firmware_specs": {"version": "2.1"}, "interfaces": ["serial"]}
        )
        
        # Make SPARTA fail
        mock_modules.get_mock("sparta").set_error(
            "analyze_vulnerabilities",
            RuntimeError("SPARTA database unavailable")
        )
        
        # Set runner modules
        workflow_runner.module_registry = mock_modules.mocks
        
        # Run scenario
        result = await self.run_scenario(fail_fast=True)
        
        # Assert partial completion
        assert result["success"] is False
        assert result["completed_steps"] == 1
        assert len(result["errors"]) == 1
        
        # Check error details
        ScenarioAssertions.assert_error_at_step(
            result["results"], 
            step=1,
            error_contains="SPARTA database unavailable"
        )
    
    @pytest.mark.integration
    @pytest.mark.security
    @pytest.mark.slow
    async def test_with_performance_delays(self, mock_modules, workflow_runner, performance_monitor):
        """Test workflow with simulated delays"""
        # Setup mocks with delays
        mock_modules.get_mock("marker").set_response(
            "extract_firmware_documentation",
            {"firmware_specs": {"version": "2.1"}},
            delay=0.5
        )
        
        mock_modules.get_mock("sparta").set_response(
            "analyze_vulnerabilities",
            {"cwe_matches": [{"cwe_id": "CWE-119", "severity": "high"}]},
            delay=1.0
        )
        
        mock_modules.get_mock("arxiv").set_response(
            "search_vulnerability_research",
            {"research_papers": [], "attack_methods": []},
            delay=2.0
        )
        
        # Set quick responses for remaining modules
        mock_modules.get_mock("llm_call").set_response(
            "analyze_attack_vectors",
            {"attack_scenarios": [], "risk_assessments": []}
        )
        
        mock_modules.get_mock("test_reporter").set_response(
            "generate_vulnerability_report",
            {"report_path": "/tmp/report.html", "status": "completed"}
        )
        
        # Set runner modules
        workflow_runner.module_registry = mock_modules.mocks
        
        # Run with performance monitoring
        with performance_monitor.measure("full_workflow"):
            result = await self.run_scenario()
        
        # Verify completion despite delays
        assert result["success"] is True
        
        # Check performance
        performance_monitor.assert_performance("full_workflow", max_duration=5.0)
        
        # Verify individual step performance from results
        for step_result in result["results"]:
            if step_result.get("to") == "arxiv":
                assert step_result["duration"] >= 2.0  # Should have delay
    
    @pytest.mark.integration
    @pytest.mark.security
    async def test_data_flow_integrity(self, mock_modules, workflow_runner):
        """Test that data flows correctly through the workflow"""
        # Setup detailed mock responses
        firmware_data = {
            "version": "2.1",
            "components": ["bootloader", "crypto", "comms"],
            "vulnerabilities": ["buffer_overflow_risk", "weak_crypto"]
        }
        
        mock_modules.get_mock("marker").set_dynamic_response(
            "extract_firmware_documentation",
            lambda msg: {
                "firmware_specs": firmware_data,
                "interfaces": msg["content"]["focus_areas"][:2]  # Use input data
            }
        )
        
        # SPARTA should receive and process firmware data
        def sparta_handler(msg):
            assert "firmware_type" in msg["content"]
            return {
                "cwe_matches": [
                    {"cwe_id": cwe, "severity": "high"} 
                    for cwe in msg["content"]["cwe_categories"][:2]
                ],
                "firmware_version": firmware_data["version"]  # Include firmware version
            }
        
        mock_modules.get_mock("sparta").set_dynamic_response(
            "analyze_vulnerabilities",
            sparta_handler
        )
        
        # Set other responses
        mock_modules.get_mock("arxiv").set_response(
            "search_vulnerability_research",
            {"research_papers": [], "attack_methods": []}
        )
        
        mock_modules.get_mock("llm_call").set_response(
            "analyze_attack_vectors",
            {"attack_scenarios": [], "risk_assessments": []}
        )
        
        mock_modules.get_mock("test_reporter").set_response(
            "generate_vulnerability_report",
            {"report_path": "/tmp/report.html"}
        )
        
        # Set runner modules
        workflow_runner.module_registry = mock_modules.mocks
        
        # Run scenario
        result = await self.run_scenario()
        
        # Verify data flow
        assert result["success"] is True
        
        # Check that firmware version propagated
        sparta_result = result["results"][1]["result"]
        assert sparta_result["firmware_version"] == "2.1"
        
        # Check that CWE matches are based on input
        assert len(sparta_result["cwe_matches"]) == 2
        assert sparta_result["cwe_matches"][0]["cwe_id"] == "CWE-119"