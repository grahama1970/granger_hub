"""
Hardware Adapter Base Class for Instrument Communication.

Purpose: Provides foundation for hardware instrument adapters
including JTAG, SCPI, and sensor data streaming.

External Dependencies:
- pyserial: For serial communication
- pyvisa: For SCPI instrument control (optional)
- pyocd: For JTAG/SWD debugging (optional)

Example Usage:
>>> adapter = JTAGAdapter(config)
>>> await adapter.connect({"interface": "cmsis-dap"})
>>> data = await adapter.read_memory(0x20000000, 1024)
bytearray(b'\x00\x01\x02...')
"""

import asyncio
import time
from abc import abstractmethod
from typing import Dict, Any, Optional, AsyncIterator, List, Callable
from dataclasses import dataclass, field
import struct
import logging
from datetime import datetime
import numpy as np

from .base_adapter import ProtocolAdapter, AdapterConfig


logger = logging.getLogger(__name__)


@dataclass
class HardwareConfig(AdapterConfig):
    """Configuration for hardware adapters."""
    protocol: str = "hardware"
    interface: str = "serial"  # serial, usb, ethernet, jtag
    baudrate: int = 115200
    data_bits: int = 8
    stop_bits: int = 1
    parity: str = "none"
    flow_control: str = "none"
    buffer_size: int = 4096
    sample_rate: int = 1000  # Hz
    channel_count: int = 1
    data_format: str = "uint16"  # uint8, uint16, int16, float32
    

@dataclass 
class StreamMetadata:
    """Metadata for hardware data streams."""
    timestamp: datetime = field(default_factory=datetime.now)
    sequence_number: int = 0
    sample_rate: int = 1000
    channel_count: int = 1
    data_format: str = "uint16"
    lost_samples: int = 0
    buffer_overruns: int = 0
    

class HardwareAdapter(ProtocolAdapter):
    """
    Base class for hardware instrument adapters.
    
    Features:
    - High-frequency data streaming
    - Buffer management
    - Data decimation and filtering
    - Error recovery
    - Performance monitoring
    """
    
    def __init__(self, config: HardwareConfig):
        """Initialize hardware adapter."""
        super().__init__(config)
        self.config: HardwareConfig = config
        self._stream_active = False
        self._stream_task: Optional[asyncio.Task] = None
        self._data_buffer: List[bytes] = []
        self._metadata = StreamMetadata(
            sample_rate=config.sample_rate,
            channel_count=config.channel_count,
            data_format=config.data_format
        )
        self._callbacks: List[Callable] = []
        self._performance_stats = {
            "bytes_received": 0,
            "samples_processed": 0,
            "buffer_overruns": 0,
            "lost_samples": 0,
            "start_time": None
        }
        
    @abstractmethod
    async def initialize_hardware(self) -> bool:
        """Initialize hardware interface."""
        pass
        
    @abstractmethod
    async def read_data(self, size: int, timeout: float = 1.0) -> bytes:
        """Read raw data from hardware."""
        pass
        
    @abstractmethod
    async def write_data(self, data: bytes) -> int:
        """Write data to hardware."""
        pass
        
    async def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to hardware device."""
        try:
            # Initialize hardware
            success = await self.initialize_hardware()
            if not success:
                return False
                
            self._connected = True
            self._connection_time = datetime.now()
            self._performance_stats["start_time"] = time.time()
            
            logger.info(f"Connected to {self.config.interface} hardware")
            return True
            
        except Exception as e:
            logger.error(f"Hardware connection failed: {e}")
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from hardware."""
        # Stop streaming if active
        await self.stop_stream()
        
        self._connected = False
        logger.info("Hardware disconnected")
        
    async def start_stream(self, callback: Optional[Callable] = None) -> None:
        """
        Start high-frequency data streaming.
        
        Args:
            callback: Optional callback for data chunks
        """
        if self._stream_active:
            logger.warning("Stream already active")
            return
            
        if callback:
            self._callbacks.append(callback)
            
        self._stream_active = True
        self._stream_task = asyncio.create_task(self._stream_loop())
        logger.info(f"Started streaming at {self.config.sample_rate} Hz")
        
    async def stop_stream(self) -> None:
        """Stop data streaming."""
        if not self._stream_active:
            return
            
        self._stream_active = False
        
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Streaming stopped")
        
    async def _stream_loop(self) -> None:
        """Main streaming loop."""
        bytes_per_sample = self._get_bytes_per_sample()
        samples_per_read = 1000  # Read 1000 samples at a time
        read_size = samples_per_read * bytes_per_sample * self.config.channel_count
        
        while self._stream_active:
            try:
                # Read data from hardware
                start_time = time.time()
                data = await self.read_data(read_size, timeout=0.1)
                read_time = time.time() - start_time
                
                if data:
                    # Update stats
                    self._performance_stats["bytes_received"] += len(data)
                    samples = len(data) // (bytes_per_sample * self.config.channel_count)
                    self._performance_stats["samples_processed"] += samples
                    
                    # Process data
                    processed = await self._process_data(data)
                    
                    # Send to callbacks
                    for callback in self._callbacks:
                        try:
                            await callback(processed)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                            
                    # Check for buffer overrun
                    if read_time > (1.0 / self.config.sample_rate * samples):
                        self._performance_stats["buffer_overruns"] += 1
                        self._metadata.buffer_overruns += 1
                        
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.001)
                
            except asyncio.TimeoutError:
                # Normal timeout, continue
                pass
            except Exception as e:
                logger.error(f"Stream error: {e}")
                await asyncio.sleep(0.1)  # Back off on error
                
    async def _process_data(self, raw_data: bytes) -> Dict[str, Any]:
        """Process raw hardware data."""
        # Parse data based on format
        samples = self._parse_samples(raw_data)
        
        # Update metadata
        self._metadata.sequence_number += 1
        
        return {
            "type": "hardware_data",
            "timestamp": datetime.now().isoformat(),
            "sequence": self._metadata.sequence_number,
            "samples": samples,
            "sample_rate": self.config.sample_rate,
            "channels": self.config.channel_count,
            "format": self.config.data_format,
            "metadata": {
                "lost_samples": self._metadata.lost_samples,
                "buffer_overruns": self._metadata.buffer_overruns
            }
        }
        
    def _parse_samples(self, data: bytes) -> List[List[float]]:
        """Parse raw bytes into samples."""
        bytes_per_sample = self._get_bytes_per_sample()
        samples_count = len(data) // (bytes_per_sample * self.config.channel_count)
        
        # Format string for struct
        format_map = {
            "uint8": "B",
            "uint16": "H",
            "int16": "h",
            "float32": "f"
        }
        
        fmt = format_map.get(self.config.data_format, "H")
        samples = []
        
        for i in range(samples_count):
            sample = []
            for ch in range(self.config.channel_count):
                offset = (i * self.config.channel_count + ch) * bytes_per_sample
                value = struct.unpack(fmt, data[offset:offset + bytes_per_sample])[0]
                sample.append(float(value))
            samples.append(sample)
            
        return samples
        
    def _get_bytes_per_sample(self) -> int:
        """Get bytes per sample based on data format."""
        format_sizes = {
            "uint8": 1,
            "uint16": 2, 
            "int16": 2,
            "float32": 4
        }
        return format_sizes.get(self.config.data_format, 2)
        
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to hardware."""
        command = message.get("command")
        
        if command == "start_stream":
            await self.start_stream()
            return {"status": "success", "message": "Streaming started"}
            
        elif command == "stop_stream":
            await self.stop_stream() 
            return {"status": "success", "message": "Streaming stopped"}
            
        elif command == "get_stats":
            return {
                "status": "success",
                "stats": self.get_performance_stats()
            }
            
        elif command == "configure":
            # Update configuration
            for key, value in message.get("config", {}).items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            return {"status": "success", "message": "Configuration updated"}
            
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}
            
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive data from hardware stream."""
        if not self._stream_active:
            return None
            
        # Wait for data in buffer
        timeout = 1.0 / self.config.sample_rate * 100  # Wait for 100 samples
        start = time.time()
        
        while len(self._data_buffer) == 0 and time.time() - start < timeout:
            await asyncio.sleep(0.001)
            
        if self._data_buffer:
            return self._data_buffer.pop(0)
            
        return None
        
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get streaming performance statistics."""
        if self._performance_stats["start_time"]:
            duration = time.time() - self._performance_stats["start_time"]
            sample_rate = self._performance_stats["samples_processed"] / duration if duration > 0 else 0
            data_rate = self._performance_stats["bytes_received"] / duration if duration > 0 else 0
        else:
            sample_rate = 0
            data_rate = 0
            
        return {
            "bytes_received": self._performance_stats["bytes_received"],
            "samples_processed": self._performance_stats["samples_processed"],
            "buffer_overruns": self._performance_stats["buffer_overruns"],
            "lost_samples": self._performance_stats["lost_samples"],
            "actual_sample_rate": sample_rate,
            "data_rate_bps": data_rate,
            "stream_active": self._stream_active
        }
        
    async def stream_chunks(self, sample_count: int = 10000) -> AsyncIterator[Dict[str, Any]]:
        """Stream data in chunks for processing."""
        collected_samples = []
        
        # Temporary callback to collect samples
        async def collector(data: Dict[str, Any]):
            collected_samples.extend(data["samples"])
            
        # Start streaming
        await self.start_stream(collector)
        
        try:
            while len(collected_samples) < sample_count:
                if len(collected_samples) >= 1000:  # Yield every 1000 samples
                    chunk = collected_samples[:1000]
                    collected_samples = collected_samples[1000:]
                    
                    yield {
                        "type": "hardware_chunk",
                        "samples": chunk,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": self._metadata.__dict__
                    }
                    
                await asyncio.sleep(0.01)  # Small delay
                
            # Yield remaining samples
            if collected_samples:
                yield {
                    "type": "hardware_chunk",
                    "samples": collected_samples,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": self._metadata.__dict__
                }
                
        finally:
            # Stop streaming
            await self.stop_stream()


if __name__ == "__main__":
    # Test hardware adapter base functionality
    async def test_hardware_adapter():
        config = HardwareConfig(
            name="test_hardware",
            interface="serial",
            baudrate=115200,
            sample_rate=1000,
            channel_count=2,
            data_format="uint16"
        )
        
        # This would need a concrete implementation
        print(f"Hardware config: {config}")
        print(f"Bytes per sample: {2}")
        print(f"Expected data rate: {config.sample_rate * config.channel_count * 2} bytes/sec")
        
    asyncio.run(test_hardware_adapter())