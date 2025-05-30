"""
CLI Protocol Adapter for Claude Module Communicator.

Enables communication with CLI-based tools by executing commands
and parsing their JSON output.
"""

import asyncio
import json
import subprocess
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import shlex
from datetime import datetime

from .base_adapter import ProtocolAdapter, AdapterConfig


class CLIAdapter(ProtocolAdapter):
    """
    Adapter for CLI-based communication.
    
    Executes command-line tools and parses their output.
    Supports JSON output parsing and streaming.
    """
    
    def __init__(self, config: AdapterConfig, command: Union[str, List[str]], 
                 working_dir: Optional[Path] = None):
        """
        Initialize CLI adapter.
        
        Args:
            config: Adapter configuration
            command: Base command to execute (can include placeholders)
            working_dir: Working directory for command execution
        """
        super().__init__(config)
        self.command = command if isinstance(command, list) else shlex.split(command)
        self.working_dir = working_dir or Path.cwd()
        self._process: Optional[asyncio.subprocess.Process] = None
        
    async def connect(self, **kwargs) -> bool:
        """
        Connect to CLI tool (verify it exists and is executable).
        """
        try:
            # Test if command is available
            test_cmd = [self.command[0], "--version"] if len(self.command) > 0 else ["echo", "test"]
            
            process = await asyncio.create_subprocess_exec(
                *test_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir
            )
            
            await process.communicate()
            
            self._connected = True
            self._connection_time = datetime.now()
            return True
            
        except (FileNotFoundError, PermissionError) as e:
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from CLI tool (terminate any running process)."""
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
        
        self._process = None
        self._connected = False
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute CLI command with message data as arguments.
        
        Args:
            message: Data to pass to CLI command
            
        Returns:
            Parsed output from command
        """
        if not self._connected:
            raise RuntimeError("Adapter not connected")
        
        # Build command with arguments from message
        cmd = self._build_command(message)
        
        # Execute command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            cwd=self.working_dir
        )
        
        # Send input if provided
        stdin_data = None
        if "stdin" in message:
            stdin_data = message["stdin"].encode() if isinstance(message["stdin"], str) else message["stdin"]
        
        # Get output
        stdout, stderr = await process.communicate(input=stdin_data)
        
        # Parse response
        response = {
            "success": process.returncode == 0,
            "exit_code": process.returncode,
            "command": " ".join(cmd)
        }
        
        # Try to parse JSON output
        if stdout:
            try:
                response["data"] = json.loads(stdout.decode())
            except json.JSONDecodeError:
                response["output"] = stdout.decode()
        
        if stderr:
            response["error"] = stderr.decode()
        
        return response
    
    async def receive(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Receive output from a running CLI process.
        
        Used for interactive CLI tools.
        """
        if not self._process:
            return None
        
        try:
            if timeout:
                line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=timeout
                )
            else:
                line = await self._process.stdout.readline()
            
            if not line:
                return None
            
            # Try to parse as JSON
            try:
                return json.loads(line.decode())
            except json.JSONDecodeError:
                return {"output": line.decode().strip()}
                
        except asyncio.TimeoutError:
            return None
    
    async def start_interactive(self, initial_command: Optional[List[str]] = None) -> bool:
        """
        Start an interactive CLI session.
        
        Args:
            initial_command: Override default command for interactive session
            
        Returns:
            True if session started successfully
        """
        if self._process:
            await self.disconnect()
        
        cmd = initial_command or self.command
        
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
            cwd=self.working_dir
        )
        
        return self._process.returncode is None
    
    async def send_interactive(self, input_text: str) -> None:
        """Send input to interactive CLI session."""
        if not self._process or self._process.returncode is not None:
            raise RuntimeError("No active interactive session")
        
        self._process.stdin.write(input_text.encode())
        await self._process.stdin.drain()
    
    def _build_command(self, message: Dict[str, Any]) -> List[str]:
        """
        Build command line from base command and message data.
        
        Args:
            message: Data containing command arguments
            
        Returns:
            Complete command line as list
        """
        cmd = self.command.copy()
        
        # Add boolean flags
        for key, value in message.items():
            if key in ["stdin", "timeout", "type"]:
                continue
                
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key.replace('_', '-')}")
            elif isinstance(value, list):
                for item in value:
                    cmd.extend([f"--{key.replace('_', '-')}", str(item)])
            elif value is not None:
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])
        
        # Add positional arguments if provided
        if "args" in message:
            args = message["args"]
            if isinstance(args, list):
                cmd.extend(str(arg) for arg in args)
            else:
                cmd.append(str(args))
        
        return cmd
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of CLI tool."""
        health = await super().health_check()
        
        # Add CLI-specific info
        health.update({
            "command": " ".join(self.command),
            "working_dir": str(self.working_dir),
            "interactive_session": self._process is not None
        })
        
        return health


# Example usage function
async def example_cli_adapter():
    """Example of using CLIAdapter with different CLI tools."""
    
    # Example 1: Simple command execution
    config = AdapterConfig(name="ls-adapter", protocol="cli")
    adapter = CLIAdapter(config, command="ls -la")
    
    async with adapter:
        result = await adapter.send({"args": ["/tmp"]})
        print(f"Files in /tmp: {result}")
    
    # Example 2: JSON output parsing
    config = AdapterConfig(name="docker-adapter", protocol="cli")
    adapter = CLIAdapter(config, command="docker ps --format json")
    
    async with adapter:
        result = await adapter.send({})
        if result["success"] and "data" in result:
            print(f"Running containers: {result['data']}")
    
    # Example 3: Interactive session
    config = AdapterConfig(name="python-adapter", protocol="cli")
    adapter = CLIAdapter(config, command="python -i")
    
    await adapter.connect()
    await adapter.start_interactive()
    
    await adapter.send_interactive("print('Hello from Python!')\n")
    response = await adapter.receive(timeout=1.0)
    print(f"Python says: {response}")
    
    await adapter.disconnect()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_cli_adapter())