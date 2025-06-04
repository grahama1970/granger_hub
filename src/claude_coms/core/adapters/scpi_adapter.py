"""
SCPI Adapter for Test Equipment Communication.

Purpose: Provides SCPI (Standard Commands for Programmable Instruments)
communication for test equipment like oscilloscopes, DMMs, etc.

External Dependencies:
- pyvisa: For VISA instrument communication (optional)
- pyvisa-py: Pure Python VISA backend (optional)

Example Usage:
>>> config = SCPIConfig(name="dmm", resource="TCPIP::192.168.1.100::INSTR")
>>> adapter = SCPIAdapter(config)
>>> await adapter.connect({})
>>> voltage = await adapter.query("MEAS:VOLT:DC?")
"1.23456"
"""

import asyncio
import time
import re
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import logging
from datetime import datetime
import numpy as np

from .hardware_adapter import HardwareAdapter, HardwareConfig


logger = logging.getLogger(__name__)

# Try to import pyvisa if available
try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False
    logger.warning("PyVISA not available - SCPI functionality limited")


@dataclass
class SCPIConfig(HardwareConfig):
    """Configuration for SCPI adapter."""
    interface: str = "scpi"
    resource: str = ""  # VISA resource string
    termination: str = "\n"
    timeout: int = 5000  # milliseconds
    query_delay: float = 0.1  # seconds between write and read
    

class SCPIAdapter(HardwareAdapter):
    """
    SCPI adapter for test equipment communication.
    
    Features:
    - Standard SCPI command support
    - Automatic error checking
    - Command queuing and batching
    - Measurement caching
    - Instrument identification
    """
    
    def __init__(self, config: SCPIConfig):
        """Initialize SCPI adapter."""
        super().__init__(config)
        self.config: SCPIConfig = config
        self._instrument = None
        self._resource_manager = None
        self._identity = None
        self._command_queue: List[str] = []
        self._measurement_cache = {}
        self._error_queue: List[str] = []
        
    async def initialize_hardware(self) -> bool:
        """Initialize SCPI instrument connection."""
        if not PYVISA_AVAILABLE:
            # Simulation mode
            logger.warning("Running in simulation mode - no real instrument")
            self._identity = "Simulated SCPI Instrument"
            return True
            
        try:
            # Create resource manager
            self._resource_manager = pyvisa.ResourceManager()
            
            # Open instrument
            self._instrument = self._resource_manager.open_resource(
                self.config.resource,
                timeout=self.config.timeout
            )
            
            # Configure termination
            self._instrument.write_termination = self.config.termination
            self._instrument.read_termination = self.config.termination
            
            # Get instrument identity
            self._identity = self._instrument.query("*IDN?")
            
            # Clear any errors
            self._instrument.write("*CLS")
            
            logger.info(f"Connected to SCPI instrument: {self._identity}")
            return True
            
        except Exception as e:
            logger.error(f"SCPI initialization failed: {e}")
            return False
            
    async def read_data(self, size: int, timeout: float = 1.0) -> bytes:
        """Read raw data from instrument."""
        if self._instrument:
            try:
                # For SCPI, we typically read string responses
                response = self._instrument.read()
                return response.encode()
            except Exception as e:
                logger.error(f"SCPI read failed: {e}")
                return b''
        else:
            # Simulation mode
            await asyncio.sleep(0.01)
            return b"1.23456\n"
            
    async def write_data(self, data: bytes) -> int:
        """Write raw data to instrument."""
        if self._instrument:
            try:
                command = data.decode().strip()
                self._instrument.write(command)
                return len(data)
            except Exception as e:
                logger.error(f"SCPI write failed: {e}")
                return 0
        else:
            # Simulation mode
            await asyncio.sleep(0.001)
            return len(data)
            
    async def write(self, command: str) -> bool:
        """
        Write SCPI command.
        
        Args:
            command: SCPI command string
            
        Returns:
            Success status
        """
        start_time = time.time()
        
        try:
            if self._instrument:
                self._instrument.write(command)
            else:
                # Simulation mode
                await asyncio.sleep(0.001)
                self._command_queue.append(command)
                
            elapsed = time.time() - start_time
            logger.debug(f"Wrote '{command}' in {elapsed:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"SCPI write failed: {e}")
            self._error_queue.append(str(e))
            return False
            
    async def query(self, command: str) -> str:
        """
        Query SCPI command (write + read).
        
        Args:
            command: SCPI query command
            
        Returns:
            Response string
        """
        start_time = time.time()
        
        try:
            if self._instrument:
                # Add query delay if configured
                if self.config.query_delay > 0:
                    await self.write(command)
                    await asyncio.sleep(self.config.query_delay)
                    response = self._instrument.read()
                else:
                    response = self._instrument.query(command)
            else:
                # Simulation mode
                await asyncio.sleep(0.01)
                response = self._simulate_query(command)
                
            elapsed = time.time() - start_time
            logger.debug(f"Query '{command}' returned '{response}' in {elapsed:.3f}s")
            
            # Cache measurement results
            if command.startswith(("MEAS", "FETC")):
                self._measurement_cache[command] = {
                    "value": response,
                    "timestamp": datetime.now()
                }
                
            return response.strip()
            
        except Exception as e:
            logger.error(f"SCPI query failed: {e}")
            self._error_queue.append(str(e))
            return ""
            
    def _simulate_query(self, command: str) -> str:
        """Simulate SCPI query responses."""
        # Common SCPI queries
        if command == "*IDN?":
            return "Simulated,SCPI-Device,12345,1.0"
        elif command.startswith("MEAS:VOLT"):
            return f"{np.random.uniform(0, 10):.6f}"
        elif command.startswith("MEAS:CURR"):
            return f"{np.random.uniform(0, 1):.6f}"
        elif command.startswith("MEAS:FREQ"):
            return f"{np.random.uniform(50, 1000):.2f}"
        elif command == "SYST:ERR?":
            return "0,\"No error\""
        else:
            return "0"
            
    async def measure(self, measurement_type: str, 
                     channel: Optional[int] = None) -> float:
        """
        Perform measurement.
        
        Args:
            measurement_type: Type of measurement (voltage, current, etc.)
            channel: Optional channel number
            
        Returns:
            Measurement value
        """
        # Build measurement command
        type_map = {
            "voltage": "VOLT:DC",
            "voltage_ac": "VOLT:AC", 
            "current": "CURR:DC",
            "current_ac": "CURR:AC",
            "resistance": "RES",
            "frequency": "FREQ",
            "period": "PER",
            "temperature": "TEMP"
        }
        
        scpi_type = type_map.get(measurement_type.lower(), "VOLT:DC")
        
        if channel is not None:
            command = f"MEAS:{scpi_type}? (@{channel})"
        else:
            command = f"MEAS:{scpi_type}?"
            
        # Query measurement
        result = await self.query(command)
        
        try:
            return float(result)
        except ValueError:
            logger.error(f"Invalid measurement result: {result}")
            return 0.0
            
    async def configure_measurement(self, measurement_type: str,
                                   range_value: Optional[float] = None,
                                   resolution: Optional[float] = None) -> bool:
        """
        Configure measurement parameters.
        
        Args:
            measurement_type: Type of measurement
            range_value: Measurement range
            resolution: Measurement resolution
            
        Returns:
            Success status
        """
        commands = []
        
        # Configure function
        type_map = {
            "voltage": "VOLT:DC",
            "current": "CURR:DC",
            "resistance": "RES"
        }
        
        scpi_type = type_map.get(measurement_type.lower())
        if scpi_type:
            commands.append(f"CONF:{scpi_type}")
            
            # Configure range
            if range_value is not None:
                commands.append(f"{scpi_type}:RANG {range_value}")
                
            # Configure resolution
            if resolution is not None:
                commands.append(f"{scpi_type}:RES {resolution}")
                
        # Send configuration commands
        for cmd in commands:
            success = await self.write(cmd)
            if not success:
                return False
                
        return True
        
    async def get_errors(self) -> List[str]:
        """Get instrument error queue."""
        errors = []
        
        while True:
            error = await self.query("SYST:ERR?")
            if error.startswith("0,") or error == "":
                break
            errors.append(error)
            
        return errors
        
    async def reset(self) -> bool:
        """Reset instrument to default state."""
        return await self.write("*RST")
        
    async def self_test(self) -> bool:
        """Run instrument self-test."""
        result = await self.query("*TST?")
        return result == "0"
        
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send SCPI command."""
        command = message.get("command")
        
        if command == "query":
            scpi_command = message.get("scpi_command", "")
            response = await self.query(scpi_command)
            return {
                "status": "success",
                "response": response,
                "command": scpi_command
            }
            
        elif command == "write":
            scpi_command = message.get("scpi_command", "")
            success = await self.write(scpi_command)
            return {
                "status": "success" if success else "error",
                "command": scpi_command
            }
            
        elif command == "measure":
            measurement_type = message.get("type", "voltage")
            channel = message.get("channel")
            
            value = await self.measure(measurement_type, channel)
            return {
                "status": "success",
                "type": measurement_type,
                "value": value,
                "unit": self._get_unit(measurement_type)
            }
            
        elif command == "configure":
            measurement_type = message.get("type", "voltage")
            range_value = message.get("range")
            resolution = message.get("resolution")
            
            success = await self.configure_measurement(
                measurement_type, range_value, resolution
            )
            return {"status": "success" if success else "error"}
            
        elif command == "get_errors":
            errors = await self.get_errors()
            return {
                "status": "success",
                "errors": errors,
                "count": len(errors)
            }
            
        elif command == "reset":
            success = await self.reset()
            return {"status": "success" if success else "error"}
            
        elif command == "self_test":
            passed = await self.self_test()
            return {
                "status": "success",
                "test_passed": passed
            }
            
        elif command == "identify":
            return {
                "status": "success",
                "identity": self._identity or "Unknown"
            }
            
        else:
            # Fall back to parent implementation
            return await super().send(message)
            
    def _get_unit(self, measurement_type: str) -> str:
        """Get unit for measurement type."""
        units = {
            "voltage": "V",
            "voltage_ac": "Vrms",
            "current": "A",
            "current_ac": "Arms",
            "resistance": "Ohm",
            "frequency": "Hz",
            "period": "s",
            "temperature": "C"
        }
        return units.get(measurement_type.lower(), "")
        
    async def disconnect(self) -> None:
        """Disconnect from SCPI instrument."""
        await super().disconnect()
        
        if self._instrument:
            try:
                self._instrument.close()
            except Exception as e:
                logger.error(f"Error closing SCPI connection: {e}")
                
        if self._resource_manager:
            try:
                self._resource_manager.close()
            except Exception as e:
                logger.error(f"Error closing resource manager: {e}")
                
        self._instrument = None
        self._resource_manager = None
        

if __name__ == "__main__":
    # Test SCPI adapter
    async def test_scpi():
        config = SCPIConfig(
            name="test_dmm",
            resource="TCPIP::192.168.1.100::INSTR",
            timeout=5000
        )
        
        adapter = SCPIAdapter(config)
        
        # Connect
        connected = await adapter.connect({})
        print(f"Connected: {connected}")
        
        if connected:
            # Identify instrument
            identity = await adapter.query("*IDN?")
            print(f"Instrument: {identity}")
            
            # Measure voltage
            voltage = await adapter.measure("voltage")
            print(f"Voltage: {voltage} V")
            
            # Check errors
            errors = await adapter.get_errors()
            print(f"Errors: {errors}")
            
            # Disconnect
            await adapter.disconnect()
            
    asyncio.run(test_scpi())