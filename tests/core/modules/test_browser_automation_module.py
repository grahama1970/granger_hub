    """Create a BrowserAutomationModule instance for testing."""
    registry = ModuleRegistry()
    return BrowserAutomationModule(registry=registry)


class TestBrowserAutomationModule:
    """Test BrowserAutomationModule functionality with real Playwright."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

"""
Tests for BrowserAutomationModule.

These tests validate browser automation functionality using real Playwright.
NO MOCKS - Uses actual browser automation.
"""

import pytest
import asyncio
from pathlib import Path

from granger_hub.core.modules.browser_automation_module import BrowserAutomationModule
from granger_hub.core.modules.module_registry import ModuleRegistry


@pytest.fixture
def browser_module():
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_module_initialization(self, browser_module):
        """Test module is initialized with correct capabilities."""
        assert browser_module.name == "BrowserAutomationModule"
        assert "browser_navigation" in browser_module.capabilities
        assert "element_click" in browser_module.capabilities
        assert "form_fill" in browser_module.capabilities
        assert "screenshot_element" in browser_module.capabilities
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_start_stop(self, browser_module):
        """Test module start and stop lifecycle with real browser."""
        # Test that module starts without error
        await browser_module.start()
        
        # Test that module stops without error
        await browser_module.stop()
        
        # Verify browser resources are cleaned up
        assert browser_module._browser is None
        assert browser_module._context is None
        assert browser_module._page is None
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_navigate_action(self, browser_module):
        """Test navigation to a URL with real browser."""
        await browser_module.start()
        
        try:
            result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "wait_for": "networkidle",
                "timeout": 10000,
                "headless": True
            })
            
            assert result["success"] is True
            assert "example.com" in result["result"]["url"]
            assert "Example" in result["result"]["title"]
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_navigate_missing_url(self, browser_module):
        """Test navigation without URL fails."""
        await browser_module.start()
        
        try:
            result = await browser_module.process({
                "action": "navigate"
            })
            
            assert result["success"] is False
            assert "URL is required" in result["error"]
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_click_action(self, browser_module):
        """Test clicking an element with real browser."""
        await browser_module.start()
        
        try:
            # First navigate to a page
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Then try to click a link
            result = await browser_module.process({
                "action": "click",
                "selector": "a",  # Click first link
                "timeout": 5000
            })
            
            assert result["success"] is True
            assert result["result"]["clicked"] == "a"
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_fill_action(self, browser_module):
        """Test filling a form field with real browser."""
        await browser_module.start()
        
        try:
            # Navigate to a page with forms (httpbin.org has test forms)
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://httpbin.org/forms/post",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Fill a form field
            result = await browser_module.process({
                "action": "fill",
                "selector": "input[name='custname']",
                "value": "Test User",
                "timeout": 5000
            })
            
            assert result["success"] is True
            assert result["result"]["filled"] == "input[name='custname']"
            assert result["result"]["value"] == "Test User"
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_hover_action(self, browser_module):
        """Test hovering over an element with real browser."""
        await browser_module.start()
        
        try:
            # Navigate to a page
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Hover over a link
            result = await browser_module.process({
                "action": "hover",
                "selector": "a"
            })
            
            assert result["success"] is True
            assert result["result"]["hovered"] == "a"
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_screenshot_full_page(self, browser_module, tmp_path):
        """Test taking a full page screenshot with real browser."""
        await browser_module.start()
        
        try:
            # Navigate first
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Take screenshot
            screenshot_path = str(tmp_path / "page.png")
            result = await browser_module.process({
                "action": "screenshot",
                "output_path": screenshot_path
            })
            
            assert result["success"] is True
            assert result["result"]["screenshot"] == screenshot_path
            assert Path(screenshot_path).exists()
            assert Path(screenshot_path).stat().st_size > 0
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_screenshot_element(self, browser_module, tmp_path):
        """Test taking a screenshot of specific element with real browser."""
        await browser_module.start()
        
        try:
            # Navigate first
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Take element screenshot
            screenshot_path = str(tmp_path / "element.jpg")
            result = await browser_module.process({
                "action": "screenshot",
                "selector": "h1",
                "output_path": screenshot_path
            })
            
            assert result["success"] is True
            assert result["result"]["selector"] == "h1"
            assert Path(screenshot_path).exists()
            assert Path(screenshot_path).stat().st_size > 0
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_evaluate_javascript(self, browser_module):
        """Test evaluating JavaScript in page context with real browser."""
        await browser_module.start()
        
        try:
            # Navigate first
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Evaluate JavaScript
            result = await browser_module.process({
                "action": "evaluate",
                "script": "document.querySelectorAll('a').length"
            })
            
            assert result["success"] is True
            assert isinstance(result["result"]["value"], int)
            assert result["result"]["value"] > 0  # Example.com has at least one link
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_wait_for_selector(self, browser_module):
        """Test waiting for a selector with real browser."""
        await browser_module.start()
        
        try:
            # Navigate first
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Wait for h1 element
            result = await browser_module.process({
                "action": "wait",
                "selector": "h1",
                "timeout": 5000
            })
            
            assert result["success"] is True
            assert result["result"]["found"] == "h1"
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_unknown_action(self, browser_module):
        """Test handling of unknown action."""
        result = await browser_module.process({
            "action": "unknown_action"
        })
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_headless_mode(self, browser_module):
        """Test browser runs in headless mode by default."""
        await browser_module.start()
        
        try:
            # Navigate in headless mode
            result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            
            assert result["success"] is True
            # In headless mode, we should still get results
            assert "example.com" in result["result"]["url"]
        finally:
            await browser_module.stop()
    
    def test_get_capabilities(self, browser_module):
        """Test get_capabilities method."""
        capabilities = browser_module.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert "browser_navigation" in capabilities
        assert "element_click" in capabilities
    
    def test_describe_method(self, browser_module):
        """Test describe method returns proper description."""
        description = browser_module.describe()
        assert isinstance(description, str)
        assert "browser" in description.lower()
        assert "playwright" in description.lower()


@pytest.mark.integration
@pytest.mark.slow
class TestBrowserAutomationModuleIntegration:
    """Integration tests for complex browser scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_complex_form_interaction(self, browser_module):
        """Test complex form interactions with real browser."""
        await browser_module.start()
        
        try:
            # Navigate to a form page
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://httpbin.org/forms/post",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Fill multiple fields
            fields = [
                ("input[name='custname']", "John Doe"),
                ("input[name='custtel']", "555-1234"),
                ("input[name='custemail']", "john@example.com")
            ]
            
            for selector, value in fields:
                result = await browser_module.process({
                    "action": "fill",
                    "selector": selector,
                    "value": value
                })
                assert result["success"] is True
            
            # Take a screenshot as proof
            screenshot_path = "/tmp/form_filled.png"
            screenshot_result = await browser_module.process({
                "action": "screenshot",
                "output_path": screenshot_path
            })
            assert screenshot_result["success"] is True
            
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_javascript_interaction(self, browser_module):
        """Test JavaScript execution and interaction with real browser."""
        await browser_module.start()
        
        try:
            # Navigate to a page
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            assert nav_result["success"] is True
            
            # Execute JavaScript to modify the page
            js_result = await browser_module.process({
                "action": "evaluate",
                "script": """
                    document.body.style.backgroundColor = 'red';
                    return window.getComputedStyle(document.body).backgroundColor;
                """
            })
            
            assert js_result["success"] is True
            # Should return the computed color value
            assert js_result["result"]["value"] is not None
            
        finally:
            await browser_module.stop()