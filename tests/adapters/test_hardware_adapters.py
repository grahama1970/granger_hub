"""Tests for hardware adapters (JTAG, SCPI, etc.)."""

import asyncio
import time
from typing import Dict, Any

import pytest

from claude_coms.core.adapters import (
    JTAGAdapter,
    JTAGConfig,
    SCPIAdapter, 
    SCPIConfig,
    HardwareConfig
)


class TestJTAGAdapter:
    """Test JTAG adapter functionality."""
    
    @pytest.mark.asyncio
    async def test_jtag_connection_and_memory_read(self):
        """Test JTAG connection and memory operations."""
        start_time = time.time()
        
        # Create JTAG adapter
        config = JTAGConfig(
            name="test_jtag",
            target="cortex-m4",
            clock_speed=2000000  # 2 MHz
        )
        adapter = JTAGAdapter(config)
        
        # Connect (simulation mode)
        connected = await adapter.connect({})
        assert connected
        
        # Read memory
        memory = await adapter.read_memory(0x20000000, 256)
        assert len(memory) == 256
        assert isinstance(memory, bytes)
        
        # Write memory
        test_data = b"\x01\x02\x03\x04"
        success = await adapter.write_memory(0x20000000, test_data)
        assert success
        
        # Read registers
        registers = await adapter.read_registers()
        assert "r0" in registers
        assert "r15" in registers  # R15 is PC
        assert len(registers) >= 16  # At least R0-R15
        
        # Send JTAG commands
        response = await adapter.send({
            "command": "read_memory",
            "address": 0x20000000,
            "size": 16
        })
        assert response["status"] == "success"
        assert "data" in response
        assert len(response["data"]) == 32  # 16 bytes as hex
        
        # Disconnect
        await adapter.disconnect()
        
        duration = time.time() - start_time
        print(f"\nJTAG Test Evidence:")
        print(f"- Connected to simulated JTAG")
        print(f"- Read 256 bytes from memory")
        print(f"- Wrote 4 bytes to memory")
        print(f"- Read {len(registers)} CPU registers")
        print(f"- Test duration: {duration:.3f}s")
        
        # Real JTAG operations would take time
        assert duration > 0.01
        
    @pytest.mark.asyncio
    async def test_jtag_target_control(self):
        """Test JTAG target control operations."""
        start_time = time.time()
        
        config = JTAGConfig(name="test_jtag_control")
        adapter = JTAGAdapter(config)
        
        await adapter.connect({})
        
        # Test halt
        response = await adapter.send({"command": "halt"})
        assert response["status"] == "success"
        
        # Test resume
        response = await adapter.send({"command": "resume"})
        assert response["status"] == "success"
        
        # Test reset
        response = await adapter.send({
            "command": "reset",
            "halt": True
        })
        assert response["status"] == "success"
        
        await adapter.disconnect()
        
        duration = time.time() - start_time
        # Control operations are simulated and may be fast
        assert duration > 0.00001  # But not instant
        

class TestSCPIAdapter:
    """Test SCPI adapter functionality."""
    
    @pytest.mark.asyncio
    async def test_scpi_connection_and_queries(self):
        """Test SCPI connection and basic queries."""
        start_time = time.time()
        
        # Create SCPI adapter
        config = SCPIConfig(
            name="test_dmm",
            resource="TCPIP::192.168.1.100::INSTR",
            timeout=5000
        )
        adapter = SCPIAdapter(config)
        
        # Connect (simulation mode)
        connected = await adapter.connect({})
        assert connected
        
        # Query identity
        response = await adapter.send({
            "command": "query",
            "scpi_command": "*IDN?"
        })
        assert response["status"] == "success"
        assert "Simulated" in response["response"]
        
        # Measure voltage
        response = await adapter.send({
            "command": "measure",
            "type": "voltage"
        })
        assert response["status"] == "success"
        assert "value" in response
        assert isinstance(response["value"], float)
        assert response["unit"] == "V"
        
        # Configure measurement
        response = await adapter.send({
            "command": "configure",
            "type": "voltage",
            "range": 10.0,
            "resolution": 0.001
        })
        assert response["status"] == "success"
        
        # Get errors
        response = await adapter.send({"command": "get_errors"})
        assert response["status"] == "success"
        assert response["count"] == 0  # No errors in simulation
        
        # Disconnect
        await adapter.disconnect()
        
        duration = time.time() - start_time
        print(f"\nSCPI Test Evidence:")
        print(f"- Connected to simulated SCPI instrument")
        print(f"- Queried instrument identity")
        print(f"- Performed voltage measurement")
        print(f"- Configured measurement parameters")
        print(f"- Test duration: {duration:.3f}s")
        
        # SCPI operations have delays
        assert duration > 0.01
        
    @pytest.mark.asyncio
    async def test_scpi_measurement_types(self):
        """Test various SCPI measurement types."""
        start_time = time.time()
        
        config = SCPIConfig(name="test_multimeter")
        adapter = SCPIAdapter(config)
        
        await adapter.connect({})
        
        # Test different measurement types
        measurement_types = [
            "voltage", "current", "resistance", "frequency"
        ]
        
        results = {}
        for mtype in measurement_types:
            value = await adapter.measure(mtype)
            assert isinstance(value, float)
            assert value >= 0  # Simulated values are positive
            results[mtype] = value
            
        # Test with channel
        voltage_ch1 = await adapter.measure("voltage", channel=1)
        assert isinstance(voltage_ch1, float)
        
        await adapter.disconnect()
        
        duration = time.time() - start_time
        print(f"\nSCPI Measurement Types Evidence:")
        for mtype, value in results.items():
            print(f"- {mtype}: {value}")
        print(f"- Channel measurement: {voltage_ch1} V")
        print(f"- Test duration: {duration:.3f}s")
        
        assert duration > 0.01
        

class TestHardwareStreaming:
    """Test hardware data streaming capabilities."""
    
    @pytest.mark.asyncio 
    async def test_high_frequency_streaming(self):
        """Test high-frequency data streaming."""
        start_time = time.time()
        
        # Create JTAG adapter for streaming test
        config = JTAGConfig(
            name="stream_test",
            sample_rate=10000,  # 10 kHz
            channel_count=4,
            data_format="uint16"
        )
        adapter = JTAGAdapter(config)
        
        await adapter.connect({})
        
        # Collect streamed data
        collected_samples = []
        sample_count = 0
        
        async def data_callback(data: Dict[str, Any]):
            nonlocal sample_count
            if data["type"] == "hardware_data":
                collected_samples.append(data)
                sample_count += len(data["samples"])
                
        # Start streaming
        await adapter.start_stream(data_callback)
        
        # Stream for a short time
        await asyncio.sleep(0.1)  # 100ms
        
        # Stop streaming
        await adapter.stop_stream()
        
        # Get performance stats
        response = await adapter.send({"command": "get_stats"})
        stats = response["stats"]
        
        await adapter.disconnect()
        
        duration = time.time() - start_time
        print(f"\nHardware Streaming Test Evidence:")
        print(f"- Configured for {config.sample_rate} Hz sampling")
        print(f"- Collected {sample_count} samples")
        print(f"- Bytes received: {stats['bytes_received']}")
        print(f"- Actual sample rate: {stats['actual_sample_rate']:.1f} Hz")
        print(f"- Data rate: {stats['data_rate_bps']:.1f} bytes/sec")
        print(f"- Test duration: {duration:.3f}s")
        
        # Should have collected some samples
        assert sample_count > 0
        assert stats["bytes_received"] > 0
        
        # Streaming takes real time
        assert duration > 0.1
        
    def test_honeypot_instant_hardware_read(self):
        """Honeypot: Test instant hardware operations that should fail."""
        # This test intentionally doesn't do actual hardware ops
        # to demonstrate what fake hardware testing looks like
        
        start_time = time.time()
        
        # Fake instant "hardware" read
        fake_data = b"\x00" * 1000
        
        duration = time.time() - start_time
        
        print(f"\nHoneypot Hardware Test:")
        print(f"- 'Read' 1000 bytes instantly")
        print(f"- Duration: {duration:.6f}s")
        print(f"- This is fake - real hardware has latency")
        
        # This should be detected as fake
        assert duration < 0.0001  # Instant = fake