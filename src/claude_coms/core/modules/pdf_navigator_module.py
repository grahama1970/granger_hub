"""
PDF Navigator Module for claude-module-communicator.

This module provides PDF navigation, screenshot capture, table extraction, and annotation capabilities.
It uses pdf2image for page rendering and can extract tables with AI assistance.

Dependencies:
- pdf2image: https://pypi.org/project/pdf2image/
- Pillow: https://pillow.readthedocs.io/

Sample input:
{
    "action": "navigate",
    "file": "document.pdf",
    "page": 42,
    "extract_tables": true,
    "annotate": true
}

Expected output:
{
    "success": true,
    "page": 42,
    "screenshot": "page_42.png",
    "tables": [
        {
            "title": "Inferred: Sales Data Q4 2023",
            "data": {...}
        }
    ],
    "annotations": [...]
}
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import tempfile
import time

try:
    from pdf2image import convert_from_path
    from PIL import Image, ImageDraw, ImageFont
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    convert_from_path = None
    Image = None
    ImageDraw = None
    ImageFont = None

from claude_coms.core.modules.base_module import BaseModule
from claude_coms.core.modules.screenshot_module import ScreenshotModule


class PDFNavigatorModule(BaseModule):
    """Module for PDF navigation, screenshot, and table extraction."""
    
    def __init__(self):
        """Initialize PDF navigator module."""
        super().__init__("pdf_navigator", "PDF Navigation and Analysis Module")
        self.screenshot_module = ScreenshotModule()
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF navigation requests."""
        if not PDF_SUPPORT:
            return {
                "success": False,
                "error": "PDF support not available. Install with: pip install pdf2image pillow"
            }
        
        action = data.get("action", "navigate")
        
        if action == "navigate":
            return await self._navigate_pdf(data)
        elif action == "extract_tables":
            return await self._extract_tables_from_page(data)
        elif action == "annotate":
            return await self._annotate_page(data)
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
    
    async def _navigate_pdf(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to a specific PDF page and optionally extract content."""
        pdf_path = data.get("file")
        page_num = data.get("page", 1)
        extract_tables = data.get("extract_tables", False)
        annotate = data.get("annotate", False)
        
        if not pdf_path:
            return {"success": False, "error": "No PDF file specified"}
        
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            return {"success": False, "error": f"PDF file not found: {pdf_path}"}
        
        try:
            # Convert specific page to image
            images = convert_from_path(
                pdf_path, 
                first_page=page_num, 
                last_page=page_num,
                dpi=150  # Good balance between quality and performance
            )
            
            if not images:
                return {"success": False, "error": f"Could not render page {page_num}"}
            
            # Save screenshot
            screenshot_path = pdf_file.parent / f"{pdf_file.stem}_page_{page_num}.png"
            images[0].save(screenshot_path, 'PNG')
            
            result = {
                "success": True,
                "page": page_num,
                "screenshot": str(screenshot_path),
                "dimensions": {
                    "width": images[0].width,
                    "height": images[0].height
                }
            }
            
            # Extract tables if requested
            if extract_tables:
                table_result = await self._extract_tables_from_image(
                    screenshot_path, page_num
                )
                result["tables"] = table_result.get("tables", [])
            
            # Annotate if requested
            if annotate and "tables" in result:
                annotated_path = await self._annotate_image_with_tables(
                    screenshot_path, result["tables"]
                )
                if annotated_path:
                    result["annotated_screenshot"] = str(annotated_path)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"PDF processing error: {str(e)}"
            }
    
    async def _extract_tables_from_image(self, image_path: Path, page_num: int) -> Dict[str, Any]:
        """Use AI to extract tables from PDF page image."""
        # Use screenshot module to analyze the image
        analysis_result = await self.screenshot_module.process({
            "action": "describe",
            "file": str(image_path),
            "prompt": """Analyze this PDF page and identify all tables present.
For each table found:
1. Describe its location on the page
2. Extract the table title if visible, or infer one from surrounding context (prefix with "Inferred:" if inferred)
3. Extract the table data in a structured format (headers and rows)
4. Note any captions or footnotes associated with the table

Return the analysis in this JSON format:
{
    "tables": [
        {
            "title": "Table Title or Inferred: Description",
            "location": "top-left/center/bottom-right etc",
            "headers": ["Col1", "Col2", ...],
            "rows": [
                ["data1", "data2", ...],
                ...
            ],
            "caption": "optional caption",
            "footnotes": ["optional footnotes"]
        }
    ],
    "table_count": N,
    "page_context": "Brief description of what this page contains"
}"""
        })
        
        if not analysis_result.get("success"):
            return {"tables": [], "error": "Failed to analyze image"}
        
        try:
            # Parse the AI response to extract structured table data
            description = analysis_result.get("description", "")
            
            # Try to extract JSON from the description
            import re
            json_match = re.search(r'\{.*\}', description, re.DOTALL)
            if json_match:
                table_data = json.loads(json_match.group())
                return {
                    "success": True,
                    "page": page_num,
                    "tables": table_data.get("tables", []),
                    "table_count": table_data.get("table_count", 0),
                    "page_context": table_data.get("page_context", "")
                }
            else:
                # Fallback: return raw description if JSON parsing fails
                return {
                    "success": True,
                    "page": page_num,
                    "tables": [],
                    "raw_analysis": description
                }
                
        except json.JSONDecodeError:
            return {
                "success": True,
                "page": page_num,
                "tables": [],
                "raw_analysis": description
            }
    
    async def _annotate_image_with_tables(self, image_path: Path, tables: List[Dict]) -> Optional[Path]:
        """Annotate image with table boundaries and labels."""
        if not tables:
            return None
            
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            # Simple annotation with rectangles and labels
            # In a real implementation, we'd use AI to detect exact table boundaries
            for i, table in enumerate(tables):
                # Draw a simple border and label for demonstration
                # Real implementation would detect actual table boundaries
                title = table.get("title", f"Table {i+1}")
                
                # Draw title at estimated position
                draw.text((10, 50 + i * 100), title, fill="red")
            
            # Save annotated image
            annotated_path = image_path.parent / f"{image_path.stem}_annotated.png"
            img.save(annotated_path)
            
            return annotated_path
            
        except Exception as e:
            print(f"Annotation error: {e}")
            return None
    
    async def _extract_tables_from_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tables from a specific PDF page."""
        # First navigate to the page
        nav_result = await self._navigate_pdf({
            "file": data.get("file"),
            "page": data.get("page", 1),
            "extract_tables": True,
            "annotate": data.get("annotate", False)
        })
        
        if nav_result.get("success"):
            return {
                "success": True,
                "page": nav_result.get("page"),
                "tables": nav_result.get("tables", []),
                "screenshot": nav_result.get("screenshot"),
                "annotated_screenshot": nav_result.get("annotated_screenshot")
            }
        else:
            return nav_result
    
    async def _annotate_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a PDF page with custom annotations."""
        # For now, this is a placeholder for more advanced annotation features
        return {
            "success": False,
            "error": "Custom annotation not yet implemented"
        }


# Test the module
if __name__ == "__main__":
    import asyncio
    
    async def test_pdf_navigation():
        """Test PDF navigation with a real PDF."""
        module = PDFNavigatorModule()
        
        # Test 1: Navigate to page 42 and extract tables
        print("Test 1: Navigate to page 42 and look for tables")
        test_pdf = "/path/to/test.pdf"  # Replace with actual PDF path
        
        result = await module.process({
            "action": "navigate",
            "file": test_pdf,
            "page": 42,
            "extract_tables": True,
            "annotate": True
        })
        
        if result.get("success"):
            print(f"✓ Successfully navigated to page {result['page']}")
            print(f"  Screenshot: {result['screenshot']}")
            print(f"  Tables found: {len(result.get('tables', []))}")
            
            for i, table in enumerate(result.get("tables", [])):
                print(f"\n  Table {i+1}: {table.get('title', 'Untitled')}")
                if "headers" in table:
                    print(f"    Headers: {table['headers']}")
                if "rows" in table and table["rows"]:
                    print(f"    Rows: {len(table['rows'])}")
        else:
            print(f"✗ Navigation failed: {result.get('error')}")
        
        return result
    
    # Run the test
    asyncio.run(test_pdf_navigation())