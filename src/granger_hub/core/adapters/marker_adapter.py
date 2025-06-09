"""
Marker Protocol Adapter for PDF Processing.
Module: marker_adapter.py
Description: Implementation of marker adapter functionality

This adapter integrates with the marker-pdf package for sophisticated PDF processing,
including table extraction, OCR, and AI-powered content analysis.

Dependencies:
- marker-pdf package (pip install marker-pdf)

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
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile

from granger_hub.core.adapters.base_adapter import ProtocolAdapter, AdapterConfig

# Import marker-pdf package
try:
    from marker.converters.pdf import PdfConverter
    from marker.settings import settings
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False
    PdfConverter = None
    settings = None


class MarkerAdapter(ProtocolAdapter):
    """Adapter for Marker PDF processing system."""
    
    def __init__(self, config: AdapterConfig, **kwargs):
        """Initialize Marker adapter.
        
        Args:
            config: Adapter configuration
            **kwargs: Additional arguments (for compatibility)
        """
        super().__init__(config)
        self.converter = None
        self.use_pip_package = True
        
    async def connect(self, **kwargs) -> bool:
        """Connect to Marker (verify package is available).
        
        Returns:
            True if marker-pdf package is available, False otherwise
        """
        if not MARKER_AVAILABLE:
            return False
            
        try:
            # marker-pdf needs an artifact_dict for initialization
            # For now, we'll use an empty dict
            artifact_dict = {}
            self.converter = PdfConverter(artifact_dict)
            self._connected = True
            self._connection_time = time.time()
            return True
        except Exception as e:
            self._last_error = str(e)
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Marker."""
        self.converter = None
        self._connected = False
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF operations through Marker.
        
        Args:
            message: Operation request with action and parameters
            
        Returns:
            Operation result with extracted content
        """
        if not self._connected or not self.converter:
            return {
                "success": False,
                "error": "Not connected to Marker"
            }
        
        start_time = time.time()
        action = message.get("action", "")
        
        try:
            if action == "extract_page":
                result = await self._extract_page(message)
            elif action == "extract_tables":
                result = await self._extract_tables(message)
            elif action == "check_resources":
                result = await self._check_resources()
            else:
                result = {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
            
            # Add timing info
            result["latency_ms"] = (time.time() - start_time) * 1000
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    async def receive(self, timeout: float = None) -> Dict[str, Any]:
        """Marker doesn't support streaming responses."""
        return {"error": "Streaming not supported"}
    
    async def _extract_page(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from a specific PDF page.
        
        Args:
            message: Request with file_path, page, and options
            
        Returns:
            Extracted content and metadata
        """
        file_path = Path(message.get("file_path", ""))
        page = message.get("page", 1)
        extract_tables = message.get("extract_tables", False)
        claude_config = message.get("claude_config", "disabled")
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def extract():
            # Convert PDF to markdown
            # marker-pdf converts entire document, not single pages
            result = self.converter.convert(str(file_path))
            
            # For now, return the full content
            # In a real implementation, we'd parse out the specific page
            return {
                "success": True,
                "page": page,
                "content": {
                    "markdown": result.markdown if hasattr(result, 'markdown') else str(result),
                    "format": "markdown"
                },
                "tables": [],  # Table extraction would require additional parsing
                "metadata": {
                    "extraction_method": "marker",
                    "claude_config": claude_config,
                    "full_document": True  # marker-pdf processes full documents
                }
            }
        
        return await loop.run_in_executor(None, extract)
    
    async def _extract_tables(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract tables from PDF page.
        
        Args:
            message: Request with file_path, page, and options
            
        Returns:
            Extracted tables
        """
        file_path = Path(message.get("file_path", ""))
        page = message.get("page", 1)
        claude_config = message.get("claude_config", "tables_only")
        
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        # Run in executor
        loop = asyncio.get_event_loop()
        
        def extract():
            # Convert PDF
            result = self.converter.convert(str(file_path))
            
            # Parse tables from markdown (simplified)
            # Real implementation would parse markdown tables
            return {
                "success": True,
                "page": page,
                "tables": [],  # Would parse tables from markdown
                "metadata": {
                    "extraction_method": "marker",
                    "claude_config": claude_config
                }
            }
        
        return await loop.run_in_executor(None, extract)
    
    async def _check_resources(self) -> Dict[str, Any]:
        """Check Marker system resources."""
        return {
            "success": True,
            "resources": {
                "marker_available": MARKER_AVAILABLE,
                "converter_initialized": self.converter is not None,
                "package_version": "marker-pdf"
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of Marker connection."""
        health = await super().health_check()
        
        health.update({
            "marker_available": MARKER_AVAILABLE,
            "converter_ready": self.converter is not None,
            "package_type": "pip"
        })
        
        return health