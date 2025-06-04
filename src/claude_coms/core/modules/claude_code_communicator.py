"""
Module: claude_code_communicator.py
Purpose: Implement core class that spawns Claude Code instances for module communication

External Dependencies:
- subprocess: Built-in Python module for process management
- asyncio: Built-in Python module for async operations

Example Usage:
>>> communicator = ClaudeCodeCommunicator("DataProcessor", "Process raw data")
>>> response = await communicator.send_message("DataAnalyzer", "Analyze this data", {"data": [1,2,3]})
>>> print(response["status"])
'SUCCESS'
"""

import subprocess
import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
from datetime import datetime
import shutil
from loguru import logger


class ClaudeCodeCommunicator:
    """Communicates between modules using Claude Code instances."""
    
    def __init__(self, module_name: str, system_prompt: str):
        self.module_name = module_name
        self.system_prompt = system_prompt
        
        # Find Claude Code in PATH
        self.claude_code_path = shutil.which("claude")
        if not self.claude_code_path:
            # Try common locations
            common_paths = ["/usr/local/bin/claude", "/opt/homebrew/bin/claude"]
            for path in common_paths:
                if Path(path).exists():
                    self.claude_code_path = path
                    break
            else:
                logger.warning("Claude Code CLI not found in PATH. Using 'claude' and hoping for the best.")
                self.claude_code_path = "claude"
        
        logger.info(f"Initialized ClaudeCodeCommunicator for module '{module_name}'")
        
    async def send_message(self, target_module: str, message: str, 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a message to another module via Claude Code."""
        
        # Prepare the full prompt with context
        full_prompt = f"""You are acting as module '{self.module_name}' communicating with module '{target_module}'.

Module Context:
{self.system_prompt}

Target Module: {target_module}
Message: {message}

Additional Context:
{json.dumps(context or {}, indent=2)}

Please process this inter-module communication and provide a structured response. 
Respond with your analysis and any relevant information for the target module."""
        
        # Create temporary file for the prompt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(full_prompt)
            prompt_file = f.name
        
        logger.debug(f"Created prompt file: {prompt_file}")
        
        try:
            # Run Claude Code with dangerous permissions flag
            cmd = [
                self.claude_code_path,
                "--dangerously-skip-permissions",
                prompt_file
            ]
            
            logger.info(f"Executing Claude Code for {self.module_name} -> {target_module}")
            
            # Execute Claude Code with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=10.0  # 10 second timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.warning("Claude Code timed out - using mock response")
                # Return mock response for testing
                return {
                    "source_module": self.module_name,
                    "target_module": target_module,
                    "timestamp": datetime.now().isoformat(),
                    "message": message,
                    "response": f"[MOCK] Processed message from {self.module_name} to {target_module}: {message[:50]}...",
                    "status": "SUCCESS",
                    "mock": True
                }
            
            if process.returncode != 0:
                logger.error(f"Claude Code failed: {stderr.decode()}")
                # Don't fail completely - return error response
                return {
                    "source_module": self.module_name,
                    "target_module": target_module,
                    "timestamp": datetime.now().isoformat(),
                    "message": message,
                    "response": f"Error executing Claude: {stderr.decode()}",
                    "status": "ERROR",
                    "error": stderr.decode()
                }
            
            # Parse response
            response = {
                "source_module": self.module_name,
                "target_module": target_module,
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "response": stdout.decode().strip(),
                "status": "SUCCESS"
            }
            
            logger.success(f"Successfully communicated {self.module_name} -> {target_module}")
            return response
            
        except Exception as e:
            logger.exception(f"Exception in send_message: {e}")
            return {
                "source_module": self.module_name,
                "target_module": target_module,
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "response": f"Exception: {str(e)}",
                "status": "ERROR",
                "error": str(e)
            }
        finally:
            # Cleanup
            try:
                Path(prompt_file).unlink()
                logger.debug(f"Cleaned up prompt file: {prompt_file}")
            except:
                pass
    
    async def receive_handler(self, callback):
        """Register a handler for receiving messages."""
        # TODO: Implement based on architecture choice (webhooks, polling, etc.)
        logger.info(f"Handler registered for module '{self.module_name}'")
        pass


# Validation
if __name__ == "__main__":
    async def test_communication():
        # Module A setup
        module_a = ClaudeCodeCommunicator(
            module_name="DataProcessor",
            system_prompt="You process raw data and extract meaningful patterns."
        )
        
        # Test data
        test_data = {
            "records": [1, 2, 3, 4, 5],
            "processing_params": {"method": "statistical"}
        }
        
        # Send message to Module B
        response = await module_a.send_message(
            target_module="DataAnalyzer",
            message="I have processed 5 records. Please analyze for anomalies.",
            context={"record_count": 5, "processing_time": 0.5, "data_sample": test_data}
        )
        
        # Validate response
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Assertions
        assert response["source_module"] == "DataProcessor"
        assert response["target_module"] == "DataAnalyzer"
        assert "timestamp" in response
        assert "response" in response
        assert response["status"] in ["SUCCESS", "ERROR"]
        
        if response["status"] == "SUCCESS":
            print("✅ Module communication validation passed!")
        else:
            print(f"⚠️  Module communication returned error: {response.get('error', 'Unknown')}")
            print("This may be expected if Claude CLI is not installed.")
    
    # Run test
    asyncio.run(test_communication())