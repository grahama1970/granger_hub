"""
REST Protocol Adapter for Claude Module Communicator.

Enables communication with REST APIs using standard HTTP methods.
"""

import aiohttp
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime

from .base_adapter import ProtocolAdapter, AdapterConfig


class RESTAdapter(ProtocolAdapter):
    """
    Adapter for REST API communication.
    
    Handles HTTP requests/responses with proper error handling,
    retries, and connection management.
    """
    
    def __init__(self, config: AdapterConfig, base_url: str,
                 headers: Optional[Dict[str, str]] = None,
                 auth: Optional[aiohttp.BasicAuth] = None):
        """
        Initialize REST adapter.
        
        Args:
            config: Adapter configuration
            base_url: Base URL for API endpoints
            headers: Default headers for all requests
            auth: Authentication credentials
        """
        super().__init__(config)
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.auth = auth
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def connect(self, **kwargs) -> bool:
        """
        Establish connection to REST API.
        
        Creates HTTP session and optionally tests connectivity.
        """
        try:
            # Create session with timeout
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                auth=self.auth,
                timeout=timeout,
                connector=aiohttp.TCPConnector(
                    limit=100,  # Connection pool size
                    ttl_dns_cache=300  # DNS cache timeout
                )
            )
            
            # Test connectivity if test_endpoint provided
            test_endpoint = kwargs.get('test_endpoint', '/health')
            if test_endpoint:
                try:
                    async with self._session.get(f"{self.base_url}{test_endpoint}") as response:
                        if response.status < 500:  # Server is responding
                            self._connected = True
                            self._connection_time = datetime.now()
                            return True
                except aiohttp.ClientError:
                    # Endpoint doesn't exist but connection works
                    self._connected = True
                    self._connection_time = datetime.now()
                    return True
            else:
                # No test endpoint, assume connected
                self._connected = True
                self._connection_time = datetime.now()
                return True
                
        except Exception as e:
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close HTTP session and cleanup."""
        if self._session and not self._session.closed:
            await self._session.close()
            # Small delay to allow cleanup
            await asyncio.sleep(0.1)
        self._session = None
        self._connected = False
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send HTTP request.
        
        Args:
            message: Request details including:
                - method: HTTP method (GET, POST, etc.)
                - endpoint: API endpoint path
                - data: Request body (for POST/PUT)
                - params: Query parameters
                - headers: Additional headers
                
        Returns:
            Response with status, data, headers, and timing info
        """
        if not self._connected or not self._session:
            raise RuntimeError("Adapter not connected")
        
        # Extract request details
        method = message.get('method', 'GET').upper()
        endpoint = message.get('endpoint', '/')
        data = message.get('data')
        params = message.get('params')
        headers = message.get('headers', {})
        
        # Merge with default headers
        request_headers = {**self.headers, **headers}
        
        # Build full URL
        url = f"{self.base_url}{endpoint}"
        
        # Retry logic
        for attempt in range(self.config.retry_count):
            try:
                start_time = time.time()
                
                # Make request
                async with self._session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers
                ) as response:
                    # Calculate latency
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Get response data
                    response_data = None
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'application/json' in content_type:
                        response_data = await response.json()
                    elif 'text/' in content_type:
                        response_data = await response.text()
                    else:
                        # Binary data
                        response_data = await response.read()
                    
                    return {
                        'success': 200 <= response.status < 300,
                        'status_code': response.status,
                        'data': response_data,
                        'headers': dict(response.headers),
                        'latency_ms': latency_ms,
                        'url': str(response.url),
                        'method': method,
                        'attempt': attempt + 1
                    }
                    
            except aiohttp.ClientError as e:
                # Network errors, timeouts, etc.
                if attempt < self.config.retry_count - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    continue
                    
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'url': url,
                    'method': method,
                    'attempt': attempt + 1
                }
    
    async def send_binary(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send binary data via REST.
        
        Uses multipart/form-data for efficient binary transfer.
        """
        if not self._connected:
            raise RuntimeError("Adapter not connected")
        
        # Create form data
        form_data = aiohttp.FormData()
        
        # Add binary file
        filename = metadata.get('filename', 'data.bin')
        content_type = metadata.get('content_type', 'application/octet-stream')
        form_data.add_field('file', data, filename=filename, content_type=content_type)
        
        # Add metadata fields
        for key, value in metadata.items():
            if key not in ['filename', 'content_type']:
                form_data.add_field(key, str(value))
        
        # Send as multipart
        endpoint = metadata.get('endpoint', '/upload')
        
        start_time = time.time()
        async with self._session.post(
            f"{self.base_url}{endpoint}",
            data=form_data
        ) as response:
            latency_ms = (time.time() - start_time) * 1000
            
            response_data = await response.json()
            
            return {
                'success': response.status == 200,
                'status_code': response.status,
                'data': response_data,
                'latency_ms': latency_ms,
                'bytes_sent': len(data)
            }
    
    async def receive(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Receive data from REST API.
        
        For REST, this is typically used for long-polling or SSE.
        Returns None as REST is request-response based.
        """
        # REST is typically request-response, not push-based
        # Override in subclasses for SSE or WebSocket support
        return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check REST API health."""
        health = await super().health_check()
        
        if self._connected and self._session:
            # Try to get API health endpoint
            try:
                async with self._session.get(
                    f"{self.base_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    health['api_status'] = response.status
                    health['api_healthy'] = 200 <= response.status < 300
            except:
                health['api_healthy'] = False
        
        health['base_url'] = self.base_url
        health['session_closed'] = self._session.closed if self._session else True
        
        return health


# Example usage
async def example_rest_adapter():
    """Example of using RESTAdapter."""
    
    # Create adapter for JSONPlaceholder API
    config = AdapterConfig(name="jsonplaceholder", protocol="rest")
    adapter = RESTAdapter(
        config,
        base_url="https://jsonplaceholder.typicode.com",
        headers={"User-Agent": "ClaudeModuleCommunicator/1.0"}
    )
    
    async with adapter:
        # GET request
        result = await adapter.send({
            "method": "GET",
            "endpoint": "/posts/1"
        })
        print(f"GET Result: {result['data']['title']}")
        print(f"Latency: {result['latency_ms']}ms")
        
        # POST request
        result = await adapter.send({
            "method": "POST",
            "endpoint": "/posts",
            "data": {
                "title": "Test Post",
                "body": "This is a test",
                "userId": 1
            }
        })
        print(f"POST Result: ID={result['data']['id']}")


if __name__ == "__main__":
    asyncio.run(example_rest_adapter())