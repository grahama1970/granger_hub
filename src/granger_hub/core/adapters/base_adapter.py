"""
Base Protocol Adapter for Granger Hub.
Module: base_adapter.py

Provides the foundation for implementing protocol-specific adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, AsyncIterator
from dataclasses import dataclass
import asyncio
from datetime import datetime


@dataclass
class AdapterConfig:
    """Configuration for protocol adapters."""
    name: str
    protocol: str
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProtocolAdapter(ABC):
    """
    Base class for all protocol adapters.
    
    Protocol adapters translate between the internal message format
    and protocol-specific formats (REST, CLI, MCP, etc.).
    """
    
    def __init__(self, config: AdapterConfig):
        """Initialize the adapter with configuration."""
        self.config = config
        self._connected = False
        self._connection_time: Optional[datetime] = None
        
    @property
    def is_connected(self) -> bool:
        """Check if adapter is connected."""
        return self._connected
    
    @property
    def protocol_type(self) -> str:
        """Get the protocol type."""
        return self.config.protocol
    
    @abstractmethod
    async def connect(self, **kwargs) -> bool:
        """
        Establish connection to the service.
        
        Returns:
            bool: True if connection successful
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the service."""
        pass
    
    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a message using the protocol.
        
        Args:
            message: Message to send
            
        Returns:
            Response from the service
        """
        pass
    
    @abstractmethod
    async def receive(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Receive a message from the protocol.
        
        Args:
            timeout: Maximum time to wait for message
            
        Returns:
            Received message or None if timeout
        """
        pass
    
    async def send_binary(self, data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send binary data.
        
        Default implementation encodes as base64 in message.
        Subclasses can override for more efficient handling.
        """
        import base64
        message = {
            "type": "binary",
            "data": base64.b64encode(data).decode('utf-8'),
            "metadata": metadata
        }
        return await self.send(message)
    
    async def receive_binary(self, timeout: Optional[float] = None) -> Optional[tuple[bytes, Dict[str, Any]]]:
        """
        Receive binary data.
        
        Returns:
            Tuple of (data, metadata) or None if timeout
        """
        message = await self.receive(timeout)
        if message and message.get("type") == "binary":
            import base64
            data = base64.b64decode(message["data"])
            metadata = message.get("metadata", {})
            return data, metadata
        return None
    
    async def stream_send(self, data_iterator: AsyncIterator[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Stream data to the service.
        
        Args:
            data_iterator: Async iterator of data chunks
            
        Returns:
            Final response after streaming
        """
        responses = []
        async for chunk in data_iterator:
            response = await self.send(chunk)
            responses.append(response)
        
        return {
            "type": "stream_complete",
            "chunks": len(responses),
            "responses": responses
        }
    
    async def stream_receive(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Receive streaming data from the service.
        
        Yields:
            Data chunks as they arrive
        """
        while True:
            message = await self.receive(timeout=self.config.timeout)
            if not message:
                break
            
            yield message
            
            if message.get("type") == "stream_end":
                break
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of the connection.
        
        Returns:
            Health status information
        """
        return {
            "connected": self._connected,
            "protocol": self.config.protocol,
            "name": self.config.name,
            "connection_time": self._connection_time.isoformat() if self._connection_time else None,
            "status": "healthy" if self._connected else "disconnected"
        }
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(name='{self.config.name}', protocol='{self.config.protocol}', connected={self._connected})"