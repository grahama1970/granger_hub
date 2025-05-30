"""
Marker Protocol Adapter for PDF Processing.

This adapter integrates with the Marker project for sophisticated PDF processing,
including table extraction, OCR, and AI-powered content analysis.

Dependencies:
- Marker project should be available at /home/graham/workspace/experiments/marker/
- Can communicate via CLI, MCP, or direct Python import

Sample input:
{
    "action": "extract_page", 
    "file_path": "document.pdf",
    "page": 42,
    "extract_tables": true,
    "claude_config": "tables_only"
}

Expected output:
{
    "success": true,
    "page": 42,
    "content": {...},
    "tables": [...],
    "metadata": {...}
}
"""

import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile

from claude_coms.core.adapters.base_adapter import ProtocolAdapter, AdapterConfig


class MarkerAdapter(ProtocolAdapter):
    """Adapter for Marker PDF processing system."""
    
    def __init__(self, config: AdapterConfig, marker_path: Optional[str] = None):
        """Initialize Marker adapter.
        
        Args:
            config: Adapter configuration
            marker_path: Path to Marker installation (defaults to standard location)
        """
        super().__init__(config)
        self.marker_path = Path(marker_path or "/home/graham/workspace/experiments/marker")
        # Try multiple possible CLI locations
        self.marker_cli = None
        cli_paths = [
            self.marker_path / "src" / "marker" / "cli" / "marker_cli.py",
            self.marker_path / "src" / "marker" / "cli" / "main.py",
            self.marker_path / "marker_cli.py"
        ]
        for cli_path in cli_paths:
            if cli_path.exists():
                self.marker_cli = cli_path
                break
        
        if not self.marker_cli:
            raise RuntimeError(f"Marker CLI not found in any expected location")
        
        self._validate_marker_installation()
    
    def _validate_marker_installation(self):
        """Validate that Marker is properly installed."""
        if not self.marker_path.exists():
            raise RuntimeError(f"Marker not found at {self.marker_path}")
        # CLI path already validated in __init__
    
    async def connect(self, **kwargs) -> bool:
        """Connect to Marker (validate installation)."""
        try:
            # Test Marker availability
            result = await self._run_marker_command(["--version"])
            if result.get("returncode") == 0:
                self._connected = True
                self._connection_time = time.time()
                return True
            return False
        except Exception:
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Marker."""
        self._connected = False
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to Marker for processing."""
        if not self._connected:
            raise RuntimeError("Adapter not connected")
        
        action = message.get("action", "extract")
        
        if action == "extract_page":
            return await self._extract_page(message)
        elif action == "extract_tables":
            return await self._extract_tables(message)
        elif action == "convert_full":
            return await self._convert_full(message)
        elif action == "check_resources":
            return await self._check_resources()
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
    
    async def receive(self, timeout: float = None) -> Dict[str, Any]:
        """Marker is command-based, not streaming."""
        return None
    
    async def _extract_page(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a specific page from PDF."""
        file_path = message.get("file_path")
        page_num = message.get("page", 1)
        extract_tables = message.get("extract_tables", False)
        claude_config = message.get("claude_config", "disabled")
        
        if not file_path:
            return {"success": False, "error": "No file_path provided"}
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.json"
            
            # Build Marker command
            cmd = [
                "extract",
                file_path,
                "--output-format", "json",
                "--output-path", str(output_path),
                "--start-page", str(page_num - 1),  # Marker uses 0-indexing
                "--max-pages", "1"
            ]
            
            if claude_config != "disabled":
                cmd.extend(["--claude-config", claude_config])
            
            start_time = time.time()
            result = await self._run_marker_command(cmd)
            latency_ms = (time.time() - start_time) * 1000
            
            if result["returncode"] == 0 and output_path.exists():
                # Read the output
                with open(output_path) as f:
                    marker_output = json.load(f)
                
                # Extract tables if requested
                tables = []
                if extract_tables and "blocks" in marker_output:
                    tables = self._extract_tables_from_blocks(marker_output["blocks"])
                
                return {
                    "success": True,
                    "page": page_num,
                    "content": marker_output,
                    "tables": tables,
                    "latency_ms": latency_ms,
                    "metadata": {
                        "extraction_method": "marker",
                        "claude_config": claude_config,
                        "page_count": marker_output.get("metadata", {}).get("page_count", 1)
                    }
                }
            else:
                return {
                    "success": False,
                    "error": result.get("stderr", "Unknown error"),
                    "latency_ms": latency_ms
                }
    
    async def _extract_tables(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only tables from PDF."""
        # Use extract_page with tables_only config
        message["claude_config"] = "tables_only"
        message["extract_tables"] = True
        return await self._extract_page(message)
    
    async def _convert_full(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Convert entire PDF document."""
        file_path = message.get("file_path")
        output_format = message.get("output_format", "markdown")
        claude_config = message.get("claude_config", "disabled")
        
        if not file_path:
            return {"success": False, "error": "No file_path provided"}
        
        # Build command
        cmd = [
            "extract", 
            file_path,
            "--output-format", output_format
        ]
        
        if claude_config != "disabled":
            cmd.extend(["--claude-config", claude_config])
        
        start_time = time.time()
        result = await self._run_marker_command(cmd)
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "success": result["returncode"] == 0,
            "output": result.get("stdout", ""),
            "error": result.get("stderr") if result["returncode"] != 0 else None,
            "latency_ms": latency_ms
        }
    
    async def _check_resources(self) -> Dict[str, Any]:
        """Check system resources for Marker."""
        cmd = ["check-resources"]
        result = await self._run_marker_command(cmd)
        
        if result["returncode"] == 0:
            try:
                resources = json.loads(result["stdout"])
                return {
                    "success": True,
                    "resources": resources
                }
            except json.JSONDecodeError:
                pass
        
        return {
            "success": False,
            "error": "Could not check resources"
        }
    
    async def _run_marker_command(self, args: List[str]) -> Dict[str, Any]:
        """Run a Marker CLI command."""
        # Full command with Python interpreter
        cmd = ["python", str(self.marker_cli)] + args
        
        # Run command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.marker_path)
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "returncode": process.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else ""
        }
    
    def _extract_tables_from_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Extract table data from Marker blocks."""
        tables = []
        
        for block in blocks:
            if block.get("type") == "Table":
                table_data = {
                    "title": block.get("title", ""),
                    "bbox": block.get("bbox", []),
                    "confidence": block.get("confidence", 0.0)
                }
                
                # Extract cells if available
                if "cells" in block:
                    headers = []
                    rows = []
                    
                    # Group cells by row
                    cells_by_row = {}
                    for cell in block["cells"]:
                        row_idx = cell.get("row", 0)
                        if row_idx not in cells_by_row:
                            cells_by_row[row_idx] = []
                        cells_by_row[row_idx].append(cell)
                    
                    # Sort rows
                    sorted_rows = sorted(cells_by_row.keys())
                    
                    # First row is usually headers
                    if sorted_rows:
                        header_row = cells_by_row[sorted_rows[0]]
                        headers = [cell.get("text", "") for cell in sorted(header_row, key=lambda x: x.get("col", 0))]
                        table_data["headers"] = headers
                        
                        # Rest are data rows
                        for row_idx in sorted_rows[1:]:
                            row_cells = cells_by_row[row_idx]
                            row_data = [cell.get("text", "") for cell in sorted(row_cells, key=lambda x: x.get("col", 0))]
                            rows.append(row_data)
                        
                        table_data["rows"] = rows
                
                # Check if title needs inference
                if not table_data["title"] and "context" in block:
                    # Marker might provide context for title inference
                    table_data["title"] = f"Inferred: {block['context']}"
                
                tables.append(table_data)
        
        return tables


# Test the adapter
if __name__ == "__main__":
    async def test_marker_adapter():
        """Test Marker adapter with real PDF."""
        config = AdapterConfig(name="marker-test", protocol="marker")
        adapter = MarkerAdapter(config)
        
        print("Testing Marker Adapter...")
        
        # Test connection
        connected = await adapter.connect()
        print(f"✓ Connected: {connected}")
        
        if connected:
            # Test page extraction
            test_pdf = "/path/to/test.pdf"  # Replace with actual PDF
            
            result = await adapter.send({
                "action": "extract_page",
                "file_path": test_pdf,
                "page": 42,
                "extract_tables": True,
                "claude_config": "tables_only"
            })
            
            if result.get("success"):
                print(f"✓ Extracted page {result['page']}")
                print(f"  Tables found: {len(result.get('tables', []))}")
                print(f"  Latency: {result.get('latency_ms', 0):.1f}ms")
                
                for i, table in enumerate(result.get("tables", [])):
                    print(f"\n  Table {i+1}: {table.get('title', 'Untitled')}")
                    if table.get("headers"):
                        print(f"    Headers: {table['headers']}")
                    if table.get("rows"):
                        print(f"    Rows: {len(table['rows'])}")
            else:
                print(f"✗ Extraction failed: {result.get('error')}")
            
            await adapter.disconnect()
    
    # Run test
    import asyncio
    asyncio.run(test_marker_adapter())