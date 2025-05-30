"""
Test PDF Navigator Module.

Tests PDF navigation, screenshot capture, and table extraction functionality.
"""

import pytest
import asyncio
from pathlib import Path
import json
import tempfile
from PIL import Image, ImageDraw, ImageFont

from claude_coms.core.modules.pdf_navigator_module import PDFNavigatorModule


class TestPDFNavigator:
    """Test PDF navigation features."""
    
    @pytest.fixture
    async def pdf_module(self):
        """Create PDF navigator module."""
        return PDFNavigatorModule()
    
    @pytest.fixture
    def sample_pdf(self):
        """Create a sample PDF for testing."""
        # For actual testing, we'd need a real PDF with tables
        # This is a placeholder path
        return Path("/tmp/test_document.pdf")
    
    @pytest.mark.asyncio
    async def test_navigate_to_page(self, pdf_module):
        """Test navigating to a specific page."""
        # This test would require a real PDF file
        # For now, we test the error handling
        result = await pdf_module.process({
            "action": "navigate",
            "file": "/nonexistent.pdf",
            "page": 42
        })
        
        assert result["success"] is False
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_extract_tables_with_mock_image(self, pdf_module):
        """Test table extraction with a mock image."""
        # Create a temporary image that simulates a PDF page with a table
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            # Create simple image with text
            img = Image.new('RGB', (800, 1000), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw some text to simulate a page with a table
            draw.text((50, 50), "Page 42", fill='black')
            draw.text((50, 100), "Table 1: Sales Data Q4 2023", fill='black')
            draw.rectangle([50, 150, 750, 500], outline='black')
            
            # Draw table headers
            draw.text((60, 160), "Product | Q1 | Q2 | Q3 | Q4", fill='black')
            draw.line([50, 190, 750, 190], fill='black')
            
            # Draw table rows
            draw.text((60, 200), "Widget A | 100 | 150 | 200 | 250", fill='black')
            draw.text((60, 230), "Widget B | 80 | 90 | 110 | 130", fill='black')
            
            img.save(tmp.name)
            
            # Test table extraction from the image
            result = await pdf_module._extract_tables_from_image(
                Path(tmp.name), 42
            )
            
            # The result depends on the AI analysis, but we can check structure
            assert "success" in result or "tables" in result
            if result.get("tables"):
                assert isinstance(result["tables"], list)
                if result["tables"]:
                    table = result["tables"][0]
                    assert "title" in table or "headers" in table
    
    @pytest.mark.asyncio
    async def test_pdf_navigation_actions(self, pdf_module):
        """Test different PDF navigation actions."""
        # Test invalid action
        result = await pdf_module.process({
            "action": "invalid_action"
        })
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
        
        # Test extract_tables action without file
        result = await pdf_module.process({
            "action": "extract_tables"
        })
        
        assert result["success"] is False
        assert "No PDF file" in result["error"]
    
    @pytest.mark.asyncio
    async def test_annotation_placeholder(self, pdf_module):
        """Test annotation action (currently not implemented)."""
        result = await pdf_module.process({
            "action": "annotate",
            "file": "/some/file.pdf"
        })
        
        assert result["success"] is False
        assert "not yet implemented" in result["error"]


# Validation function
if __name__ == "__main__":
    import sys
    
    async def validate_pdf_navigation():
        """Validate PDF navigation with real data."""
        module = PDFNavigatorModule()
        
        # Check if we have a test PDF
        test_pdf = Path("./test_data/sample.pdf")
        if not test_pdf.exists():
            print("❌ No test PDF found at ./test_data/sample.pdf")
            print("   Please provide a PDF with tables on page 42 for testing")
            return False
        
        print("Testing PDF Navigation...")
        
        # Test 1: Navigate to page 42 and extract tables
        print("\n1. Navigating to page 42 and extracting tables...")
        result = await module.process({
            "action": "navigate",
            "file": str(test_pdf),
            "page": 42,
            "extract_tables": True,
            "annotate": True
        })
        
        if result.get("success"):
            print(f"✓ Successfully navigated to page 42")
            print(f"  Screenshot: {result['screenshot']}")
            print(f"  Tables found: {len(result.get('tables', []))}")
            
            for i, table in enumerate(result.get('tables', [])):
                print(f"\n  Table {i+1}: {table.get('title', 'Untitled')}")
                if table.get('headers'):
                    print(f"    Headers: {table['headers']}")
                if table.get('rows'):
                    print(f"    Data rows: {len(table['rows'])}")
                
                # Save table data
                with open(f"table_{i+1}_page_42.json", 'w') as f:
                    json.dump(table, f, indent=2)
                print(f"    Saved to: table_{i+1}_page_42.json")
            
            return True
        else:
            print(f"✗ Navigation failed: {result.get('error')}")
            return False
    
    # Run validation
    success = asyncio.run(validate_pdf_navigation())
    sys.exit(0 if success else 1)