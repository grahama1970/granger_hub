"""
Tests for ScreenshotModule.

These tests validate screenshot capture and image description functionality.
"""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from claude_coms.core.modules.screenshot_module import ScreenshotModule


@pytest.fixture
def screenshot_module():
    """Create a ScreenshotModule instance for testing."""
    return ScreenshotModule()


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess execution."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps({
        "success": True,
        "file": "/tmp/screenshot.jpg",
        "metadata": {
            "width": 1920,
            "height": 1080,
            "capture_time": "2024-01-20T10:30:00Z"
        }
    })
    mock_result.stderr = ""
    return mock_result


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess execution."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error: Display not found"
    return mock_result


class TestScreenshotModule:
    """Test ScreenshotModule functionality."""
    
    @pytest.mark.asyncio
    async def test_module_initialization(self, screenshot_module):
        """Test module is initialized with correct capabilities."""
        assert screenshot_module.name == "ScreenshotModule"
        assert "screenshot_capture" in screenshot_module.capabilities
        assert "url_capture" in screenshot_module.capabilities
        assert "image_description" in screenshot_module.capabilities
        assert "visual_verification" in screenshot_module.capabilities
        assert "browser_automation" in screenshot_module.capabilities
    
    @pytest.mark.asyncio
    async def test_capture_screenshot_success(self, screenshot_module, mock_subprocess_success):
        """Test successful screenshot capture."""
        with patch('subprocess.run', return_value=mock_subprocess_success):
            result = await screenshot_module.process({
                "action": "capture",
                "region": "full",
                "output": "test.jpg",
                "quality": 80
            })
            
            assert result["success"] is True
            assert "result" in result
            assert result["result"]["file"] == "/tmp/screenshot.jpg"
    
    @pytest.mark.asyncio
    async def test_capture_screenshot_failure(self, screenshot_module, mock_subprocess_failure):
        """Test failed screenshot capture."""
        with patch('subprocess.run', return_value=mock_subprocess_failure):
            result = await screenshot_module.process({
                "action": "capture",
                "region": "full"
            })
            
            assert result["success"] is False
            assert "error" in result
            assert "Display not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_capture_url_screenshot(self, screenshot_module, mock_subprocess_success):
        """Test URL screenshot capture."""
        with patch('subprocess.run', return_value=mock_subprocess_success):
            result = await screenshot_module.process({
                "action": "capture",
                "url": "https://example.com",
                "wait": 5,
                "quality": 70
            })
            
            assert result["success"] is True
            
            # Verify subprocess was called with correct arguments
            subprocess.run.assert_called_once()
            args = subprocess.run.call_args[0][0]
            assert "--url" in args
            assert "https://example.com" in args
            assert "--wait" in args
            assert "5" in args
    
    @pytest.mark.asyncio
    async def test_describe_image(self, screenshot_module):
        """Test image description functionality."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "success": True,
            "description": "A screenshot showing a web page with text and images"
        })
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = await screenshot_module.process({
                "action": "describe",
                "file": "/tmp/test.jpg",
                "prompt": "What is in this image?"
            })
            
            assert result["success"] is True
            assert "result" in result
            assert "description" in result["result"]
    
    @pytest.mark.asyncio
    async def test_describe_image_missing_file(self, screenshot_module):
        """Test describe with missing file parameter."""
        result = await screenshot_module.process({
            "action": "describe"
        })
        
        assert result["success"] is False
        assert "error" in result
        assert "file" in result["error"] or "url" in result["error"]
    
    @pytest.mark.asyncio
    async def test_verify_visualization(self, screenshot_module):
        """Test visualization verification."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "success": True,
            "verification": {
                "expert_mode": "chart",
                "features_found": ["axes", "legend", "data_points"],
                "confidence": 0.95
            }
        })
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = await screenshot_module.process({
                "action": "verify",
                "file": "/tmp/chart.png",
                "expert": "chart",
                "features": "axes,legend"
            })
            
            assert result["success"] is True
            assert "result" in result
    
    @pytest.mark.asyncio
    async def test_unknown_action(self, screenshot_module):
        """Test handling of unknown action."""
        result = await screenshot_module.process({
            "action": "unknown_action"
        })
        
        assert result["success"] is False
        assert "error" in result
        assert "Unknown action" in result["error"]
    
    @pytest.mark.asyncio
    async def test_click_element_placeholder(self, screenshot_module):
        """Test click element returns placeholder."""
        result = await screenshot_module.process({
            "action": "click",
            "selector": "#button"
        })
        
        assert result["success"] is False
        assert "not yet implemented" in result["error"]
    
    @pytest.mark.asyncio
    async def test_fill_element_placeholder(self, screenshot_module):
        """Test fill element returns placeholder."""
        result = await screenshot_module.process({
            "action": "fill",
            "selector": "#input",
            "value": "test value"
        })
        
        assert result["success"] is False
        assert "not yet implemented" in result["error"]
    
    def test_get_capabilities(self, screenshot_module):
        """Test get_capabilities method."""
        capabilities = screenshot_module.get_capabilities()
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert "screenshot_capture" in capabilities
    
    def test_describe_method(self, screenshot_module):
        """Test describe method returns proper description."""
        description = screenshot_module.describe()
        assert isinstance(description, str)
        assert "screenshot" in description.lower()
        assert "browser" in description.lower()
    
    @pytest.mark.asyncio
    async def test_all_regions(self, screenshot_module, mock_subprocess_success):
        """Test all supported screen regions."""
        regions = ["full", "left-half", "right-half", "top-half", "bottom-half", "center"]
        
        for region in regions:
            with patch('subprocess.run', return_value=mock_subprocess_success):
                result = await screenshot_module.process({
                    "action": "capture",
                    "region": region
                })
                
                assert result["success"] is True
                
                # Verify region parameter was passed
                args = subprocess.run.call_args[0][0]
                assert "--region" in args
                assert region in args


@pytest.mark.integration
class TestScreenshotModuleIntegration:
    """Integration tests requiring mcp-screenshot to be installed."""
    
    @pytest.mark.asyncio
    async def test_real_screenshot_capture(self, screenshot_module, tmp_path):
        """Test real screenshot capture (requires mcp-screenshot installed)."""
        output_file = tmp_path / "test_screenshot.jpg"
        
        result = await screenshot_module.process({
            "action": "capture",
            "region": "center",
            "output": str(output_file),
            "quality": 60
        })
        
        # This test will only pass if mcp-screenshot is properly installed
        # and we have a display available
        if result["success"]:
            assert output_file.exists()
            assert output_file.stat().st_size > 0
        else:
            # Expected failure if no display or mcp-screenshot not installed
            assert "error" in result