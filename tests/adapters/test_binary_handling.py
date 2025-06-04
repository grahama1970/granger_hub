"""
Test Binary Data Handling.

Purpose: Validates binary data compression, streaming, and adapter integration
with realistic data sizes and transfer scenarios.
"""

import pytest
import asyncio
import time
import os
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import hashlib

from granger_hub.core.binary_handler import (
    BinaryDataHandler, BinaryFileHandler, CompressionMethod
)
from granger_hub.core.adapters import ProtocolAdapter, AdapterConfig
from granger_hub.core.adapters.binary_adapter_mixin import BinaryAdapterMixin


class MockBinaryAdapter(ProtocolAdapter, BinaryAdapterMixin):
    """Mock adapter for testing binary capabilities."""
    
    def __init__(self, config: AdapterConfig, **kwargs):
        # Extract binary-specific kwargs before passing to parent
        binary_kwargs = {}
        for key in ['binary_chunk_size', 'binary_compression']:
            if key in kwargs:
                binary_kwargs[key] = kwargs.pop(key)
        
        # Initialize ProtocolAdapter first
        ProtocolAdapter.__init__(self, config)
        # Then initialize BinaryAdapterMixin with binary-specific kwargs
        BinaryAdapterMixin.__init__(self, **binary_kwargs)
        
        self._messages = []
        self._connected = False
    
    async def connect(self, **kwargs) -> bool:
        await asyncio.sleep(0.01)  # Realistic delay
        self._connected = True
        return True
    
    async def disconnect(self) -> None:
        self._connected = False
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        # Simulate network latency based on data size
        if "data" in message:
            data_size = len(message.get("data", ""))
            await asyncio.sleep(data_size / (1024 * 1024 * 10))  # 10MB/s
        else:
            await asyncio.sleep(0.001)
        
        self._messages.append(message)
        return {"success": True, "message_id": len(self._messages)}
    
    async def receive(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        # For testing streaming receive
        if self._messages:
            return self._messages.pop(0)
        return None


class TestBinaryDataHandler:
    """Test core binary data handler."""
    
    @pytest.mark.asyncio
    async def test_compression_methods(self):
        """Test different compression methods with real data."""
        start_time = time.time()
        
        # Generate realistic test data (1MB of compressible data)
        # Random data doesn't compress well, use repetitive pattern
        test_data = (b"This is a test pattern that repeats. " * 1000) * 30  # ~1MB
        
        results = {}
        
        for method in CompressionMethod.available_methods():
            handler = BinaryDataHandler(compression_method=method)
            
            # Compress
            compress_start = time.time()
            compressed, metadata = await handler.compress(test_data)
            compress_time = time.time() - compress_start
            
            # Decompress
            decompress_start = time.time()
            decompressed = await handler.decompress(compressed, metadata)
            decompress_time = time.time() - decompress_start
            
            # Verify data integrity
            assert decompressed == test_data
            assert metadata["checksum"] == hashlib.sha256(test_data).hexdigest()
            
            results[method] = {
                "compression_ratio": metadata["compression_ratio"],
                "compress_time": compress_time,
                "decompress_time": decompress_time,
                "compressed_size": metadata["compressed_size"]
            }
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "compression_methods",
            "data_size_mb": 1.0,
            "methods_tested": len(results),
            "results": results,
            "duration_seconds": duration,
            "data_integrity_verified": True
        }
        print(f"\nTest Evidence: {evidence}")
        
        # Verify realistic compression ratios
        for method, result in results.items():
            if method != CompressionMethod.NONE:
                assert result["compression_ratio"] > 1.0  # Some compression achieved
    
    @pytest.mark.asyncio
    async def test_streaming_large_data(self):
        """Test streaming with large data."""
        start_time = time.time()
        
        # Generate 5MB of test data
        large_data = b"Test pattern " * (1024 * 1024 // 13 * 5)  # ~5MB
        
        handler = BinaryDataHandler(chunk_size=512 * 1024)  # 512KB chunks
        
        # Stream data
        chunks = []
        chunk_times = []
        
        async for chunk in handler.stream_chunks(large_data):
            chunk_start = time.time()
            chunks.append(chunk)
            chunk_times.append(time.time() - chunk_start)
            
            # Verify chunk structure
            assert "chunk_index" in chunk
            assert "total_chunks" in chunk
            assert "data" in chunk
            assert "progress" in chunk
        
        # Reassemble
        reassembled = await handler.reassemble_chunks(chunks)
        assert reassembled == large_data
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "streaming",
            "data_size_mb": len(large_data) / (1024 * 1024),
            "chunk_size_kb": 512,
            "total_chunks": len(chunks),
            "avg_chunk_time_ms": sum(chunk_times) / len(chunk_times) * 1000,
            "duration_seconds": duration,
            "reassembly_verified": True
        }
        print(f"\nTest Evidence: {evidence}")
        
        assert len(chunks) > 5  # Should have multiple chunks
        assert duration > 0.01  # Realistic timing


class TestBinaryFileHandler:
    """Test file-specific binary operations."""
    
    @pytest.mark.asyncio
    async def test_file_compression(self):
        """Test file compression and decompression."""
        start_time = time.time()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test_data.bin"
            test_content = os.urandom(500 * 1024)  # 500KB
            test_file.write_bytes(test_content)
            
            handler = BinaryFileHandler(compression_method=CompressionMethod.GZIP)
            
            # Compress file
            compressed, metadata = await handler.compress_file(test_file)
            
            # Verify metadata
            assert metadata["filename"] == "test_data.bin"
            assert metadata["file_size"] == 500 * 1024
            assert "file_modified" in metadata
            
            # Decompress to new file
            output_file = Path(tmpdir) / "decompressed.bin"
            await handler.decompress_to_file(compressed, metadata, output_file)
            
            # Verify content
            assert output_file.read_bytes() == test_content
            
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "file_compression",
            "file_size_kb": 500,
            "compression_ratio": metadata["compression_ratio"],
            "duration_seconds": duration,
            "file_integrity_verified": True
        }
        print(f"\nTest Evidence: {evidence}")


class TestBinaryAdapterMixin:
    """Test binary adapter mixin integration."""
    
    @pytest.mark.asyncio
    async def test_adapter_binary_compression(self):
        """Test adapter with binary compression."""
        start_time = time.time()
        
        config = AdapterConfig(name="binary_test", protocol="mock")
        adapter = MockBinaryAdapter(config, binary_compression=CompressionMethod.GZIP)
        
        async with adapter:
            # Send compressed binary data
            test_data = b"Compressible pattern " * 1000  # ~21KB
            metadata = {"content_type": "text/plain"}
            
            result = await adapter.send_binary_compressed(test_data, metadata)
            
            assert result["success"]
            assert "compression_stats" in result
            assert result["compression_stats"]["compression_ratio"] > 1.0
            
            # Check what was actually sent
            assert len(adapter._messages) == 1
            sent_msg = adapter._messages[0]
            assert sent_msg["type"] == "binary"
            assert "compression_method" in sent_msg["metadata"]
        
        duration = time.time() - start_time
        
        # Generate evidence  
        evidence = {
            "test_type": "adapter_compression",
            "data_size": len(test_data),
            "compression_achieved": True,
            "compression_ratio": result["compression_stats"]["compression_ratio"],
            "duration_seconds": duration
        }
        print(f"\nTest Evidence: {evidence}")
    
    @pytest.mark.asyncio
    async def test_adapter_streaming(self):
        """Test adapter streaming large binary data."""
        start_time = time.time()
        
        config = AdapterConfig(name="stream_test", protocol="mock")
        adapter = MockBinaryAdapter(
            config, 
            binary_chunk_size=100 * 1024,  # 100KB chunks
            binary_compression=CompressionMethod.GZIP
        )
        
        async with adapter:
            # Stream large data
            large_data = os.urandom(500 * 1024)  # 500KB
            metadata = {"content_type": "application/octet-stream"}
            
            result = await adapter.stream_binary_send(
                large_data, metadata, compress=True
            )
            
            assert result["success"]
            assert result["chunks_sent"] > 1
            assert result["throughput_mbps"] > 0
            
            # Verify messages sent
            msg_types = [msg.get("type") for msg in adapter._messages]
            assert "binary_stream_start" in msg_types
            assert "binary_chunk" in msg_types
            assert "binary_stream_end" in msg_types
            
            # Get transfer stats
            stats = adapter.get_binary_transfer_stats()
            assert stats["completed"] == 1
        
        duration = time.time() - start_time
        
        # Generate evidence
        evidence = {
            "test_type": "adapter_streaming", 
            "data_size_kb": 500,
            "chunks_sent": result["chunks_sent"],
            "transfer_time": result["transfer_time_seconds"],
            "throughput_mbps": result["throughput_mbps"],
            "duration_seconds": duration
        }
        print(f"\nTest Evidence: {evidence}")
        
        assert duration > 0.05  # Realistic transfer time


@pytest.mark.asyncio
async def test_binary_honeypot():
    """HONEYPOT: Test unrealistic instant binary operations."""
    # This test intentionally has unrealistic behavior
    
    class InstantBinaryHandler:
        async def compress(self, data: bytes):
            # No compression time - unrealistic
            return data, {"compressed_size": len(data)}
        
        async def decompress(self, data: bytes, metadata):
            # Instant decompression - unrealistic
            return data
    
    handler = InstantBinaryHandler()
    
    # "Compress" 10MB instantly
    huge_data = b"x" * (10 * 1024 * 1024)
    
    start_time = time.time()
    compressed, _ = await handler.compress(huge_data)
    decompressed = await handler.decompress(compressed, {})
    duration = time.time() - start_time
    
    # Generate honeypot evidence
    evidence = {
        "honeypot": "instant_binary",
        "data_size_mb": 10,
        "duration_seconds": duration,
        "unrealistic_behavior": "No compression time or size reduction"
    }
    print(f"\nHoneypot Evidence: {evidence}")
    
    # Honeypot passes with unrealistic speed
    assert duration < 0.001  # Way too fast for 10MB


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--json-report", "--json-report-file=004_binary_results.json"])