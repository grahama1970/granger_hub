"""
Browser Automation Module for Granger Hub.
Module: browser_automation_module.py

This module provides Playwright-based browser automation capabilities
including clicking elements, filling forms, and navigating web pages.

Links:
- Playwright Documentation: https://playwright.dev/python/

Sample Input:
{
    "action": "navigate",
    "url": "https://example.com",
    "wait_for": "networkidle"
}

Expected Output:
{
    "success": True,
    "page_title": "Example Domain",
    "url": "https://example.com/"
}
"""

from typing import Dict, Any, Optional, List
import asyncio
from pathlib import Path

from granger_hub.core.modules.base_module import BaseModule

# Lazy import to make Playwright optional
playwright = None
async_playwright = None


def _ensure_playwright():
    """Ensure Playwright is available."""
    global playwright, async_playwright
    if playwright is None:
        try:
            from playwright import async_api
            playwright = async_api
            async_playwright = async_api.async_playwright
        except ImportError:
            raise ImportError(
                "Playwright is not installed. Install with: pip install playwright && playwright install"
            )


class BrowserAutomationModule(BaseModule):
    """Module for browser automation using Playwright."""
    
    def __init__(self, registry=None):
        """Initialize the BrowserAutomationModule."""
        # Store schemas as instance attributes BEFORE calling super().__init__
        self.input_schema = {
            "action": {
                "type": "string",
                "enum": ["navigate", "click", "fill", "hover", "screenshot", "evaluate", "wait"],
                "description": "The browser action to perform"
            },
            "url": {
                "type": "string",
                "description": "URL to navigate to"
            },
            "selector": {
                "type": "string",
                "description": "CSS selector for the target element"
            },
            "value": {
                "type": "string",
                "description": "Value to fill in form fields"
            },
            "script": {
                "type": "string",
                "description": "JavaScript to evaluate in page context"
            },
            "wait_for": {
                "type": "string",
                "enum": ["load", "domcontentloaded", "networkidle"],
                "default": "load",
                "description": "Wait condition for navigation"
            },
            "timeout": {
                "type": "integer",
                "default": 30000,
                "description": "Timeout in milliseconds"
            },
            "output_path": {
                "type": "string",
                "description": "Path to save screenshot"
            },
            "headless": {
                "type": "boolean",
                "default": True,
                "description": "Run browser in headless mode"
            }
        }
        self.output_schema = {
            "success": {"type": "boolean"},
            "result": {"type": "object"},
            "error": {"type": "string"}
        }
        
        # Now call super().__init__ after schemas are set
        super().__init__(
            name="BrowserAutomationModule",
            system_prompt="I am a browser automation module that can navigate websites, click elements, fill forms, take screenshots, and execute JavaScript.",
            capabilities=[
                "browser_navigation",
                "element_click",
                "form_fill",
                "element_hover",
                "screenshot_element",
                "page_evaluate",
                "wait_for_selector"
            ],
            registry=registry
        )
        
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
    
    async def start(self):
        """Start the browser automation module."""
        _ensure_playwright()
    
    async def stop(self):
        """Stop the browser automation module and cleanup."""
        await self._cleanup_browser()
    
    async def _cleanup_browser(self):
        """Clean up browser resources."""
        if self._page:
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Return the input schema for this module."""
        return self.input_schema
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Return the output schema for this module."""
        return self.output_schema
    
    async def _ensure_browser(self, headless: bool = True):
        """Ensure browser is initialized."""
        if not self._browser:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=headless)
            self._context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self._page = await self._context.new_page()
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process browser automation requests."""
        action = data.get("action", "navigate")
        headless = data.get("headless", True)
        
        try:
            await self._ensure_browser(headless)
            
            if action == "navigate":
                return await self._navigate(data)
            elif action == "click":
                return await self._click(data)
            elif action == "fill":
                return await self._fill(data)
            elif action == "hover":
                return await self._hover(data)
            elif action == "screenshot":
                return await self._screenshot(data)
            elif action == "evaluate":
                return await self._evaluate(data)
            elif action == "wait":
                return await self._wait_for_selector(data)
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
    
    async def _navigate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to a URL."""
        url = data.get("url")
        if not url:
            return {"success": False, "error": "URL is required"}
        
        wait_for = data.get("wait_for", "load")
        timeout = data.get("timeout", 30000)
        
        await self._page.goto(url, wait_until=wait_for, timeout=timeout)
        
        return {
            "success": True,
            "result": {
                "url": self._page.url,
                "title": await self._page.title(),
                "viewport": self._page.viewport_size
            }
        }
    
    async def _click(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Click an element."""
        selector = data.get("selector")
        if not selector:
            return {"success": False, "error": "Selector is required"}
        
        timeout = data.get("timeout", 30000)
        
        # Wait for element and click
        await self._page.wait_for_selector(selector, timeout=timeout)
        await self._page.click(selector)
        
        return {
            "success": True,
            "result": {
                "clicked": selector,
                "url": self._page.url
            }
        }
    
    async def _fill(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a form field."""
        selector = data.get("selector")
        value = data.get("value", "")
        
        if not selector:
            return {"success": False, "error": "Selector is required"}
        
        timeout = data.get("timeout", 30000)
        
        # Wait for element and fill
        await self._page.wait_for_selector(selector, timeout=timeout)
        await self._page.fill(selector, value)
        
        return {
            "success": True,
            "result": {
                "filled": selector,
                "value": value,
                "url": self._page.url
            }
        }
    
    async def _hover(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hover over an element."""
        selector = data.get("selector")
        if not selector:
            return {"success": False, "error": "Selector is required"}
        
        timeout = data.get("timeout", 30000)
        
        # Wait for element and hover
        await self._page.wait_for_selector(selector, timeout=timeout)
        await self._page.hover(selector)
        
        return {
            "success": True,
            "result": {
                "hovered": selector,
                "url": self._page.url
            }
        }
    
    async def _screenshot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Take a screenshot of the page or element."""
        output_path = data.get("output_path", "screenshot.png")
        selector = data.get("selector")
        
        screenshot_options = {
            "path": output_path,
            "type": "png" if output_path.endswith(".png") else "jpeg"
        }
        
        if selector:
            # Screenshot specific element
            element = await self._page.query_selector(selector)
            if not element:
                return {"success": False, "error": f"Element not found: {selector}"}
            await element.screenshot(**screenshot_options)
        else:
            # Screenshot full page
            screenshot_options["full_page"] = True
            await self._page.screenshot(**screenshot_options)
        
        return {
            "success": True,
            "result": {
                "screenshot": output_path,
                "selector": selector,
                "url": self._page.url
            }
        }
    
    async def _evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate JavaScript in the page context."""
        script = data.get("script")
        if not script:
            return {"success": False, "error": "Script is required"}
        
        result = await self._page.evaluate(script)
        
        return {
            "success": True,
            "result": {
                "value": result,
                "url": self._page.url
            }
        }
    
    async def _wait_for_selector(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for a selector to appear."""
        selector = data.get("selector")
        if not selector:
            return {"success": False, "error": "Selector is required"}
        
        timeout = data.get("timeout", 30000)
        
        await self._page.wait_for_selector(selector, timeout=timeout)
        
        return {
            "success": True,
            "result": {
                "found": selector,
                "url": self._page.url
            }
        }
    
    def get_capabilities(self) -> List[str]:
        """Return the capabilities of this module."""
        return self.capabilities
    
    def describe(self) -> str:
        """Return a description of this module."""
        return (
            "Browser automation module using Playwright that provides:\n"
            "- Web page navigation\n"
            "- Element clicking and hovering\n"
            "- Form filling\n"
            "- Screenshot capture (full page or elements)\n"
            "- JavaScript evaluation\n"
            "- Waiting for elements\n"
            "- Supports headless and headed modes"
        )


# Validation function
if __name__ == "__main__":
    async def test_browser_automation():
        """Test the BrowserAutomationModule with real examples."""
        module = BrowserAutomationModule()
        await module.start()
        
        try:
            # Test 1: Navigate to a page
            print("Test 1: Navigating to example.com...")
            result = await module.process({
                "action": "navigate",
                "url": "https://example.com",
                "wait_for": "networkidle"
            })
            print(f"Navigation result: {result}")
            
            # Test 2: Take a screenshot
            print("\nTest 2: Taking screenshot...")
            screenshot_result = await module.process({
                "action": "screenshot",
                "output_path": "example_page.png"
            })
            print(f"Screenshot result: {screenshot_result}")
            
            # Test 3: Evaluate JavaScript
            print("\nTest 3: Evaluating JavaScript...")
            js_result = await module.process({
                "action": "evaluate",
                "script": "document.title"
            })
            print(f"JavaScript result: {js_result}")
            
            # Test 4: Navigate to a form page and fill it
            print("\nTest 4: Form interaction example...")
            # This would work on a real form page
            form_result = await module.process({
                "action": "navigate",
                "url": "https://www.google.com"
            })
            print(f"Form navigation result: {form_result}")
            
        finally:
            # Clean up
            await module.stop()
        
        # Test capabilities
        print(f"\nModule capabilities: {module.get_capabilities()}")
        print(f"\nModule description:\n{module.describe()}")
    
    # Run the test
    asyncio.run(test_browser_automation())