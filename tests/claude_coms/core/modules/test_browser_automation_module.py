"""
Tests for BrowserAutomationModule.

These tests validate browser automation functionality using Playwright.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from granger_hub.core.modules.browser_automation_module import BrowserAutomationModule


@pytest.fixture
def browser_module():
    """Create a BrowserAutomationModule instance for testing."""
    return BrowserAutomationModule()


@pytest.fixture
def mock_playwright():
    """Mock Playwright components."""
    # Create mock page
    mock_page = AsyncMock()
    mock_page.url = "https://example.com"
    mock_page.title = AsyncMock(return_value="Example Domain")
    mock_page.viewport_size = {"width": 1920, "height": 1080}
    mock_page.goto = AsyncMock()
    mock_page.click = AsyncMock()
    mock_page.fill = AsyncMock()
    mock_page.hover = AsyncMock()
    mock_page.screenshot = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value="test result")
    mock_page.wait_for_selector = AsyncMock()
    mock_page.query_selector = AsyncMock()
    mock_page.close = AsyncMock()
    
    # Create mock context
    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()
    
    # Create mock browser
    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    
    # Create mock chromium
    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)
    
    # Create mock playwright instance
    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.chromium = mock_chromium
    mock_playwright_instance.stop = AsyncMock()
    
    # Create mock async_playwright
    mock_async_playwright = AsyncMock()
    mock_async_playwright.start = AsyncMock(return_value=mock_playwright_instance)
    
    return {
        "async_playwright": mock_async_playwright,
        "playwright_instance": mock_playwright_instance,
        "browser": mock_browser,
        "context": mock_context,
        "page": mock_page
    }


class TestBrowserAutomationModule:
    """Test BrowserAutomationModule functionality."""
    
    @pytest.mark.asyncio
    async def test_module_initialization(self, browser_module):
        """Test module is initialized with correct capabilities."""
        assert browser_module.name == "BrowserAutomationModule"
        assert "browser_navigation" in browser_module.capabilities
        assert "element_click" in browser_module.capabilities
        assert "form_fill" in browser_module.capabilities
        assert "screenshot_element" in browser_module.capabilities
    
    @pytest.mark.asyncio
    async def test_start_stop(self, browser_module):
        """Test module start and stop lifecycle."""
        # Test that module starts without error
        await browser_module.start()
        
        # Test that module stops without error
        await browser_module.stop()
        
        # Verify browser resources are cleaned up
        assert browser_module._browser is None
        assert browser_module._context is None
        assert browser_module._page is None
    
    @pytest.mark.asyncio
    async def test_navigate_action(self, browser_module, mock_playwright):
        """Test navigation to a URL."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "wait_for": "networkidle",
                "timeout": 10000
            })
            
            assert result["success"] is True
            assert result["result"]["url"] == "https://example.com"
            assert result["result"]["title"] == "Example Domain"
            
            # Verify navigation was called
            mock_playwright["page"].goto.assert_called_once_with(
                "https://example.com",
                wait_until="networkidle",
                timeout=10000
            )
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_navigate_missing_url(self, browser_module, mock_playwright):
        """Test navigation without URL fails."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "navigate"
            })
            
            assert result["success"] is False
            assert "URL is required" in result["error"]
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_click_action(self, browser_module, mock_playwright):
        """Test clicking an element."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "click",
                "selector": "#submit-button",
                "timeout": 5000
            })
            
            assert result["success"] is True
            assert result["result"]["clicked"] == "#submit-button"
            
            # Verify wait and click were called
            mock_playwright["page"].wait_for_selector.assert_called_with(
                "#submit-button", 
                timeout=5000
            )
            mock_playwright["page"].click.assert_called_with("#submit-button")
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_fill_action(self, browser_module, mock_playwright):
        """Test filling a form field."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "fill",
                "selector": "#username",
                "value": "testuser",
                "timeout": 5000
            })
            
            assert result["success"] is True
            assert result["result"]["filled"] == "#username"
            assert result["result"]["value"] == "testuser"
            
            # Verify fill was called
            mock_playwright["page"].fill.assert_called_with("#username", "testuser")
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_hover_action(self, browser_module, mock_playwright):
        """Test hovering over an element."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "hover",
                "selector": ".dropdown-trigger"
            })
            
            assert result["success"] is True
            assert result["result"]["hovered"] == ".dropdown-trigger"
            
            # Verify hover was called
            mock_playwright["page"].hover.assert_called_with(".dropdown-trigger")
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_screenshot_full_page(self, browser_module, mock_playwright):
        """Test taking a full page screenshot."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "screenshot",
                "output_path": "page.png"
            })
            
            assert result["success"] is True
            assert result["result"]["screenshot"] == "page.png"
            
            # Verify screenshot was called with full_page
            mock_playwright["page"].screenshot.assert_called_with(
                path="page.png",
                type="png",
                full_page=True
            )
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_screenshot_element(self, browser_module, mock_playwright):
        """Test taking a screenshot of specific element."""
        # Create mock element
        mock_element = AsyncMock()
        mock_element.screenshot = AsyncMock()
        mock_playwright["page"].query_selector = AsyncMock(return_value=mock_element)
        
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "screenshot",
                "selector": "#content",
                "output_path": "element.jpg"
            })
            
            assert result["success"] is True
            assert result["result"]["selector"] == "#content"
            
            # Verify element screenshot was called
            mock_element.screenshot.assert_called_with(
                path="element.jpg",
                type="jpeg"
            )
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_evaluate_javascript(self, browser_module, mock_playwright):
        """Test evaluating JavaScript in page context."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "evaluate",
                "script": "document.querySelectorAll('a').length"
            })
            
            assert result["success"] is True
            assert result["result"]["value"] == "test result"
            
            # Verify evaluate was called
            mock_playwright["page"].evaluate.assert_called_with(
                "document.querySelectorAll('a').length"
            )
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_wait_for_selector(self, browser_module, mock_playwright):
        """Test waiting for a selector."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "wait",
                "selector": ".loading-complete",
                "timeout": 15000
            })
            
            assert result["success"] is True
            assert result["result"]["found"] == ".loading-complete"
            
            # Verify wait was called
            mock_playwright["page"].wait_for_selector.assert_called_with(
                ".loading-complete",
                timeout=15000
            )
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_unknown_action(self, browser_module):
        """Test handling of unknown action."""
        result = await browser_module.process({
            "action": "unknown_action"
        })
        
        assert result["success"] is False
        assert "Unknown action" in result["error"]
    
    @pytest.mark.asyncio
    async def test_headless_mode(self, browser_module, mock_playwright):
        """Test browser runs in headless mode by default."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            # Navigate to ensure browser is initialized
            await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            
            # Verify browser was launched with headless=True
            mock_playwright["playwright_instance"].chromium.launch.assert_called_with(
                headless=True
            )
            
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_headed_mode(self, browser_module, mock_playwright):
        """Test browser can run in headed mode."""
        with patch('granger_hub.core.modules.browser_automation_module.async_playwright', 
                  return_value=mock_playwright["async_playwright"]):
            await browser_module.start()
            
            # Navigate with headed mode
            await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": False
            })
            
            # Verify browser was launched with headless=False
            mock_playwright["playwright_instance"].chromium.launch.assert_called_with(
                headless=False
            )
            
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
    """Integration tests requiring Playwright to be installed."""
    
    @pytest.mark.asyncio
    async def test_real_browser_navigation(self, browser_module):
        """Test real browser navigation (requires Playwright installed)."""
        try:
            await browser_module.start()
            
            result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True,
                "wait_for": "networkidle"
            })
            
            if result["success"]:
                assert result["result"]["url"] == "https://example.com/"
                assert "Example" in result["result"]["title"]
            else:
                # Expected if Playwright not installed
                assert "not installed" in result["error"].lower()
            
        finally:
            await browser_module.stop()
    
    @pytest.mark.asyncio
    async def test_real_browser_screenshot(self, browser_module, tmp_path):
        """Test real browser screenshot (requires Playwright installed)."""
        try:
            await browser_module.start()
            
            # Navigate first
            nav_result = await browser_module.process({
                "action": "navigate",
                "url": "https://example.com",
                "headless": True
            })
            
            if nav_result["success"]:
                # Take screenshot
                output_file = tmp_path / "browser_test.png"
                result = await browser_module.process({
                    "action": "screenshot",
                    "output_path": str(output_file)
                })
                
                if result["success"]:
                    assert output_file.exists()
                    assert output_file.stat().st_size > 0
            
        finally:
            await browser_module.stop()