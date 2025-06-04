"""
Screenshot Module for Claude Module Communicator.

This module provides screenshot capture and browser automation capabilities
by integrating with the mcp-screenshot package.

Links:
- mcp-screenshot: https://github.com/grahama1970/mcp-screenshot

Sample Input:
{
    "action": "capture",
    "region": "full",
    "output": "screenshot.jpg",
    "quality": 80
}

Expected Output:
{
    "success": True,
    "file": "/path/to/screenshot.jpg",
    "metadata": {
        "width": 1920,
        "height": 1080,
        "capture_time": "2024-01-20T10:30:00Z"
    }
}
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from granger_hub.core.modules.base_module import BaseModule


class ScreenshotModule(BaseModule):
    """Module for screenshot capture and browser automation."""
    
    def __init__(self, registry=None):
        """Initialize the ScreenshotModule."""
        super().__init__(
            name="ScreenshotModule",
            capabilities=[
                "screenshot_capture",
                "url_capture", 
                "image_description",
                "visual_verification",
                "browser_automation"
            ],
            input_schema={
                "action": {
                    "type": "string",
                    "enum": ["capture", "describe", "verify", "click", "fill"],
                    "description": "The action to perform"
                },
                "region": {
                    "type": "string",
                    "enum": ["full", "left-half", "right-half", "top-half", "bottom-half", "center"],
                    "description": "Screen region to capture",
                    "default": "full"
                },
                "url": {
                    "type": "string",
                    "description": "URL to capture (for web screenshots)"
                },
                "file": {
                    "type": "string", 
                    "description": "File path for describe/verify actions"
                },
                "output": {
                    "type": "string",
                    "description": "Output filename"
                },
                "quality": {
                    "type": "integer",
                    "minimum": 30,
                    "maximum": 90,
                    "default": 70,
                    "description": "JPEG quality"
                },
                "prompt": {
                    "type": "string",
                    "description": "Custom prompt for description/verification"
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for click/fill actions"
                },
                "value": {
                    "type": "string",
                    "description": "Value to fill in form fields"
                },
                "wait": {
                    "type": "integer",
                    "default": 3,
                    "description": "Wait time in seconds for dynamic content"
                }
            },
            output_schema={
                "success": {"type": "boolean"},
                "result": {"type": "object"},
                "error": {"type": "string"}
            },
            registry=registry
        )
        
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process screenshot and browser automation requests."""
        action = data.get("action", "capture")
        
        try:
            if action == "capture":
                return await self._capture_screenshot(data)
            elif action == "describe":
                return await self._describe_image(data)
            elif action == "verify":
                return await self._verify_visualization(data)
            elif action == "click":
                return await self._click_element(data)
            elif action == "fill":
                return await self._fill_element(data)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _capture_screenshot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Capture a screenshot using mcp-screenshot CLI."""
        cmd = ["mcp-screenshot", "--json", "capture"]
        
        # Add parameters
        if "region" in data:
            cmd.extend(["--region", data["region"]])
        if "url" in data:
            cmd.extend(["--url", data["url"]])
        if "output" in data:
            cmd.extend(["--output", data["output"]])
        if "quality" in data:
            cmd.extend(["--quality", str(data["quality"])])
        if "wait" in data:
            cmd.extend(["--wait", str(data["wait"])])
        
        # Execute command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            return {
                "success": True,
                "result": output
            }
        else:
            return {
                "success": False,
                "error": result.stderr or "Screenshot capture failed"
            }
    
    async def _describe_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Describe an image using AI."""
        cmd = ["mcp-screenshot", "--json", "describe"]
        
        if "file" in data:
            cmd.extend(["--file", data["file"]])
        elif "url" in data:
            cmd.extend(["--url", data["url"]])
        else:
            return {
                "success": False,
                "error": "Either 'file' or 'url' must be provided"
            }
        
        if "prompt" in data:
            cmd.extend(["--prompt", data["prompt"]])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            return {
                "success": True,
                "result": output
            }
        else:
            return {
                "success": False,
                "error": result.stderr or "Image description failed"
            }
    
    async def _verify_visualization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a visualization with expert mode."""
        target = data.get("file") or data.get("url")
        if not target:
            return {
                "success": False,
                "error": "Either 'file' or 'url' must be provided"
            }
        
        cmd = ["mcp-screenshot", "--json", "verify", target]
        
        if "expert" in data:
            cmd.extend(["--expert", data["expert"]])
        if "features" in data:
            cmd.extend(["--features", data["features"]])
        if "prompt" in data:
            cmd.extend(["--prompt", data["prompt"]])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            output = json.loads(result.stdout)
            return {
                "success": True,
                "result": output
            }
        else:
            return {
                "success": False,
                "error": result.stderr or "Verification failed"
            }
    
    async def _click_element(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Click an element on a web page (requires Playwright)."""
        # This would use a separate Playwright-based script
        # For now, return a placeholder
        return {
            "success": False,
            "error": "Click functionality not yet implemented. Use Playwright directly."
        }
    
    async def _fill_element(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a form field on a web page (requires Playwright)."""
        # This would use a separate Playwright-based script
        # For now, return a placeholder
        return {
            "success": False,
            "error": "Fill functionality not yet implemented. Use Playwright directly."
        }
    
    def get_capabilities(self) -> List[str]:
        """Return the capabilities of this module."""
        return self.capabilities
    
    def describe(self) -> str:
        """Return a description of this module."""
        return (
            "Screenshot and browser automation module that provides:\n"
            "- Screen capture (full screen or regions)\n"
            "- Web page screenshots\n"
            "- AI-powered image description\n"
            "- Visual verification with expert modes\n"
            "- Browser automation (click, fill - requires setup)"
        )


# Validation function
if __name__ == "__main__":
    import asyncio
    
    async def test_screenshot_module():
        """Test the ScreenshotModule with real examples."""
        module = ScreenshotModule()
        
        # Test 1: Capture full screen
        print("Test 1: Capturing full screen...")
        result = await module.process({
            "action": "capture",
            "region": "full",
            "output": "test_screenshot.jpg",
            "quality": 80
        })
        print(f"Result: {result}")
        
        # Test 2: Describe an image (if capture was successful)
        if result.get("success") and result.get("result", {}).get("file"):
            print("\nTest 2: Describing captured image...")
            desc_result = await module.process({
                "action": "describe",
                "file": result["result"]["file"],
                "prompt": "What can you see in this screenshot?"
            })
            print(f"Description: {desc_result}")
        
        # Test 3: Capture a website
        print("\nTest 3: Capturing a website...")
        web_result = await module.process({
            "action": "capture",
            "url": "https://example.com",
            "output": "example_website.jpg",
            "wait": 5
        })
        print(f"Web capture result: {web_result}")
        
        # Test capabilities
        print(f"\nModule capabilities: {module.get_capabilities()}")
        print(f"\nModule description:\n{module.describe()}")
    
    # Run the test
    asyncio.run(test_screenshot_module())