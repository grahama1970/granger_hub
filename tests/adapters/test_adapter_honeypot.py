"""
Honeypot tests for Protocol Adapters.

These tests are DESIGNED TO FAIL to verify our testing is real.
If these pass, it means our testing framework is not properly detecting fake tests.
"""

import asyncio
import pytest
import time
from typing import Dict, Any

from granger_hub.core.adapters.base_adapter import ProtocolAdapter, AdapterConfig


class InstantNetworkAdapter(ProtocolAdapter):
    """Fake adapter that responds instantly (impossible for real network)."""
    
    async def connect(self, **kwargs) -> bool:
        # Instant connection - impossible for real network
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        self._connected = False
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Instant response with 0ms latency - impossible
        return {
            "success": True,
            "data": "Instant response",
            "latency_ms": 0.0  # Impossible!
        }
    
    async def receive(self, timeout: float = None) -> Dict[str, Any]:
        # Instant receive
        return {"data": "Instant"}


class TestAdapterHoneypot:
    """Honeypot tests that MUST fail."""
    
    @pytest.mark.asyncio
    async def test_impossible_zero_latency(self):
        """
        HONEYPOT: Test that claims network calls have 0ms latency.
        This MUST fail - network calls always have latency.
        """
        config = AdapterConfig(name="honeypot", protocol="fake")
        adapter = InstantNetworkAdapter(config)
        
        # Time the "network" call
        start_time = time.time()
        await adapter.connect()
        result = await adapter.send({"test": "data"})
        duration = time.time() - start_time
        
        # These assertions should FAIL for real testing
        # Network calls cannot have 0ms latency
        # CORRECTED: We want this test to FAIL to prove testing is real
        assert result["latency_ms"] > 0, "HONEYPOT DETECTED: Zero latency is impossible!"
        assert duration > 0.001, f"HONEYPOT DETECTED: Operation completed too fast ({duration}s)!"
        
        # If we get here, the test is fake
        return {
            "HONEYPOT": "PASSED (BAD!)",
            "latency": result["latency_ms"],
            "duration": duration,
            "error": "This test should have failed!"
        }
    
    @pytest.mark.asyncio 
    async def test_impossible_concurrent_instant(self):
        """
        HONEYPOT: Test that claims 1000 operations complete instantly.
        This MUST fail - operations take time.
        """
        config = AdapterConfig(name="honeypot-concurrent", protocol="fake")
        adapter = InstantNetworkAdapter(config)
        
        await adapter.connect()
        
        # "Execute" 1000 operations
        start_time = time.time()
        tasks = []
        for i in range(1000):
            tasks.append(adapter.send({"id": i}))
        
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # These assertions should FAIL
        # 1000 operations cannot complete in microseconds
        # CORRECTED: We want this test to FAIL to prove testing is real
        assert duration > 0.1, f"HONEYPOT DETECTED: 1000 operations completed too fast ({duration}s)!"
        assert len(results) == 1000
        assert any(r["latency_ms"] > 0 for r in results), "HONEYPOT DETECTED: All operations had zero latency!"
        
        return {
            "HONEYPOT": "PASSED (BAD!)",
            "operations": 1000,
            "total_duration": duration,
            "error": "1000 operations completed instantly - impossible!"
        }
    
    @pytest.mark.asyncio
    async def test_impossible_data_transfer(self):
        """
        HONEYPOT: Test that claims 1GB transferred instantly.
        This MUST fail - data transfer takes time.
        """
        # Simulate transferring 1GB instantly
        data_size = 1024 * 1024 * 1024  # 1GB
        
        start_time = time.time()
        
        # "Transfer" the data
        fake_data = b"x" * data_size  # This alone should take time
        transfer_time = time.time() - start_time
        
        # These assertions should FAIL
        # Creating 1GB of data cannot be instant
        # CORRECTED: We want this test to FAIL to prove testing is real
        assert transfer_time > 0.01, f"HONEYPOT DETECTED: 1GB created too fast ({transfer_time}s)!"
        
        return {
            "HONEYPOT": "PASSED (BAD!)", 
            "data_size": data_size,
            "transfer_time": transfer_time,
            "error": "1GB created/transferred instantly - impossible!"
        }
    
    @pytest.mark.asyncio
    async def test_impossible_hardware_response(self):
        """
        HONEYPOT: Test that claims hardware responds in 0 nanoseconds.
        This MUST fail - hardware has physical delays.
        """
        # Simulate instant hardware response
        start_time = time.time()
        
        # "Read" from hardware
        hardware_data = {"sensor": 42, "timestamp": time.time()}
        
        response_time = time.time() - start_time
        
        # These assertions should FAIL
        # Hardware cannot respond in 0 time
        # CORRECTED: We want this test to FAIL to prove testing is real
        assert response_time > 0.0, f"HONEYPOT DETECTED: Hardware responded in zero time ({response_time}s)!"
        
        return {
            "HONEYPOT": "PASSED (BAD!)",
            "response_time": response_time,
            "error": "Hardware responded instantly - physically impossible!"
        }