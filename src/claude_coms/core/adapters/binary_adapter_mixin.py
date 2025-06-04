"""
Binary Adapter Mixin for Enhanced Binary Support.

Purpose: Provides enhanced binary data handling capabilities to protocol adapters
using the BinaryDataHandler for compression and streaming.

Example Usage:
>>> class MyAdapter(ProtocolAdapter, BinaryAdapterMixin):
>>>     pass
>>> adapter = MyAdapter(config)
>>> await adapter.send_binary_compressed(large_data, {"type": "image"})
"""

from typing import Dict, Any, Optional, AsyncIterator, Tuple
import asyncio
from datetime import datetime

from ..binary_handler import BinaryDataHandler, CompressionMethod


class BinaryAdapterMixin:
    """
    Mixin to add enhanced binary capabilities to protocol adapters.
    
    Provides:
    - Automatic compression/decompression
    - Streaming large binary data
    - Progress tracking
    - Bandwidth optimization
    """
    
    def __init__(self, *args, binary_chunk_size: int = 1024 * 1024,
                 binary_compression: str = CompressionMethod.GZIP,
                 **kwargs):
        """
        Initialize binary mixin.
        
        Args:
            binary_chunk_size: Size of chunks for streaming
            binary_compression: Default compression method
        """
        super().__init__(*args, **kwargs)
        
        self.binary_handler = BinaryDataHandler(
            chunk_size=binary_chunk_size,
            compression_method=binary_compression
        )
        self._binary_transfers = {}  # Track ongoing transfers
    
    async def send_binary_compressed(self, data: bytes, 
                                   metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send binary data with automatic compression.
        
        Args:
            data: Binary data to send
            metadata: Additional metadata
            
        Returns:
            Response including compression stats
        """
        # Compress data
        compressed, compression_metadata = await self.binary_handler.compress(data)
        
        # Merge metadata
        full_metadata = {**metadata, **compression_metadata}
        
        # Send compressed data
        result = await self.send_binary(compressed, full_metadata)
        
        # Add compression stats to result
        result["compression_stats"] = {
            "original_size": compression_metadata["original_size"],
            "compressed_size": compression_metadata["compressed_size"],
            "compression_ratio": compression_metadata["compression_ratio"],
            "method": compression_metadata["compression_method"]
        }
        
        return result
    
    async def receive_binary_compressed(self, 
                                      timeout: Optional[float] = None) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Receive and decompress binary data.
        
        Returns:
            Tuple of (decompressed_data, metadata) or None
        """
        result = await self.receive_binary(timeout)
        if not result:
            return None
        
        compressed_data, metadata = result
        
        # Check if data is compressed
        if "compression_method" in metadata:
            # Decompress
            decompressed = await self.binary_handler.decompress(
                compressed_data, metadata
            )
            return decompressed, metadata
        
        # Not compressed, return as-is
        return compressed_data, metadata
    
    async def stream_binary_send(self, data: bytes, 
                               metadata: Dict[str, Any],
                               compress: bool = True) -> Dict[str, Any]:
        """
        Stream large binary data in chunks.
        
        Args:
            data: Binary data to stream
            metadata: Additional metadata
            compress: Whether to compress before streaming
            
        Returns:
            Final response after streaming
        """
        transfer_id = f"transfer_{datetime.now().timestamp()}"
        self._binary_transfers[transfer_id] = {
            "start_time": asyncio.get_event_loop().time(),
            "total_size": len(data),
            "chunks_sent": 0,
            "status": "active"
        }
        
        try:
            # Compress if requested
            if compress:
                data, compression_metadata = await self.binary_handler.compress(data)
                metadata.update(compression_metadata)
            
            # Send initial metadata
            await self.send({
                "type": "binary_stream_start",
                "transfer_id": transfer_id,
                "metadata": metadata,
                "total_size": len(data)
            })
            
            # Stream chunks
            responses = []
            async for chunk in self.binary_handler.stream_chunks(data):
                chunk["transfer_id"] = transfer_id
                response = await self.send(chunk)
                responses.append(response)
                
                # Update transfer stats
                self._binary_transfers[transfer_id]["chunks_sent"] += 1
                
                # Allow for backpressure
                if response.get("pause_requested"):
                    await asyncio.sleep(response.get("pause_duration", 0.1))
            
            # Send completion
            final_response = await self.send({
                "type": "binary_stream_end",
                "transfer_id": transfer_id,
                "chunks_sent": len(responses)
            })
            
            # Calculate stats
            transfer_time = asyncio.get_event_loop().time() - self._binary_transfers[transfer_id]["start_time"]
            throughput = len(data) / transfer_time if transfer_time > 0 else 0
            
            self._binary_transfers[transfer_id]["status"] = "completed"
            
            return {
                "success": True,
                "transfer_id": transfer_id,
                "chunks_sent": len(responses),
                "total_size": len(data),
                "transfer_time_seconds": transfer_time,
                "throughput_mbps": throughput / (1024 * 1024),
                "responses": responses
            }
            
        except Exception as e:
            self._binary_transfers[transfer_id]["status"] = "failed"
            self._binary_transfers[transfer_id]["error"] = str(e)
            raise
    
    async def stream_binary_receive(self, 
                                  transfer_id: Optional[str] = None,
                                  timeout: float = 30.0) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Receive streaming binary data.
        
        Args:
            transfer_id: Expected transfer ID (None to accept any)
            timeout: Total timeout for transfer
            
        Returns:
            Tuple of (data, metadata) or None
        """
        chunks = []
        metadata = None
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                return None
            
            # Receive message
            message = await self.receive(timeout=5.0)
            if not message:
                continue
            
            msg_type = message.get("type")
            
            if msg_type == "binary_stream_start":
                # Validate transfer ID if provided
                if transfer_id and message.get("transfer_id") != transfer_id:
                    continue
                
                metadata = message.get("metadata", {})
                transfer_id = message.get("transfer_id")
                
            elif msg_type == "binary_chunk":
                # Validate this is our transfer
                if transfer_id and message.get("transfer_id") != transfer_id:
                    continue
                
                chunks.append(message)
                
                # Send acknowledgment with flow control
                await self.send({
                    "type": "chunk_ack",
                    "transfer_id": transfer_id,
                    "chunk_index": message["chunk_index"],
                    "pause_requested": False  # Could implement backpressure here
                })
                
            elif msg_type == "binary_stream_end":
                # Validate this is our transfer
                if transfer_id and message.get("transfer_id") != transfer_id:
                    continue
                
                # Reassemble chunks
                data = await self.binary_handler.reassemble_chunks(chunks)
                
                # Decompress if needed
                if metadata and "compression_method" in metadata:
                    data = await self.binary_handler.decompress(data, metadata)
                
                return data, metadata
    
    def get_binary_transfer_stats(self, transfer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for binary transfers.
        
        Args:
            transfer_id: Specific transfer ID or None for all
            
        Returns:
            Transfer statistics
        """
        if transfer_id:
            return self._binary_transfers.get(transfer_id, {})
        
        # Return summary of all transfers
        total_transfers = len(self._binary_transfers)
        active = sum(1 for t in self._binary_transfers.values() if t["status"] == "active")
        completed = sum(1 for t in self._binary_transfers.values() if t["status"] == "completed")
        failed = sum(1 for t in self._binary_transfers.values() if t["status"] == "failed")
        
        return {
            "total_transfers": total_transfers,
            "active": active,
            "completed": completed,
            "failed": failed,
            "transfers": self._binary_transfers
        }


# Example enhanced adapter
class BinaryEnhancedAdapter(BinaryAdapterMixin):
    """Example adapter with enhanced binary support."""
    
    async def send_file(self, file_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send a file with automatic compression and streaming.
        
        Args:
            file_path: Path to file
            metadata: Additional metadata
            
        Returns:
            Transfer result
        """
        from pathlib import Path
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read file
        with open(path, 'rb') as f:
            data = f.read()
        
        # Prepare metadata
        file_metadata = {
            "filename": path.name,
            "file_size": len(data),
            "content_type": self._guess_content_type(path.name),
            **(metadata or {})
        }
        
        # Use streaming for large files
        if len(data) > 10 * 1024 * 1024:  # 10MB
            return await self.stream_binary_send(data, file_metadata)
        else:
            return await self.send_binary_compressed(data, file_metadata)
    
    def _guess_content_type(self, filename: str) -> str:
        """Guess content type from filename."""
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"