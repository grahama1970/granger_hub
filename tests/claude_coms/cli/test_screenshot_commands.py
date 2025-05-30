"""
Tests for screenshot and browser CLI commands.
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock, MagicMock
import json

from claude_coms.cli.claude_comm import app


runner = CliRunner()


class TestScreenshotCommand:
    """Test the screenshot CLI command."""
    
    def test_screenshot_help(self):
        """Test screenshot command help."""
        result = runner.invoke(app, ["screenshot", "--help"])
        assert result.exit_code == 0
        assert "screenshot" in result.stdout
        assert "--output" in result.stdout
        assert "--region" in result.stdout
        assert "--quality" in result.stdout
    
    @patch('claude_coms.core.modules.screenshot_module.ScreenshotModule')
    def test_screenshot_basic(self, mock_module_class):
        """Test basic screenshot capture."""
        # Create mock module instance
        mock_module = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {
                "file": "/tmp/screenshot.jpg"
            }
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, ["screenshot"])
        
        assert result.exit_code == 0
        assert "Screenshot saved" in result.stdout
        assert "/tmp/screenshot.jpg" in result.stdout
    
    @patch('claude_coms.core.modules.screenshot_module.ScreenshotModule')
    def test_screenshot_with_options(self, mock_module_class):
        """Test screenshot with all options."""
        mock_module = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {
                "file": "/tmp/custom.jpg"
            }
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "screenshot",
            "--output", "custom.jpg",
            "--region", "center",
            "--quality", "85"
        ])
        
        assert result.exit_code == 0
        
        # Verify process was called with correct parameters
        mock_module.process.assert_called_once()
        call_args = mock_module.process.call_args[0][0]
        assert call_args["output"] == "custom.jpg"
        assert call_args["region"] == "center"
        assert call_args["quality"] == 85
    
    @patch('claude_coms.core.modules.screenshot_module.ScreenshotModule')
    def test_screenshot_url(self, mock_module_class):
        """Test screenshot of URL."""
        mock_module = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {
                "file": "/tmp/website.jpg"
            }
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "screenshot",
            "--url", "https://example.com",
            "--wait", "5"
        ])
        
        assert result.exit_code == 0
        
        # Verify URL parameters were passed
        call_args = mock_module.process.call_args[0][0]
        assert call_args["url"] == "https://example.com"
        assert call_args["wait"] == 5
    
    @patch('claude_coms.core.modules.screenshot_module.ScreenshotModule')
    def test_screenshot_with_description(self, mock_module_class):
        """Test screenshot with AI description."""
        mock_module = AsyncMock()
        mock_module.process = AsyncMock(side_effect=[
            # First call: capture
            {
                "success": True,
                "result": {
                    "file": "/tmp/screenshot.jpg"
                }
            },
            # Second call: describe
            {
                "success": True,
                "result": {
                    "description": "A screenshot showing a web page"
                }
            }
        ])
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "screenshot",
            "--describe",
            "--prompt", "What do you see?"
        ])
        
        assert result.exit_code == 0
        assert "Screenshot saved" in result.stdout
        assert "Description:" in result.stdout
        assert "A screenshot showing a web page" in result.stdout
    
    @patch('claude_coms.core.modules.screenshot_module.ScreenshotModule')
    def test_screenshot_failure(self, mock_module_class):
        """Test screenshot failure handling."""
        mock_module = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": False,
            "error": "Display not found"
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, ["screenshot"])
        
        assert result.exit_code == 1
        assert "Screenshot failed" in result.stdout
        assert "Display not found" in result.stdout


class TestBrowserCommand:
    """Test the browser CLI command."""
    
    def test_browser_help(self):
        """Test browser command help."""
        result = runner.invoke(app, ["browser", "--help"])
        assert result.exit_code == 0
        assert "browser" in result.stdout
        assert "navigate" in result.stdout
        assert "click" in result.stdout
        assert "--url" in result.stdout
        assert "--selector" in result.stdout
    
    @patch('claude_coms.core.modules.browser_automation_module.BrowserAutomationModule')
    def test_browser_navigate(self, mock_module_class):
        """Test browser navigate action."""
        mock_module = AsyncMock()
        mock_module.start = AsyncMock()
        mock_module.stop = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {
                "url": "https://example.com/",
                "title": "Example Domain"
            }
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "browser", "navigate",
            "--url", "https://example.com"
        ])
        
        assert result.exit_code == 0
        assert "Action completed successfully" in result.stdout
        
        # Verify process was called correctly
        call_args = mock_module.process.call_args[0][0]
        assert call_args["action"] == "navigate"
        assert call_args["url"] == "https://example.com"
    
    @patch('claude_coms.core.modules.browser_automation_module.BrowserAutomationModule')
    def test_browser_click(self, mock_module_class):
        """Test browser click action."""
        mock_module = AsyncMock()
        mock_module.start = AsyncMock()
        mock_module.stop = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {
                "clicked": "#button",
                "url": "https://example.com/"
            }
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "browser", "click",
            "--selector", "#button"
        ])
        
        assert result.exit_code == 0
        assert "Action completed successfully" in result.stdout
    
    @patch('claude_coms.core.modules.browser_automation_module.BrowserAutomationModule')
    def test_browser_fill(self, mock_module_class):
        """Test browser fill action."""
        mock_module = AsyncMock()
        mock_module.start = AsyncMock()
        mock_module.stop = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {
                "filled": "#username",
                "value": "testuser"
            }
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "browser", "fill",
            "--selector", "#username",
            "--value", "testuser"
        ])
        
        assert result.exit_code == 0
        assert "Action completed successfully" in result.stdout
    
    @patch('claude_coms.core.modules.browser_automation_module.BrowserAutomationModule')
    def test_browser_screenshot(self, mock_module_class):
        """Test browser screenshot action."""
        mock_module = AsyncMock()
        mock_module.start = AsyncMock()
        mock_module.stop = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {
                "screenshot": "page.png",
                "url": "https://example.com/"
            }
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "browser", "screenshot",
            "--output", "page.png"
        ])
        
        assert result.exit_code == 0
        assert "Action completed successfully" in result.stdout
    
    @patch('claude_coms.core.modules.browser_automation_module.BrowserAutomationModule')
    def test_browser_navigate_missing_url(self, mock_module_class):
        """Test browser navigate without URL shows error."""
        mock_module = AsyncMock()
        mock_module.start = AsyncMock()
        mock_module.stop = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {}
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, ["browser", "navigate"])
        
        # The error should be shown in output
        assert "URL is required" in result.stdout
    
    @patch('claude_coms.core.modules.browser_automation_module.BrowserAutomationModule')
    def test_browser_headed_mode(self, mock_module_class):
        """Test browser in headed mode."""
        mock_module = AsyncMock()
        mock_module.start = AsyncMock()
        mock_module.stop = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": True,
            "result": {"url": "https://example.com/"}
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "browser", "navigate",
            "--url", "https://example.com",
            "--headed"
        ])
        
        assert result.exit_code == 0
        
        # Verify headless=False was passed
        call_args = mock_module.process.call_args[0][0]
        assert call_args["headless"] is False
    
    @patch('claude_coms.core.modules.browser_automation_module.BrowserAutomationModule')
    def test_browser_action_failure(self, mock_module_class):
        """Test browser action failure handling."""
        mock_module = AsyncMock()
        mock_module.start = AsyncMock()
        mock_module.stop = AsyncMock()
        mock_module.process = AsyncMock(return_value={
            "success": False,
            "error": "Element not found"
        })
        mock_module_class.return_value = mock_module
        
        result = runner.invoke(app, [
            "browser", "click",
            "--selector", "#missing"
        ])
        
        assert result.exit_code == 0  # CLI itself succeeds
        assert "Action failed" in result.stdout
        assert "Element not found" in result.stdout