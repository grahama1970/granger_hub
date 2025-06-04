"""
Test PDF extraction and processing scenarios
"""

import pytest
from tests.integration_scenarios.base.scenario_test_base import ScenarioTestBase, TestMessage
from tests.integration_scenarios.base.result_assertions import ScenarioAssertions


class TestPDFExtractionWorkflow(ScenarioTestBase):
    """Test PDF extraction and processing workflow"""
    
    def register_modules(self):
        """Modules provided by fixtures"""
        return {}
    
    def create_test_workflow(self):
        """Create workflow for PDF processing"""
        return [
            TestMessage(
                from_module="coordinator",
                to_module="marker",
                content={
                    "task": "extract_pdf",
                    "pdf_path": "research_paper.pdf",
                    "extract_tables": True,
                    "extract_images": True,
                    "output_format": "markdown"
                },
                metadata={"step": 1, "description": "Extract PDF content"}
            ),
            TestMessage(
                from_module="marker",
                to_module="arangodb",
                content={
                    "task": "store_document",
                    "document_type": "research_paper",
                    "create_embeddings": True,
                    "extract_entities": True
                },
                metadata={"step": 2, "description": "Store in knowledge graph"}
            ),
            TestMessage(
                from_module="arangodb",
                to_module="llm_call",
                content={
                    "task": "generate_summary",
                    "max_length": 500,
                    "focus_areas": ["methodology", "results", "conclusions"]
                },
                metadata={"step": 3, "description": "Generate summary"}
            ),
            TestMessage(
                from_module="llm_call",
                to_module="test_reporter",
                content={
                    "task": "create_extraction_report",
                    "include_metrics": True,
                    "format": "html"
                },
                metadata={"step": 4, "description": "Generate report"}
            )
        ]
    
    def assert_results(self, results):
        """Assert expected outcomes"""
        ScenarioAssertions.assert_workflow_completed(results, 4)
        ScenarioAssertions.assert_no_errors(results)
        
        # Check extraction results
        extraction_result = results[0]["result"]
        assert extraction_result.get("status") == "success"
        assert extraction_result.get("content") is not None
        
        # Verify data was stored
        storage_result = results[1]["result"]
        assert storage_result.get("document_id") is not None
        assert storage_result.get("embeddings_created") is True
    
    @pytest.mark.integration
    @pytest.mark.document_processing
    async def test_successful_extraction(self, mock_modules, workflow_runner):
        """Test successful PDF extraction workflow"""
        # Setup mock responses
        mock_modules.get_mock("marker").set_response("extract_pdf", {
            "status": "success",
            "content": "# Research Paper\n\n## Abstract\n\nThis paper presents...",
            "tables": [{"rows": 5, "cols": 3, "content": "table_data"}],
            "images": ["image_1.png", "image_2.png"],
            "metadata": {"pages": 15, "title": "Research Paper"}
        })
        
        mock_modules.get_mock("arangodb").set_response("store_document", {
            "document_id": "doc_12345",
            "embeddings_created": True,
            "entities_extracted": ["AI", "Machine Learning", "Neural Networks"],
            "relationships_created": 5
        })
        
        mock_modules.get_mock("llm_call").set_response("generate_summary", {
            "summary": "This research paper explores advanced AI techniques...",
            "key_points": ["Novel approach", "Significant results", "Future work"]
        })
        
        mock_modules.get_mock("test_reporter").set_response("create_extraction_report", {
            "report_path": "/tmp/extraction_report.html",
            "metrics": {
                "extraction_time": 2.5,
                "tables_found": 1,
                "images_found": 2
            }
        })
        
        workflow_runner.module_registry = mock_modules.mocks
        
        # Run scenario
        result = await self.run_scenario()
        
        # Assert success
        assert result["success"] is True
        self.assert_results(result["results"])
        
        # Verify all modules were called
        for module in ["marker", "arangodb", "llm_call", "test_reporter"]:
            assert mock_modules.get_mock(module).call_count == 1
    
    @pytest.mark.integration
    @pytest.mark.document_processing
    async def test_table_extraction_focus(self, mock_modules, workflow_runner):
        """Test workflow focused on table extraction"""
        # Modified workflow for table focus
        self.table_workflow = [
            TestMessage(
                from_module="coordinator",
                to_module="mcp_screenshot",
                content={
                    "task": "capture_pdf_page",
                    "pdf_path": "data_tables.pdf",
                    "page_number": 3
                }
            ),
            TestMessage(
                from_module="mcp_screenshot",
                to_module="marker",
                content={
                    "task": "extract_tables_from_image",
                    "confidence_threshold": 0.95
                }
            ),
            TestMessage(
                from_module="marker",
                to_module="arangodb",
                content={
                    "task": "store_structured_data",
                    "data_type": "table",
                    "validate_schema": True
                }
            )
        ]
        
        # Setup mocks
        mock_modules.get_mock("mcp_screenshot").set_response("capture_pdf_page", {
            "screenshot_path": "/tmp/page_3.png",
            "page_info": {"number": 3, "has_tables": True}
        })
        
        mock_modules.get_mock("marker").set_response("extract_tables_from_image", {
            "tables": [
                {
                    "confidence": 0.98,
                    "rows": 10,
                    "columns": 5,
                    "data": [["header1", "header2"], ["data1", "data2"]]
                }
            ],
            "extraction_quality": "high"
        })
        
        mock_modules.get_mock("arangodb").set_response("store_structured_data", {
            "collection": "extracted_tables",
            "document_id": "table_456",
            "validation_passed": True
        })
        
        workflow_runner.module_registry = mock_modules.mocks
        
        # Override workflow for this test
        original_workflow = self.create_test_workflow
        self.create_test_workflow = lambda: self.table_workflow
        
        # Run scenario
        result = await self.run_scenario()
        
        # Restore original workflow
        self.create_test_workflow = original_workflow
        
        # Assert table extraction success
        assert result["success"] is True
        assert result["completed_steps"] == 3
        
        # Verify table was extracted with high confidence
        table_result = result["results"][1]["result"]
        assert table_result["tables"][0]["confidence"] > 0.95
        assert table_result["extraction_quality"] == "high"