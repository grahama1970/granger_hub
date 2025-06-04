"""
Binary Data Handler for Claude Module Communicator.

Purpose: Provides enhanced binary data handling with compression,
chunking, and streaming support for large data transfers.

External Dependencies:
- zstandard: https://github.com/facebook/zstd

Example Usage:
>>> handler = BinaryDataHandler()
>>> compressed = await handler.compress(b"Large data...")
>>> decompressed = await handler.decompress(compressed)
b'Large data...'
"""

import asyncio
import base64
import hashlib
import json
from typing import Dict, Any, Optional, AsyncIterator, Tuple, Union
from pathlib import Path
from datetime import datetime
import io

# Try to import compression libraries
try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

try:
    import lz4.frame
    LZ4_AVAILABLE = True
except ImportError:
    LZ4_AVAILABLE = False

import gzip  # Built-in, always available


class CompressionMethod:
    """Supported compression methods."""
    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"
    LZ4 = "lz4"
    
    @classmethod
    def available_methods(cls) -> list[str]:
        """Get list of available compression methods."""
        methods = [cls.NONE, cls.GZIP]
        if ZSTD_AVAILABLE:
            methods.append(cls.ZSTD)
        if LZ4_AVAILABLE:
            methods.append(cls.LZ4)
        return methods


class BinaryDataHandler:
    """
    Enhanced binary data handler with compression and streaming.
    
    Features:
    - Multiple compression algorithms (gzip, zstd, lz4)
    - Automatic chunking for large data
    - Streaming support for memory efficiency
    - Checksum verification
    - Progress tracking
    """
    
    def __init__(self, chunk_size: int = 1024 * 1024,  # 1MB chunks
                 compression_method: str = CompressionMethod.GZIP,
                 compression_level: int = 6):
        """
        Initialize binary data handler.
        
        Args:
            chunk_size: Size of chunks for streaming (bytes)
            compression_method: Compression algorithm to use
            compression_level: Compression level (1-9 for most algorithms)
        """
        self.chunk_size = chunk_size
        self.compression_method = compression_method
        self.compression_level = compression_level
        
        # Validate compression method
        if compression_method not in CompressionMethod.available_methods():
            raise ValueError(
                f"Compression method '{compression_method}' not available. "
                f"Available: {CompressionMethod.available_methods()}"
            )
    
    async def compress(self, data: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress binary data.
        
        Args:
            data: Raw binary data
            
        Returns:
            Tuple of (compressed_data, metadata)
        """
        start_time = asyncio.get_event_loop().time()
        original_size = len(data)
        
        # Compute checksum of original data
        checksum = hashlib.sha256(data).hexdigest()
        
        # Compress based on method
        if self.compression_method == CompressionMethod.NONE:
            compressed = data
        elif self.compression_method == CompressionMethod.GZIP:
            compressed = await self._compress_gzip(data)
        elif self.compression_method == CompressionMethod.ZSTD and ZSTD_AVAILABLE:
            compressed = await self._compress_zstd(data)
        elif self.compression_method == CompressionMethod.LZ4 and LZ4_AVAILABLE:
            compressed = await self._compress_lz4(data)
        else:
            compressed = data
        
        compressed_size = len(compressed)
        compression_time = asyncio.get_event_loop().time() - start_time
        
        metadata = {
            "compression_method": self.compression_method,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": original_size / compressed_size if compressed_size > 0 else 0,
            "checksum": checksum,
            "compression_time_ms": compression_time * 1000,
            "timestamp": datetime.now().isoformat()
        }
        
        return compressed, metadata
    
    async def decompress(self, data: bytes, metadata: Dict[str, Any]) -> bytes:
        """
        Decompress binary data.
        
        Args:
            data: Compressed binary data
            metadata: Compression metadata
            
        Returns:
            Decompressed data
        """
        method = metadata.get("compression_method", CompressionMethod.NONE)
        
        if method == CompressionMethod.NONE:
            decompressed = data
        elif method == CompressionMethod.GZIP:
            decompressed = await self._decompress_gzip(data)
        elif method == CompressionMethod.ZSTD and ZSTD_AVAILABLE:
            decompressed = await self._decompress_zstd(data)
        elif method == CompressionMethod.LZ4 and LZ4_AVAILABLE:
            decompressed = await self._decompress_lz4(data)
        else:
            raise ValueError(f"Unknown compression method: {method}")
        
        # Verify checksum if provided
        if "checksum" in metadata:
            actual_checksum = hashlib.sha256(decompressed).hexdigest()
            if actual_checksum != metadata["checksum"]:
                raise ValueError("Checksum mismatch after decompression")
        
        return decompressed
    
    async def stream_chunks(self, data: bytes) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream data in chunks.
        
        Yields:
            Chunk dictionaries with data and metadata
        """
        total_size = len(data)
        total_chunks = (total_size + self.chunk_size - 1) // self.chunk_size
        
        for i in range(0, total_size, self.chunk_size):
            chunk_data = data[i:i + self.chunk_size]
            chunk_index = i // self.chunk_size
            
            yield {
                "type": "binary_chunk",
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "chunk_size": len(chunk_data),
                "data": base64.b64encode(chunk_data).decode('utf-8'),
                "progress": (chunk_index + 1) / total_chunks
            }
            
            # Small delay to prevent overwhelming receiver
            await asyncio.sleep(0.001)
    
    async def reassemble_chunks(self, chunks: list[Dict[str, Any]]) -> bytes:
        """
        Reassemble data from chunks.
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            Reassembled binary data
        """
        # Sort chunks by index
        sorted_chunks = sorted(chunks, key=lambda c: c["chunk_index"])
        
        # Verify we have all chunks
        expected_chunks = sorted_chunks[0]["total_chunks"]
        if len(sorted_chunks) != expected_chunks:
            raise ValueError(
                f"Missing chunks: got {len(sorted_chunks)}, expected {expected_chunks}"
            )
        
        # Reassemble data
        data_parts = []
        for chunk in sorted_chunks:
            chunk_data = base64.b64decode(chunk["data"])
            data_parts.append(chunk_data)
        
        return b"".join(data_parts)
    
    # Compression implementations
    async def _compress_gzip(self, data: bytes) -> bytes:
        """Compress using gzip."""
        return await asyncio.to_thread(
            gzip.compress, data, compresslevel=self.compression_level
        )
    
    async def _decompress_gzip(self, data: bytes) -> bytes:
        """Decompress gzip data."""
        return await asyncio.to_thread(gzip.decompress, data)
    
    async def _compress_zstd(self, data: bytes) -> bytes:
        """Compress using zstandard."""
        if not ZSTD_AVAILABLE:
            raise RuntimeError("zstandard not available")
        
        compressor = zstd.ZstdCompressor(level=self.compression_level)
        return await asyncio.to_thread(compressor.compress, data)
    
    async def _decompress_zstd(self, data: bytes) -> bytes:
        """Decompress zstandard data."""
        if not ZSTD_AVAILABLE:
            raise RuntimeError("zstandard not available")
        
        decompressor = zstd.ZstdDecompressor()
        return await asyncio.to_thread(decompressor.decompress, data)
    
    async def _compress_lz4(self, data: bytes) -> bytes:
        """Compress using LZ4."""
        if not LZ4_AVAILABLE:
            raise RuntimeError("lz4 not available")
        
        return await asyncio.to_thread(
            lz4.frame.compress, data, compression_level=self.compression_level
        )
    
    async def _decompress_lz4(self, data: bytes) -> bytes:
        """Decompress LZ4 data."""
        if not LZ4_AVAILABLE:
            raise RuntimeError("lz4 not available")
        
        return await asyncio.to_thread(lz4.frame.decompress, data)


class BinaryFileHandler(BinaryDataHandler):
    """
    Extended handler for binary file operations.
    
    Adds file-specific functionality like direct file streaming
    and metadata extraction.
    """
    
    async def compress_file(self, file_path: Path) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Tuple of (compressed_data, metadata)
        """
        # Read file in chunks to avoid loading large files into memory
        file_data = await self._read_file_chunked(file_path)
        
        # Add file metadata
        compressed, metadata = await self.compress(file_data)
        metadata.update({
            "filename": file_path.name,
            "file_size": file_path.stat().st_size,
            "file_modified": datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat()
        })
        
        return compressed, metadata
    
    async def decompress_to_file(self, data: bytes, metadata: Dict[str, Any],
                                 output_path: Path) -> Path:
        """
        Decompress data and write to file.
        
        Args:
            data: Compressed data
            metadata: Compression metadata
            output_path: Output file path
            
        Returns:
            Path to written file
        """
        decompressed = await self.decompress(data, metadata)
        
        # Write to file
        await self._write_file_chunked(output_path, decompressed)
        
        return output_path
    
    async def _read_file_chunked(self, file_path: Path) -> bytes:
        """Read file in chunks."""
        chunks = []
        
        def read_file():
            with open(file_path, 'rb') as f:
                while chunk := f.read(self.chunk_size):
                    chunks.append(chunk)
        
        await asyncio.to_thread(read_file)
        return b"".join(chunks)
    
    async def _write_file_chunked(self, file_path: Path, data: bytes):
        """Write file in chunks."""
        def write_file():
            with open(file_path, 'wb') as f:
                for i in range(0, len(data), self.chunk_size):
                    f.write(data[i:i + self.chunk_size])
        
        await asyncio.to_thread(write_file)


# Validation
if __name__ == "__main__":
    import time
    
    async def test_binary_handler():
        """Test binary data handler."""
        # Test data
        test_data = b"Hello, this is test data! " * 1000  # ~27KB
        
        # Test different compression methods
        for method in CompressionMethod.available_methods():
            print(f"\nTesting {method} compression:")
            handler = BinaryDataHandler(compression_method=method)
            
            # Compress
            start = time.time()
            compressed, metadata = await handler.compress(test_data)
            compress_time = time.time() - start
            
            print(f"  Original size: {metadata['original_size']} bytes")
            print(f"  Compressed size: {metadata['compressed_size']} bytes")
            print(f"  Compression ratio: {metadata['compression_ratio']:.2f}x")
            print(f"  Compression time: {compress_time*1000:.2f}ms")
            
            # Decompress
            start = time.time()
            decompressed = await handler.decompress(compressed, metadata)
            decompress_time = time.time() - start
            
            assert decompressed == test_data
            print(f"  Decompression time: {decompress_time*1000:.2f}ms")
            print(f"  ✅ Compression/decompression successful")
        
        # Test streaming
        print("\nTesting streaming:")
        handler = BinaryDataHandler(chunk_size=1024)  # 1KB chunks
        
        chunks = []
        async for chunk in handler.stream_chunks(test_data):
            chunks.append(chunk)
            print(f"  Chunk {chunk['chunk_index']+1}/{chunk['total_chunks']}: "
                  f"{chunk['chunk_size']} bytes, progress: {chunk['progress']*100:.1f}%")
        
        # Reassemble
        reassembled = await handler.reassemble_chunks(chunks)
        assert reassembled == test_data
        print(f"  ✅ Streaming successful, reassembled {len(reassembled)} bytes")
        
        return True
    
    # Run test
    result = asyncio.run(test_binary_handler())
    assert result == True
    print("\n✅ Binary handler validation passed!")