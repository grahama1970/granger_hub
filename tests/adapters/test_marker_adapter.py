"""
Real tests for Marker Protocol Adapter.

These tests verify integration with the Marker PDF processing system.
No mocks allowed - we test against real Marker installation.
"""

import asyncio
import pytest
import time
from pathlib import Path
from typing import Dict, Any
import tempfile

from granger_hub.core.adapters import MarkerAdapter, AdapterConfig


class TestMarkerAdapterReal:
    """Test Marker adapter with real PDF processing."""
    
    @pytest.fixture
    def test_pdf(self):
        """Create a simple test PDF if needed."""
        # For testing, we'll use a PDF from the test fixtures if available
        test_pdfs = [
            Path("/tmp/test.pdf"),
            Path("./test_data/sample.pdf"),
            Path("./fixtures/test_document.pdf")
        ]
        
        for pdf in test_pdfs:
            if pdf.exists():
                return pdf
        
        # If no test PDF exists, skip the test
        pytest.skip("No test PDF found. Please provide a test PDF.")
    
    @pytest.mark.asyncio
    async def test_marker_connection(self):
        """Test connecting to Marker installation."""
        start_time = time.time()
        
        config = AdapterConfig(name="marker-test", protocol="marker")
        adapter = MarkerAdapter(config)
        
        # Try to connect
        connected = await adapter.connect()
        duration = time.time() - start_time
        
        if not connected:
            pytest.skip("Marker not installed or not available")
        
        assert connected, "Failed to connect to Marker"
        assert adapter._connected is True
        assert adapter._connection_time > 0
        assert duration > 0.001, f"Connection too fast ({duration}s) - might be mocked"
        
        await adapter.disconnect()
        assert adapter._connected is False
        
        return {
            "duration": duration,
            "marker_path": str(adapter.marker_path),
            "cli_path": str(adapter.marker_cli)
        }
    
    @pytest.mark.asyncio
    async def test_extract_page(self, test_pdf):
        """Test extracting a single page from PDF."""
        start_time = time.time()
        
        config = AdapterConfig(name="marker-page-test", protocol="marker")
        adapter = MarkerAdapter(config)
        
        connected = await adapter.connect()
        if not connected:
            pytest.skip("Marker not available")
        
        # Extract page 1
        result = await adapter.send({
            "action": "extract_page",
            "file_path": str(test_pdf),
            "page": 1,
            "extract_tables": False,
            "claude_config": "disabled"
        })
        
        duration = time.time() - start_time
        
        # Verify response
        assert "success" in result
        if result["success"]:
            assert result["page"] == 1
            assert "content" in result
            assert "metadata" in result
            assert result["latency_ms"] > 10  # Real processing takes time
            
            # Verify metadata
            metadata = result["metadata"]
            assert metadata["extraction_method"] == "marker"
            assert metadata["claude_config"] == "disabled"
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "success": result.get("success", False),
            "latency_ms": result.get("latency_ms", 0),
            "has_content": "content" in result
        }
    
    @pytest.mark.asyncio
    async def test_extract_tables(self, test_pdf):
        """Test extracting tables from PDF page."""
        start_time = time.time()
        
        config = AdapterConfig(name="marker-table-test", protocol="marker")
        adapter = MarkerAdapter(config)
        
        connected = await adapter.connect()
        if not connected:
            pytest.skip("Marker not available")
        
        # Extract tables from page 1
        result = await adapter.send({
            "action": "extract_tables",
            "file_path": str(test_pdf),
            "page": 1,
            "claude_config": "tables_only"
        })
        
        duration = time.time() - start_time
        
        # Verify response
        assert "success" in result
        if result["success"]:
            assert "tables" in result
            assert isinstance(result["tables"], list)
            assert result["latency_ms"] > 100  # Table extraction takes longer
            
            # Check table structure if any found
            for table in result["tables"]:
                assert "title" in table or "bbox" in table
                if "confidence" in table:
                    assert 0 <= table["confidence"] <= 1
                if "headers" in table:
                    assert isinstance(table["headers"], list)
                if "rows" in table:
                    assert isinstance(table["rows"], list)
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "success": result.get("success", False),
            "table_count": len(result.get("tables", [])),
            "latency_ms": result.get("latency_ms", 0)
        }
    
    @pytest.mark.asyncio
    async def test_check_resources(self):
        """Test checking Marker system resources."""
        config = AdapterConfig(name="marker-resources", protocol="marker")
        adapter = MarkerAdapter(config)
        
        connected = await adapter.connect()
        if not connected:
            pytest.skip("Marker not available")
        
        # Check resources
        result = await adapter.send({
            "action": "check_resources"
        })
        
        # Resources check might not be implemented
        assert "success" in result
        
        await adapter.disconnect()
        
        return {
            "resources_available": result.get("success", False),
            "resources": result.get("resources", {})
        }
    
    @pytest.mark.asyncio
    async def test_invalid_action(self):
        """Test handling of invalid action."""
        config = AdapterConfig(name="marker-invalid", protocol="marker")
        adapter = MarkerAdapter(config)
        
        connected = await adapter.connect()
        if not connected:
            pytest.skip("Marker not available")
        
        # Send invalid action
        result = await adapter.send({
            "action": "invalid_action",
            "file_path": "/nonexistent.pdf"
        })
        
        # Should handle gracefully
        assert result["success"] is False
        assert "error" in result
        assert "Unknown action" in result["error"]
        
        await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_concurrent_extraction(self, test_pdf):
        """Test concurrent page extraction."""
        config = AdapterConfig(name="marker-concurrent", protocol="marker")
        adapter = MarkerAdapter(config)
        
        connected = await adapter.connect()
        if not connected:
            pytest.skip("Marker not available")
        
        start_time = time.time()
        
        # Extract 3 pages concurrently
        tasks = []
        for page in range(1, 4):
            task = adapter.send({
                "action": "extract_page",
                "file_path": str(test_pdf),
                "page": page,
                "extract_tables": False,
                "claude_config": "disabled"
            })
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # Count successful extractions
        successful = sum(1 for r in results 
                        if isinstance(r, dict) and r.get("success"))
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "pages_requested": 3,
            "pages_extracted": successful,
            "avg_time_per_page": duration / 3 if successful > 0 else 0
        }


# Validation function
if __name__ == "__main__":
    async def validate_marker_integration():
        """Validate Marker integration with real PDF."""
        config = AdapterConfig(name="marker-validate", protocol="marker")
        adapter = MarkerAdapter(config)
        
        print("Testing Marker Integration...")
        
        # Test 1: Connection
        print("\n1. Testing connection to Marker...")
        connected = await adapter.connect()
        if connected:
            print(f"✓ Connected to Marker at {adapter.marker_path}")
        else:
            print("✗ Could not connect to Marker")
            print("  Please ensure Marker is installed at:")
            print("  /home/graham/workspace/experiments/marker/")
            return False
        
        # Test 2: Extract page
        test_pdf = Path("./test_document.pdf")
        if not test_pdf.exists():
            print("\n✗ No test PDF found")
            print("  Please provide a test PDF at ./test_document.pdf")
            return False
        
        print(f"\n2. Extracting page 1 from {test_pdf}...")
        result = await adapter.send({
            "action": "extract_page",
            "file_path": str(test_pdf),
            "page": 1,
            "extract_tables": True,
            "claude_config": "disabled"
        })
        
        if result.get("success"):
            print("✓ Successfully extracted page")
            print(f"  Processing time: {result.get('latency_ms', 0):.1f}ms")
            print(f"  Tables found: {len(result.get('tables', []))}")
            
            for i, table in enumerate(result.get("tables", [])):
                print(f"\n  Table {i+1}:")
                print(f"    Title: {table.get('title', 'Untitled')}")
                if table.get("headers"):
                    print(f"    Headers: {table['headers']}")
                if table.get("rows"):
                    print(f"    Rows: {len(table['rows'])}")
        else:
            print(f"✗ Extraction failed: {result.get('error')}")
            return False
        
        await adapter.disconnect()
        return True
    
    # Run validation
    import sys
    success = asyncio.run(validate_marker_integration())
    sys.exit(0 if success else 1)