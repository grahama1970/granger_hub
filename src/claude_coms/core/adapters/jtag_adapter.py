"""
JTAG Adapter for Debug Interface Communication.

Purpose: Provides JTAG/SWD debugging interface adapter
for embedded systems and hardware debugging.

External Dependencies:
- pyocd: For CMSIS-DAP and other debug probes (optional)
- openocd: For OpenOCD-based debugging (optional)

Example Usage:
>>> config = JTAGConfig(name="stm32_jtag", target="stm32f4")
>>> adapter = JTAGAdapter(config)
>>> await adapter.connect({"probe": "cmsis-dap"})
>>> memory = await adapter.read_memory(0x20000000, 1024)
"""

import asyncio
import time
import struct
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
from datetime import datetime

from .hardware_adapter import HardwareAdapter, HardwareConfig


logger = logging.getLogger(__name__)

# Try to import pyocd if available
try:
    from pyocd.core.helpers import ConnectHelper
    from pyocd.core.target import Target
    PYOCD_AVAILABLE = True
except ImportError:
    PYOCD_AVAILABLE = False
    logger.warning("PyOCD not available - JTAG functionality limited")


@dataclass
class JTAGConfig(HardwareConfig):
    """Configuration for JTAG adapter."""
    interface: str = "jtag"
    target: str = "cortex-m"  # Target device type
    clock_speed: int = 1000000  # 1 MHz default
    reset_on_connect: bool = False
    halt_on_connect: bool = True
    probe_type: str = "cmsis-dap"  # cmsis-dap, stlink, jlink
    

class JTAGAdapter(HardwareAdapter):
    """
    JTAG/SWD adapter for embedded debugging.
    
    Features:
    - Memory read/write operations
    - Register access
    - Flash programming
    - Real-time trace (if supported)
    - Performance profiling
    """
    
    def __init__(self, config: JTAGConfig):
        """Initialize JTAG adapter."""
        super().__init__(config)
        self.config: JTAGConfig = config
        self._session = None
        self._target: Optional['Target'] = None
        self._memory_cache = {}
        self._register_cache = {}
        
    async def initialize_hardware(self) -> bool:
        """Initialize JTAG hardware interface."""
        if not PYOCD_AVAILABLE:
            # Simulate JTAG for testing
            logger.warning("Running in simulation mode - no real hardware")
            return True
            
        try:
            # Connect to target
            self._session = ConnectHelper.session_with_chosen_probe(
                target_override=self.config.target,
                frequency=self.config.clock_speed
            )
            self._session.open()
            
            self._target = self._session.target
            
            # Reset and halt if configured
            if self.config.reset_on_connect:
                self._target.reset()
                
            if self.config.halt_on_connect:
                self._target.halt()
                
            logger.info(f"Connected to {self.config.target} via {self.config.probe_type}")
            return True
            
        except Exception as e:
            logger.error(f"JTAG initialization failed: {e}")
            return False
            
    async def read_data(self, size: int, timeout: float = 1.0) -> bytes:
        """Read data from target memory."""
        # For JTAG, this would read from a specific memory region
        # Simulating for testing
        await asyncio.sleep(0.001)  # Simulate hardware delay
        
        if self._target:
            # Real hardware read
            try:
                # Read from a default memory region (e.g., SRAM)
                data = self._target.read_memory_block8(0x20000000, size)
                return bytes(data)
            except Exception as e:
                logger.error(f"Memory read failed: {e}")
                return b''
        else:
            # Simulation mode - return pattern data
            return bytes([i & 0xFF for i in range(size)])
            
    async def write_data(self, data: bytes) -> int:
        """Write data to target memory."""
        await asyncio.sleep(0.001)  # Simulate hardware delay
        
        if self._target:
            try:
                # Write to default memory region
                self._target.write_memory_block8(0x20000000, list(data))
                return len(data)
            except Exception as e:
                logger.error(f"Memory write failed: {e}")
                return 0
        else:
            # Simulation mode
            return len(data)
            
    async def read_memory(self, address: int, size: int) -> bytes:
        """
        Read memory from specific address.
        
        Args:
            address: Memory address to read from
            size: Number of bytes to read
            
        Returns:
            Memory contents as bytes
        """
        start_time = time.time()
        
        if self._target:
            try:
                # Read memory
                data = self._target.read_memory_block8(address, size)
                result = bytes(data)
                
                # Cache the read
                self._memory_cache[address] = {
                    "data": result,
                    "timestamp": datetime.now()
                }
                
                elapsed = time.time() - start_time
                logger.debug(f"Read {size} bytes from 0x{address:08X} in {elapsed:.3f}s")
                
                return result
                
            except Exception as e:
                logger.error(f"Memory read at 0x{address:08X} failed: {e}")
                raise
        else:
            # Simulation mode
            await asyncio.sleep(0.01)  # Simulate read time
            return bytes([(address + i) & 0xFF for i in range(size)])
            
    async def write_memory(self, address: int, data: bytes) -> bool:
        """
        Write memory to specific address.
        
        Args:
            address: Memory address to write to
            data: Data to write
            
        Returns:
            Success status
        """
        start_time = time.time()
        
        if self._target:
            try:
                # Write memory
                self._target.write_memory_block8(address, list(data))
                
                # Invalidate cache
                if address in self._memory_cache:
                    del self._memory_cache[address]
                    
                elapsed = time.time() - start_time
                logger.debug(f"Wrote {len(data)} bytes to 0x{address:08X} in {elapsed:.3f}s")
                
                return True
                
            except Exception as e:
                logger.error(f"Memory write at 0x{address:08X} failed: {e}")
                return False
        else:
            # Simulation mode
            await asyncio.sleep(0.01)  # Simulate write time
            return True
            
    async def read_registers(self) -> Dict[str, int]:
        """Read CPU registers."""
        registers = {}
        
        if self._target:
            try:
                # Read core registers
                for i in range(16):  # R0-R15
                    registers[f"r{i}"] = self._target.read_core_register(i)
                    
                # Read special registers
                registers["sp"] = registers["r13"]
                registers["lr"] = registers["r14"]
                registers["pc"] = registers["r15"]
                
                # Cache registers
                self._register_cache = registers.copy()
                self._register_cache["timestamp"] = datetime.now()
                
            except Exception as e:
                logger.error(f"Register read failed: {e}")
                
        else:
            # Simulation mode
            await asyncio.sleep(0.005)  # Simulate read time
            for i in range(16):
                registers[f"r{i}"] = 0x20000000 + i * 4
            
            # Add aliases in simulation too
            registers["sp"] = registers["r13"]
            registers["lr"] = registers["r14"] 
            registers["pc"] = registers["r15"]
                
        return registers
        
    async def write_register(self, name: str, value: int) -> bool:
        """Write CPU register."""
        if self._target:
            try:
                # Map register name to index
                if name.startswith("r") and name[1:].isdigit():
                    reg_num = int(name[1:])
                    self._target.write_core_register(reg_num, value)
                    return True
                    
            except Exception as e:
                logger.error(f"Register write failed: {e}")
                return False
        else:
            # Simulation mode
            await asyncio.sleep(0.001)
            return True
            
    async def halt_target(self) -> bool:
        """Halt target execution."""
        if self._target:
            try:
                self._target.halt()
                return True
            except Exception as e:
                logger.error(f"Halt failed: {e}")
                return False
        else:
            # Simulation mode - add realistic delay
            await asyncio.sleep(0.001)
        return True
        
    async def resume_target(self) -> bool:
        """Resume target execution."""
        if self._target:
            try:
                self._target.resume()
                return True
            except Exception as e:
                logger.error(f"Resume failed: {e}")
                return False
        else:
            # Simulation mode - add realistic delay
            await asyncio.sleep(0.001)
        return True
        
    async def reset_target(self, halt: bool = True) -> bool:
        """Reset target."""
        if self._target:
            try:
                self._target.reset(halt=halt)
                return True
            except Exception as e:
                logger.error(f"Reset failed: {e}")
                return False
        else:
            # Simulation mode - add realistic delay
            await asyncio.sleep(0.002)  # Reset takes longer
        return True
        
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send JTAG command."""
        command = message.get("command")
        
        if command == "read_memory":
            address = message.get("address", 0)
            size = message.get("size", 4)
            
            try:
                data = await self.read_memory(address, size)
                return {
                    "status": "success",
                    "address": address,
                    "data": data.hex(),
                    "size": len(data)
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}
                
        elif command == "write_memory":
            address = message.get("address", 0)
            data = bytes.fromhex(message.get("data", ""))
            
            success = await self.write_memory(address, data)
            return {
                "status": "success" if success else "error",
                "address": address,
                "size": len(data)
            }
            
        elif command == "read_registers":
            registers = await self.read_registers()
            return {
                "status": "success",
                "registers": {k: f"0x{v:08X}" for k, v in registers.items()}
            }
            
        elif command == "halt":
            success = await self.halt_target()
            return {"status": "success" if success else "error"}
            
        elif command == "resume":
            success = await self.resume_target()
            return {"status": "success" if success else "error"}
            
        elif command == "reset":
            halt = message.get("halt", True)
            success = await self.reset_target(halt)
            return {"status": "success" if success else "error"}
            
        else:
            # Fall back to parent implementation
            return await super().send(message)
            
    async def disconnect(self) -> None:
        """Disconnect from JTAG interface."""
        await super().disconnect()
        
        if self._session:
            try:
                self._session.close()
            except Exception as e:
                logger.error(f"Error closing JTAG session: {e}")
                
        self._session = None
        self._target = None
        

if __name__ == "__main__":
    # Test JTAG adapter
    async def test_jtag():
        config = JTAGConfig(
            name="test_jtag",
            target="cortex-m4",
            clock_speed=2000000  # 2 MHz
        )
        
        adapter = JTAGAdapter(config)
        
        # Connect
        connected = await adapter.connect({})
        print(f"Connected: {connected}")
        
        if connected:
            # Read memory
            memory = await adapter.read_memory(0x20000000, 256)
            print(f"Memory read: {len(memory)} bytes")
            print(f"First 16 bytes: {memory[:16].hex()}")
            
            # Read registers  
            regs = await adapter.read_registers()
            print(f"Registers: {regs}")
            
            # Disconnect
            await adapter.disconnect()
            
    asyncio.run(test_jtag())