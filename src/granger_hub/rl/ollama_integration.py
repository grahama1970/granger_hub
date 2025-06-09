"""
Module: ollama_integration.py
Description: Implementation of ollama integration functionality

External Dependencies:
- requests: https://requests.readthedocs.io/
- dataclasses: [Documentation URL]

Sample Input:
>>> # Add specific examples based on module functionality

Expected Output:
>>> # Add expected output examples

Example Usage:
>>> # Add usage examples
"""

# granger_hub/rl/ollama_integration.py
"""
Ollama integration for RL training in Granger Hub.

This module provides direct integration with the local Ollama server
for reinforcement learning tasks.
"""

import requests
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)


@dataclass
class OllamaConfig:
    """Configuration for Ollama server."""
    host: str = "localhost"
    port: int = 11434
    model: str = "auto"  # Auto-select best available model
    preferred_models: List[str] = None  # Preferred models in order
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30  # Reasonable timeout
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        if self.preferred_models is None:
            # Order of preference for RL tasks
            self.preferred_models = [
                "qwen3:30b-a3b-q8_0",  # Best for RL if available
                "codellama:latest",     # Good for code/logic tasks
                "qwen2.5:3b-instruct",  # Decent general purpose
                "phi3:mini",            # Fallback option
            ]
    
    @property
    def base_url(self) -> str:
        """Get the base URL for Ollama API."""
        return f"http://{self.host}:{self.port}"
    
    @property
    def external_url(self) -> str:
        """Get the external URL for accessing from outside."""
        return "http://192.168.86.49:11434"


class OllamaClient:
    """Client for interacting with Ollama server."""
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.available_models = []
        self._select_best_model()
        self._verify_connection()
    
    def _select_best_model(self):
        """Auto-select the best available model."""
        try:
            response = requests.get(f"{self.config.base_url}/api/tags")
            models = response.json().get('models', [])
            self.available_models = [m['name'] for m in models]
            
            if self.config.model == "auto":
                # Find the best available model from preferred list
                for preferred in self.config.preferred_models:
                    if preferred in self.available_models:
                        self.config.model = preferred
                        logger.info(f"Auto-selected model: {preferred}")
                        break
                else:
                    # Use first available model as fallback
                    if self.available_models:
                        self.config.model = self.available_models[0]
                        logger.warning(f"Using fallback model: {self.config.model}")
                    else:
                        raise Exception("No Ollama models available")
            
        except Exception as e:
            logger.error(f"Failed to query Ollama models: {e}")
            # Use a safe default
            self.config.model = "qwen2.5:3b-instruct"
            
    def _verify_connection(self):
        """Verify connection to Ollama server."""
        try:
            if self.config.model not in self.available_models and self.available_models:
                logger.warning(f"Model {self.config.model} not found. Available: {self.available_models}")
                logger.info(f"Pull the model with: ollama pull {self.config.model}")
            else:
                logger.info(f"Connected to Ollama. Using model: {self.config.model}")
                
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            logger.info("Ensure Ollama is running and accessible")
    
    def generate(self, prompt: str, 
                 system_prompt: Optional[str] = None,
                 temperature: Optional[float] = None,
                 format: Optional[str] = None,
                 retry_on_error: bool = True) -> Dict[str, Any]:
        """
        Generate a response from Ollama.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            format: Response format (e.g., 'json')
            
        Returns:
            Dict with response and metadata
        """
        url = f"{self.config.base_url}/api/generate"
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "temperature": temperature or self.config.temperature,
            "options": {
                "num_predict": self.config.max_tokens,
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        if format:
            payload["format"] = format
        
        last_error = None
        attempts = self.config.retry_attempts if retry_on_error else 1
        
        for attempt in range(attempts):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout,
                    stream=False
                )
                response.raise_for_status()
                
                result = response.json()
                
                return {
                    "response": result.get("response", ""),
                    "model": result.get("model", self.config.model),
                    "total_duration": result.get("total_duration", 0),
                    "prompt_eval_count": result.get("prompt_eval_count", 0),
                    "eval_count": result.get("eval_count", 0),
                }
                
            except requests.exceptions.Timeout:
                last_error = f"Timeout after {self.config.timeout}s"
                logger.warning(f"Ollama request timed out (attempt {attempt + 1}/{attempts})")
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Ollama generation failed (attempt {attempt + 1}/{attempts}): {e}")
            
            if attempt < attempts - 1:
                time.sleep(self.config.retry_delay)
        
        logger.error(f"All Ollama attempts failed: {last_error}")
        return {"response": "", "error": last_error}
    
    def generate_route_optimization(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate optimized route using Ollama for RL training.
        
        Args:
            task: Routing task with source, target, constraints
            
        Returns:
            Optimized route with reasoning
        """
        system_prompt = """You are an expert at optimizing communication routes between modules.
Your goal is to find the most efficient path considering latency, reliability, and schema compatibility.
Always provide your reasoning before the route."""
        
        prompt = f"""Find the optimal communication route for this task:

Source Module: {task.get('source')}
Target Module: {task.get('target')}
Constraints: {json.dumps(task.get('constraints', {}), indent=2)}

Available context:
{json.dumps(task.get('graph_context', {}), indent=2)}

Think step by step:
1. Analyze the requirements
2. Consider available paths
3. Evaluate trade-offs
4. Choose the optimal route

Respond with JSON in this format:
{{
    "reasoning": "your detailed reasoning",
    "route": ["module1", "module2", ..., "target"],
    "expected_latency_ms": <number>,
    "expected_success_rate": <number between 0 and 1>
}}"""
        
        result = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more consistent routing
            format="json"
        )
        
        if result.get("error"):
            logger.warning(f"Route optimization failed: {result['error']}")
            return self._get_fallback_route(task)
            
        try:
            # Try to parse JSON response
            response_text = result.get("response", "")
            if response_text:
                # Clean up response if needed
                response_text = response_text.strip()
                # Find JSON in response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    response_data = json.loads(json_text)
                    return response_data
            
            logger.warning("Empty or invalid JSON response")
            return self._get_fallback_route(task)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return self._get_fallback_route(task)
    
    def _get_fallback_route(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a reasonable fallback route."""
        # Check if there's a suggested better path in context
        context = task.get('graph_context', {})
        paths = context.get('available_paths', [])
        
        if paths:
            # Sort by latency and pick the best
            best_path = min(paths, key=lambda p: p.get('latency', float('inf')))
            return {
                "reasoning": "Selected lowest latency path (fallback)",
                "route": best_path.get('path', [task["source"], task["target"]]),
                "expected_latency_ms": best_path.get('latency', 100),
                "expected_success_rate": 0.85
            }
        
        # Default direct route
        return {
            "reasoning": "Direct connection (fallback)",
            "route": [task["source"], task["target"]],
            "expected_latency_ms": 100,
            "expected_success_rate": 0.8
        }
    
    def generate_schema_adaptation(self, source_schema: Dict, 
                                  target_schema: Dict,
                                  sample_data: Any) -> Dict[str, Any]:
        """
        Generate schema adaptation strategy using Ollama.
        
        Args:
            source_schema: Output schema from source module
            target_schema: Input schema expected by target
            sample_data: Sample data to transform
            
        Returns:
            Adaptation strategy with transformation code
        """
        system_prompt = """You are an expert at data schema transformation.
Your goal is to transform data from one schema to another while preserving as much information as possible."""
        
        prompt = f"""Create a schema transformation strategy:

Source Schema:
{json.dumps(source_schema, indent=2)}

Target Schema:
{json.dumps(target_schema, indent=2)}

Sample Data:
{json.dumps(sample_data, indent=2)}

Provide a transformation strategy that:
1. Maps fields appropriately
2. Handles type conversions
3. Preserves data integrity
4. Minimizes information loss

Respond with JSON:
{{
    "strategy": "description of transformation approach",
    "field_mappings": {{
        "source_field": "target_field",
        ...
    }},
    "transformations": [
        {{"field": "field_name", "operation": "description"}},
        ...
    ],
    "data_preservation_rate": <number between 0 and 1>,
    "complexity": <number 1-10>
}}"""
        
        result = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,  # Very low temperature for consistent transformations
            format="json"
        )
        
        if result.get("error"):
            logger.warning(f"Schema adaptation failed: {result['error']}")
            return self._get_fallback_adaptation(source_schema, target_schema)
            
        try:
            response_text = result.get("response", "")
            if response_text:
                # Extract JSON from response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    return json.loads(json_text)
            
            return self._get_fallback_adaptation(source_schema, target_schema)
            
        except json.JSONDecodeError:
            return self._get_fallback_adaptation(source_schema, target_schema)
    
    def _get_fallback_adaptation(self, source_schema: Dict, target_schema: Dict) -> Dict[str, Any]:
        """Generate a reasonable fallback adaptation strategy."""
        # Try to match fields by similarity
        source_props = source_schema.get('properties', {})
        target_props = target_schema.get('properties', {})
        
        field_mappings = {}
        for s_field in source_props:
            for t_field in target_props:
                if s_field.lower() in t_field.lower() or t_field.lower() in s_field.lower():
                    field_mappings[s_field] = t_field
                    break
        
        return {
            "strategy": "Field name similarity matching (fallback)",
            "field_mappings": field_mappings,
            "transformations": [],
            "data_preservation_rate": len(field_mappings) / max(len(source_props), 1),
            "complexity": 3
        }
    
    def generate_module_selection(self, task_description: str,
                                 available_modules: List[Dict]) -> Dict[str, Any]:
        """
        Generate module selection strategy using Ollama.
        
        Args:
            task_description: Description of the task
            available_modules: List of available modules with capabilities
            
        Returns:
            Module selection with reasoning
        """
        system_prompt = """You are an expert at selecting optimal modules for complex tasks.
Consider module capabilities, load, and task requirements to make the best selection."""
        
        modules_info = "\n".join([
            f"- {m['name']}: {m.get('capabilities', [])} (load: {m.get('current_load', 0)}%)"
            for m in available_modules
        ])
        
        prompt = f"""Select the optimal modules for this task:

Task: {task_description}

Available Modules:
{modules_info}

Consider:
1. Module capabilities vs task requirements
2. Current load and availability
3. Potential for parallel processing
4. Efficiency and resource usage

Respond with JSON:
{{
    "reasoning": "detailed selection reasoning",
    "selected_modules": ["module1", "module2", ...],
    "execution_order": "sequential|parallel|mixed",
    "expected_efficiency": <number 0-1>,
    "alternative_modules": ["backup1", "backup2", ...]
}}"""
        
        result = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4,
            format="json"
        )
        
        if result.get("error"):
            logger.warning(f"Module selection failed: {result['error']}")
            return self._get_fallback_selection(task_description, available_modules)
            
        try:
            response_text = result.get("response", "")
            if response_text:
                # Extract JSON from response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    return json.loads(json_text)
            
            return self._get_fallback_selection(task_description, available_modules)
            
        except json.JSONDecodeError:
            return self._get_fallback_selection(task_description, available_modules)
    
    def _get_fallback_selection(self, task_description: str, available_modules: List[Dict]) -> Dict[str, Any]:
        """Generate a reasonable fallback module selection."""
        if not available_modules:
            return {
                "reasoning": "No modules available (fallback)",
                "selected_modules": [],
                "execution_order": "sequential",
                "expected_efficiency": 0,
                "alternative_modules": []
            }
        
        # Simple heuristic: select modules with lowest load
        sorted_modules = sorted(available_modules, key=lambda m: m.get('current_load', 100))
        selected = sorted_modules[:2] if len(sorted_modules) > 1 else sorted_modules
        
        return {
            "reasoning": "Selected modules with lowest load (fallback)",
            "selected_modules": [m['name'] for m in selected],
            "execution_order": "sequential",
            "expected_efficiency": 0.7,
            "alternative_modules": [m['name'] for m in sorted_modules[2:4]] if len(sorted_modules) > 2 else []
        }


# Singleton instance for easy access
_ollama_client = None

def get_ollama_client(config: Optional[OllamaConfig] = None) -> OllamaClient:
    """Get or create the Ollama client singleton."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient(config)
    return _ollama_client


def get_model_capabilities() -> Dict[str, Dict[str, Any]]:
    """Get capabilities of available Ollama models."""
    return {
        "qwen3:30b-a3b-q8_0": {
            "size": "30B",
            "strengths": ["complex reasoning", "optimization", "analysis"],
            "context_length": 8192,
            "recommended_for": ["route_optimization", "complex_adaptations"]
        },
        "codellama:latest": {
            "size": "7B",
            "strengths": ["code generation", "schema transformation", "logic"],
            "context_length": 4096,
            "recommended_for": ["schema_adaptation", "code_transformations"]
        },
        "qwen2.5:3b-instruct": {
            "size": "3B",
            "strengths": ["fast inference", "instruction following", "general tasks"],
            "context_length": 4096,
            "recommended_for": ["module_selection", "quick_decisions"]
        },
        "phi3:mini": {
            "size": "3.8B",
            "strengths": ["efficiency", "reasoning", "small footprint"],
            "context_length": 4096,
            "recommended_for": ["fallback", "simple_routing"]
        }
    }
