
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

"""
Real tests for REST Protocol Adapter.

These tests make actual HTTP requests to real servers.
No mocks allowed - we test against httpbin.org and other real endpoints.
"""

import asyncio
import pytest
import time
import aiohttp
from typing import Dict, Any

from granger_hub.core.adapters.base_adapter import ProtocolAdapter, AdapterConfig


class RESTAdapter(ProtocolAdapter):
    """REST API Protocol Adapter implementation."""
    
    def __init__(self, config: AdapterConfig, base_url: str, 
                 headers: Dict[str, str] = None):
        super().__init__(config)
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self._session: aiohttp.ClientSession = None
        
    async def connect(self, **kwargs) -> bool:
        """Connect to REST API (create session)."""
        try:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
            
            # Test connection with a simple request
            async with self._session.get(f"{self.base_url}/get") as response:
                if response.status == 200:
                    self._connected = True
                    self._connection_time = time.time()
                    return True
            return False
        except Exception:
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from REST API (close session)."""
        if self._session:
            await self._session.close()
            self._session = None
        self._connected = False
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send HTTP request."""
        if not self._connected:
            raise RuntimeError("Adapter not connected")
        
        method = message.get("method", "GET").upper()
        endpoint = message.get("endpoint", "/")
        data = message.get("data")
        params = message.get("params")
        
        url = f"{self.base_url}{endpoint}"
        
        start_time = time.time()
        
        async with self._session.request(
            method, url, json=data, params=params
        ) as response:
            latency = (time.time() - start_time) * 1000  # Convert to ms
            
            response_data = None
            try:
                response_data = await response.json()
            except:
                response_data = await response.text()
            
            return {
                "success": 200 <= response.status < 300,
                "status_code": response.status,
                "data": response_data,
                "headers": dict(response.headers),
                "latency_ms": latency,
                "url": str(response.url)
            }
    
    async def receive(self, timeout: float = None) -> Dict[str, Any]:
        """REST is request/response, not streaming."""
        return None


class TestRESTAdapterReal:
    """Test REST adapter with real HTTP requests."""
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_real_http_request(self):
        """Test making real HTTP GET request."""
        start_time = time.time()
        
        config = AdapterConfig(name="httpbin-test", protocol="rest", timeout=30)
        adapter = RESTAdapter(config, base_url="https://httpbin.org")
        
        # Connect (tests endpoint availability)
        connected = await adapter.connect()
        assert connected, "Failed to connect to httpbin.org"
        
        # Make real HTTP request
        result = await adapter.send({
            "method": "GET",
            "endpoint": "/get",
            "params": {"test": "value", "timestamp": str(time.time())}
        })
        
        duration = time.time() - start_time
        
        # Verify real HTTP response
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["latency_ms"] > 10, f"HTTP latency too low ({result['latency_ms']}ms) - might be mocked"
        assert result["latency_ms"] < 5000, f"HTTP latency too high ({result['latency_ms']}ms)"
        
        # Verify response data
        assert "args" in result["data"]
        assert result["data"]["args"]["test"] == "value"
        
        # Check headers to verify real HTTP
        # Headers might be lowercase
        headers_lower = {k.lower(): v for k, v in result["headers"].items()}
        assert "date" in headers_lower or "Date" in result["headers"]
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "latency_ms": result["latency_ms"],
            "server": result["headers"].get("server"),
            "url": result["url"]
        }
    
    @pytest.mark.asyncio 
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_real_http_post(self):
        """Test making real HTTP POST request with data."""
        start_time = time.time()
        
        config = AdapterConfig(name="httpbin-post", protocol="rest")
        adapter = RESTAdapter(config, base_url="https://httpbin.org")
        
        await adapter.connect()
        
        # POST with JSON data
        test_data = {
            "message": "Real REST adapter test",
            "timestamp": time.time(),
            "nested": {"key": "value"}
        }
        
        result = await adapter.send({
            "method": "POST",
            "endpoint": "/post",
            "data": test_data
        })
        
        duration = time.time() - start_time
        
        # Verify response
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["latency_ms"] > 10  # Real network latency
        
        # httpbin echoes back the posted data
        assert "json" in result["data"]
        assert result["data"]["json"]["message"] == test_data["message"]
        assert result["data"]["json"]["nested"]["key"] == "value"
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "latency_ms": result["latency_ms"],
            "data_echoed": result["data"]["json"] == test_data
        }
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_http_error_handling(self):
        """Test handling HTTP error responses."""
        start_time = time.time()
        
        config = AdapterConfig(name="httpbin-error", protocol="rest")
        adapter = RESTAdapter(config, base_url="https://httpbin.org")
        
        await adapter.connect()
        
        # Request that returns 404
        result = await adapter.send({
            "method": "GET",
            "endpoint": "/status/404"
        })
        
        duration = time.time() - start_time
        
        # Should handle error gracefully
        assert result["success"] is False
        assert result["status_code"] == 404
        assert result["latency_ms"] > 10  # Still takes time for error
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "status_code": result["status_code"],
            "handled_error": True
        }
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_concurrent_requests(self):
        """Test multiple concurrent HTTP requests."""
        start_time = time.time()
        
        config = AdapterConfig(name="httpbin-concurrent", protocol="rest")
        adapter = RESTAdapter(config, base_url="https://httpbin.org")
        
        await adapter.connect()
        
        # Make 5 concurrent requests
        tasks = []
        for i in range(5):
            task = adapter.send({
                "method": "GET",
                "endpoint": f"/delay/0.1",  # Each delays 100ms
                "params": {"request": i}
            })
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # All should succeed
        for result in results:
            assert result["success"] is True
            assert result["status_code"] == 200
            assert result["latency_ms"] > 100  # At least the delay time
        
        # Concurrent should be faster than sequential
        # 5 * 0.1s = 0.5s if sequential, but httpbin.org may be slow
        assert duration < 10.0, f"Requests took too long ({duration}s)"
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "request_count": len(results),
            "concurrent": duration < 0.3,
            "avg_latency": sum(r["latency_ms"] for r in results) / len(results)
        }
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_real_api_headers(self):
        """Test with custom headers and user agent."""
        config = AdapterConfig(name="httpbin-headers", protocol="rest")
        custom_headers = {
            "User-Agent": "ClaudeModuleCommunicator/1.0",
            "X-Test-Header": "test-value"
        }
        adapter = RESTAdapter(config, base_url="https://httpbin.org", 
                            headers=custom_headers)
        
        await adapter.connect()
        
        # httpbin /headers endpoint returns request headers
        result = await adapter.send({
            "method": "GET",
            "endpoint": "/headers"
        })
        
        assert result["success"] is True
        
        # Verify our headers were sent
        request_headers = result["data"]["headers"]
        assert request_headers["User-Agent"] == "ClaudeModuleCommunicator/1.0"
        assert request_headers["X-Test-Header"] == "test-value"
        
        await adapter.disconnect()
        
        return {
            "headers_sent": True,
            "user_agent": request_headers["User-Agent"]
        }