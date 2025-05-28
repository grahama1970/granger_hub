"""
Claude Code Communicator for inter-module communication.

Purpose: Enables modules to communicate dynamically using Claude Code instances
with system prompts and dangerous permissions flag.

Dependencies:
- subprocess: For spawning Claude Code instances
- asyncio: For async communication
- json: For data serialization
- tempfile: For temporary prompt files
"""

import subprocess
import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
from datetime import datetime
import shutil
from dataclasses import dataclass
import uuid


@dataclass
class CommunicationResult:
    """Result of module communication."""
    source_module: str
    target_module: str
    message_id: str
    timestamp: str
    message: str
    response: str
    status: str
    metadata: Dict[str, Any]


class ClaudeCodeCommunicator:
    """Communicates between modules using Claude Code instances."""
    
    def __init__(self, module_name: str, system_prompt: str):
        """Initialize communicator for a module.
        
        Args:
            module_name: Name of the module
            system_prompt: System prompt describing module's capabilities
        """
        self.module_name = module_name
        self.system_prompt = system_prompt
        
        # Find Claude Code executable
        self.claude_code_path = self._find_claude_executable()
        
        # Communication history
        self.communication_log: List[CommunicationResult] = []
        
    def _find_claude_executable(self) -> str:
        """Find Claude Code executable in system."""
        # Try common names
        for cmd in ["claude", "claude-code", "claude-cli"]:
            path = shutil.which(cmd)
            if path:
                return path
        
        # Default fallback
        return "claude"
    
    async def send_message(self, 
                          target_module: str, 
                          message: str,
                          target_context: Optional[str] = None,
                          context: Optional[Dict[str, Any]] = None,
                          timeout: int = 30) -> CommunicationResult:
        """Send a message to another module via Claude Code.
        
        Args:
            target_module: Name of the target module
            message: Message to send
            target_context: Optional context about the target module
            context: Additional context data
            timeout: Timeout in seconds
            
        Returns:
            CommunicationResult with response
        """
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Build the full prompt for Claude
        full_prompt = self._build_prompt(
            target_module, message, target_context, context
        )
        
        # Create temporary file for the prompt
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.md', delete=False
        ) as f:
            f.write(full_prompt)
            prompt_file = f.name
        
        try:
            # Run Claude Code with dangerous permissions flag
            cmd = [
                self.claude_code_path,
                "--dangerously-skip-permissions",
                prompt_file
            ]
            
            # Execute Claude Code asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Claude Code timed out after {timeout}s")
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Claude Code failed: {error_msg}")
            
            # Create result
            result = CommunicationResult(
                source_module=self.module_name,
                target_module=target_module,
                message_id=message_id,
                timestamp=timestamp,
                message=message,
                response=stdout.decode().strip(),
                status="SUCCESS",
                metadata={
                    "context": context or {},
                    "execution_time": (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds()
                }
            )
            
            # Log communication
            self.communication_log.append(result)
            
            return result
            
        except Exception as e:
            # Create error result
            result = CommunicationResult(
                source_module=self.module_name,
                target_module=target_module,
                message_id=message_id,
                timestamp=timestamp,
                message=message,
                response=str(e),
                status="ERROR",
                metadata={"error_type": type(e).__name__}
            )
            self.communication_log.append(result)
            raise
            
        finally:
            # Cleanup temporary file
            Path(prompt_file).unlink(missing_ok=True)
    
    def _build_prompt(self, 
                     target_module: str, 
                     message: str,
                     target_context: Optional[str],
                     context: Optional[Dict[str, Any]]) -> str:
        """Build the full prompt for Claude Code."""
        return f"""# Inter-Module Communication

## Current Module: {self.module_name}
{self.system_prompt}

## Target Module: {target_module}
{target_context or "No specific context provided for target module."}

## Communication Request
**From:** {self.module_name}
**To:** {target_module}
**Message:** {message}

## Additional Context
```json
{json.dumps(context or {}, indent=2)}
```

## Instructions
You are facilitating communication between these modules. Based on the source module's capabilities and the message content, provide an appropriate response that the target module would give. Consider:

1. The capabilities and constraints of both modules
2. The specific request in the message
3. Any additional context provided
4. Maintain consistency with each module's defined behavior

Respond as if you are the target module ({target_module}) receiving this message.
"""
    
    async def broadcast_message(self,
                               target_modules: List[str],
                               message: str,
                               context: Optional[Dict[str, Any]] = None) -> List[CommunicationResult]:
        """Broadcast a message to multiple modules.
        
        Args:
            target_modules: List of target module names
            message: Message to broadcast
            context: Additional context
            
        Returns:
            List of CommunicationResult objects
        """
        tasks = [
            self.send_message(target, message, context=context)
            for target in target_modules
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to results
        communication_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error result
                error_result = CommunicationResult(
                    source_module=self.module_name,
                    target_module=target_modules[i],
                    message_id=str(uuid.uuid4()),
                    timestamp=datetime.now().isoformat(),
                    message=message,
                    response=str(result),
                    status="ERROR",
                    metadata={"error_type": type(result).__name__}
                )
                communication_results.append(error_result)
            else:
                communication_results.append(result)
        
        return communication_results
    
    def get_communication_history(self, 
                                 target_module: Optional[str] = None) -> List[CommunicationResult]:
        """Get communication history, optionally filtered by target module."""
        if target_module:
            return [
                r for r in self.communication_log 
                if r.target_module == target_module
            ]
        return self.communication_log.copy()


# Example usage and testing
if __name__ == "__main__":
    async def test_communication():
        # Create a data processor module
        processor = ClaudeCodeCommunicator(
            module_name="DataProcessor",
            system_prompt="You are a data processing module that transforms raw data into structured formats."
        )
        
        # Send a message to an analyzer module
        try:
            result = await processor.send_message(
                target_module="DataAnalyzer",
                message="I have processed 1000 records with 3 anomalies detected. Please analyze the anomaly patterns.",
                target_context="You are a data analysis module that identifies patterns and generates insights.",
                context={
                    "record_count": 1000,
                    "anomaly_count": 3,
                    "processing_time": 5.2,
                    "anomaly_types": ["missing_data", "outlier", "format_error"]
                }
            )
            
            print(f"✅ Communication successful!")
            print(f"Message ID: {result.message_id}")
            print(f"Response: {result.response}")
            print(f"Execution time: {result.metadata['execution_time']:.2f}s")
            
        except Exception as e:
            print(f"❌ Communication failed: {e}")
    
    # Run the test
    asyncio.run(test_communication())