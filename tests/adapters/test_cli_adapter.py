"""
Real tests for CLI Protocol Adapter.

These tests execute actual processes and verify real timing.
No mocks allowed - we test against real commands.
"""

import asyncio
import pytest
import time
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from granger_hub.core.adapters import CLIAdapter, AdapterConfig


class TestCLIAdapterReal:
    """Test CLI adapter with real process execution."""
    
    @pytest.mark.asyncio
    async def test_real_process_execution(self):
        """Test executing a real process and capturing output."""
        start_time = time.time()
        
        # Use a real command that exists on all systems
        config = AdapterConfig(name="echo-test", protocol="cli")
        adapter = CLIAdapter(config, command="echo")
        
        # Connect (verify command exists)
        connected = await adapter.connect()
        assert connected, "Failed to connect to echo command"
        
        # Send a message that becomes command arguments
        result = await adapter.send({
            "args": ["Hello", "from", "CLI", "adapter"]
        })
        
        duration = time.time() - start_time
        
        # Verify real process execution
        assert result["success"] is True, f"Command failed: {result.get('error')}"
        assert result["exit_code"] == 0
        assert "Hello from CLI adapter" in result.get("output", "")
        
        # Real process execution should take measurable time
        assert duration > 0.001, f"Process executed too fast ({duration}s) - might be mocked"
        assert duration < 2.0, f"Process took too long ({duration}s)"
        
        # Get process details for verification
        assert "command" in result
        assert "echo" in result["command"]
        
        await adapter.disconnect()
        
        # Return evidence for LLM verification
        return {
            "duration": duration,
            "command": result["command"],
            "output": result.get("output", ""),
            "exit_code": result["exit_code"]
        }
    
    @pytest.mark.asyncio
    async def test_real_python_execution(self):
        """Test executing Python code via CLI."""
        start_time = time.time()
        
        config = AdapterConfig(name="python-test", protocol="cli")
        adapter = CLIAdapter(config, command="python")
        
        # Connect
        connected = await adapter.connect()
        assert connected, "Failed to connect to python command"
        
        # Execute Python code that takes measurable time
        result = await adapter.send({
            "args": ["-c", "import time; time.sleep(0.1); print('Python executed:', 42)"]
        })
        
        duration = time.time() - start_time
        
        # Verify execution
        assert result["success"] is True
        assert "Python executed: 42" in result.get("output", "")
        
        # Should take at least 100ms due to sleep
        assert duration > 0.1, f"Python didn't sleep properly ({duration}s)"
        assert duration < 0.5, f"Python took too long ({duration}s)"
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "output": result.get("output", ""),
            "sleep_worked": duration > 0.1
        }
    
    @pytest.mark.asyncio
    async def test_process_with_error(self):
        """Test handling process that returns error."""
        start_time = time.time()
        
        config = AdapterConfig(name="error-test", protocol="cli")
        # Use a command that will fail
        adapter = CLIAdapter(config, command="ls")
        
        await adapter.connect()
        
        # Try to list non-existent directory
        result = await adapter.send({
            "args": ["/this/directory/does/not/exist/at/all"]
        })
        
        duration = time.time() - start_time
        
        # Should fail but still return result
        assert result["success"] is False
        assert result["exit_code"] != 0
        assert result.get("error") is not None
        
        # Real process with error still takes time
        assert duration > 0.001
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "exit_code": result["exit_code"],
            "error": result.get("error", "")[:100]  # First 100 chars of error
        }
    
    @pytest.mark.asyncio
    async def test_interactive_session(self):
        """Test interactive CLI session with real process."""
        start_time = time.time()
        
        config = AdapterConfig(name="interactive-test", protocol="cli", timeout=5)
        adapter = CLIAdapter(config, command="python")
        
        await adapter.connect()
        
        # Start interactive Python session
        started = await adapter.start_interactive(["python", "-u", "-i"])
        assert started, "Failed to start interactive session"
        
        # Send command
        await adapter.send_interactive("print('Interactive test')\n")
        
        # Try to receive output (with timeout)
        output = await adapter.receive(timeout=2.0)
        
        duration = time.time() - start_time
        
        # Should have received something
        assert output is not None
        assert duration > 0.01  # Interactive session takes time
        
        await adapter.disconnect()
        
        return {
            "duration": duration,
            "interactive_worked": output is not None,
            "session_started": started
        }
    
    @pytest.mark.asyncio
    async def test_concurrent_adapters(self):
        """Test multiple adapters running concurrently."""
        start_time = time.time()
        
        # Create multiple adapters
        adapters = []
        for i in range(3):
            config = AdapterConfig(name=f"concurrent-{i}", protocol="cli")
            adapter = CLIAdapter(config, command="python")
            adapters.append(adapter)
        
        # Connect all
        for adapter in adapters:
            await adapter.connect()
        
        # Execute commands concurrently
        tasks = []
        for i, adapter in enumerate(adapters):
            task = adapter.send({
                "args": ["-c", f"import time; time.sleep(0.05); print('Process {i}')"]
            })
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        # All should succeed
        for i, result in enumerate(results):
            assert result["success"] is True
            assert f"Process {i}" in result.get("output", "")
        
        # Concurrent execution should be faster than sequential
        # 3 processes * 0.05s = 0.15s if sequential
        # Should be close to 0.05s if concurrent (plus overhead)
        assert duration < 0.12, f"Processes didn't run concurrently ({duration}s)"
        assert duration > 0.05, f"Processes completed too fast ({duration}s)"
        
        # Cleanup
        for adapter in adapters:
            await adapter.disconnect()
        
        return {
            "duration": duration,
            "process_count": len(results),
            "concurrent": duration < 0.12
        }


# Test utilities for verification
def get_process_id():
    """Get current process ID for verification."""
    return os.getpid()


def get_system_info():
    """Get system info for test verification."""
    import platform
    return {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "pid": get_process_id()
    }