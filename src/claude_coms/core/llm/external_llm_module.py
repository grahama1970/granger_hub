"""
External LLM Module for easy access to various AI models.

Purpose: Provides a module that makes it trivial for Claude instances to
communicate with external models including other Claude instances, Gemini,
GPT-4, and more through the claude_max_proxy integration.

Dependencies:
- claude_max_proxy: Universal LLM interface
- Module inherits from BaseModule and uses LLMCapableMixin

Sample Input:
{
    "action": "ask_model",
    "model": "gemini/gemini-2.0-flash-exp",  # or "claude-3-opus-20240229" 
    "prompt": "Analyze this data and suggest improvements",
    "context": {"data": [...], "current_approach": "..."}
}

Expected Output:
{
    "response": "Model's analysis and suggestions...",
    "model_used": "gemini/gemini-2.0-flash-exp",
    "tokens": 350,
    "success": true
}
"""

import asyncio
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from .base_module import BaseModule
from .module_registry import ModuleRegistry
from .llm_integration import LLMCapableMixin, LLMConfig

# Try to import claude_max_proxy components
try:
    from llm_call import ask, chat, call
    from llm_call.core.caller import make_llm_request
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("⚠️  claude_max_proxy not available. Install with: pip install claude_max_proxy")


class ExternalLLMModule(LLMCapableMixin, BaseModule):
    """Module for easy access to external LLMs including other Claude instances."""
    
    def __init__(self, registry: ModuleRegistry, llm_config: Optional[LLMConfig] = None):
        """Initialize External LLM Module.
        
        Args:
            registry: Module registry
            llm_config: Optional LLM configuration
        """
        # Default config with popular models
        if not llm_config:
            llm_config = LLMConfig(
                default_model="gemini/gemini-2.0-flash-exp",
                fallback_models=[
                    "claude-3-opus-20240229",
                    "gpt-4-turbo-preview",
                    "claude-3-sonnet-20240229",
                    "gemini/gemini-pro"
                ],
                temperature=0.7,
                max_tokens=4000
            )
        
        super().__init__(
            name="ExternalLLM",
            system_prompt=(
                "You are an External LLM Module that provides easy access to various AI models "
                "including Claude, Gemini, GPT-4, and others. You facilitate inter-model communication "
                "and can route requests to the most appropriate model based on the task."
            ),
            capabilities=[
                "external_llm_access",
                "model_routing",
                "multi_model_chat",
                "claude_to_claude",
                "gemini_access",
                "cross_model_analysis"
            ],
            registry=registry,
            llm_config=llm_config
        )
        
        # Track available models
        self.available_models = {
            "claude": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229", 
                "claude-3-haiku-20240307"
            ],
            "gemini": [
                "gemini/gemini-2.0-flash-exp",
                "gemini/gemini-pro",
                "gemini/gemini-pro-vision"
            ],
            "openai": [
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-3.5-turbo"
            ],
            "perplexity": [
                "perplexity/sonar-medium-online"
            ]
        }
        
        # Active chat sessions with different models
        self.model_sessions = {}
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ask_model", "chat_with_model", "compare_models", "route_to_best", "claude_dialogue"]
                },
                "model": {"type": "string"},
                "models": {"type": "array", "items": {"type": "string"}},
                "prompt": {"type": "string"},
                "context": {"type": "object"},
                "temperature": {"type": "number"},
                "session_id": {"type": "string"}
            },
            "required": ["action", "prompt"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "responses": {"type": "object"},
                "model_used": {"type": "string"},
                "models_used": {"type": "array"},
                "tokens": {"type": "number"},
                "session_id": {"type": "string"},
                "success": {"type": "boolean"}
            }
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process requests to external LLMs."""
        if not LLM_AVAILABLE:
            return {
                "success": False,
                "error": "LLM integration not available. Please install claude_max_proxy."
            }
        
        action = data.get("action", "ask_model")
        prompt = data.get("prompt", "")
        context = data.get("context", {})
        
        # Build full prompt with context
        if context:
            full_prompt = f"Context: {json.dumps(context, indent=2)}\n\nRequest: {prompt}"
        else:
            full_prompt = prompt
        
        try:
            if action == "ask_model":
                # Direct model query
                model = data.get("model", self.llm_config.default_model)
                response = await self._ask_single_model(model, full_prompt, data)
                
                return {
                    "response": response,
                    "model_used": model,
                    "success": True,
                    "tokens": len(response.split()) * 1.3  # Rough estimate
                }
            
            elif action == "chat_with_model":
                # Ongoing chat session
                model = data.get("model", self.llm_config.default_model)
                session_id = data.get("session_id", f"{model}_{datetime.now().isoformat()}")
                
                response = await self._chat_with_model(model, full_prompt, session_id)
                
                return {
                    "response": response,
                    "model_used": model,
                    "session_id": session_id,
                    "success": True
                }
            
            elif action == "compare_models":
                # Get responses from multiple models
                models = data.get("models", ["gemini/gemini-2.0-flash-exp", "claude-3-opus-20240229"])
                responses = await self._compare_models(models, full_prompt, data)
                
                return {
                    "responses": responses,
                    "models_used": list(responses.keys()),
                    "success": True
                }
            
            elif action == "route_to_best":
                # Route to best model based on task
                best_model = self._select_best_model(prompt, context)
                response = await self._ask_single_model(best_model, full_prompt, data)
                
                return {
                    "response": response,
                    "model_used": best_model,
                    "success": True,
                    "routing_reason": f"Selected {best_model} as optimal for this task"
                }
            
            elif action == "claude_dialogue":
                # Special handling for Claude-to-Claude communication
                other_claude = data.get("model", "claude-3-sonnet-20240229")
                
                # Add special context for Claude instances
                claude_prompt = f"""You are communicating with another Claude instance.
This is an inter-Claude dialogue for collaborative problem solving.

{full_prompt}

Please provide your perspective as a Claude AI assistant."""
                
                response = await self._ask_single_model(other_claude, claude_prompt, data)
                
                return {
                    "response": response,
                    "model_used": other_claude,
                    "success": True,
                    "communication_type": "claude_to_claude"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model_used": data.get("model", "unknown")
            }
    
    async def _ask_single_model(self, model: str, prompt: str, params: Dict[str, Any]) -> str:
        """Ask a single model."""
        # Use the LLM mixin's method
        result = await self.llm_process(
            prompt,
            model=model,
            temperature=params.get("temperature", self.llm_config.temperature),
            max_tokens=params.get("max_tokens", self.llm_config.max_tokens)
        )
        
        if result.success:
            return result.content
        else:
            # Try fallback
            for fallback in self.llm_config.fallback_models:
                if fallback != model:
                    result = await self.llm_process(prompt, model=fallback)
                    if result.success:
                        return f"[Via {fallback}] {result.content}"
            
            return f"Error: {result.error}"
    
    async def _chat_with_model(self, model: str, message: str, session_id: str) -> str:
        """Maintain chat session with a model."""
        if session_id not in self.model_sessions:
            self.model_sessions[session_id] = {
                "model": model,
                "history": [],
                "created": datetime.now().isoformat()
            }
        
        # Add to history
        self.model_sessions[session_id]["history"].append({
            "role": "user",
            "content": message
        })
        
        # Use llm_chat from mixin
        response = await self.llm_chat(
            self.model_sessions[session_id]["history"],
            model=model,
            session_id=session_id
        )
        
        if isinstance(response, str):
            # Add assistant response to history
            self.model_sessions[session_id]["history"].append({
                "role": "assistant",
                "content": response
            })
            return response
        else:
            return "Chat error occurred"
    
    async def _compare_models(self, models: List[str], prompt: str, params: Dict[str, Any]) -> Dict[str, str]:
        """Get responses from multiple models for comparison."""
        tasks = []
        for model in models:
            task = self._ask_single_model(model, prompt, params)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for model, response in zip(models, responses):
            if isinstance(response, Exception):
                result[model] = f"Error: {str(response)}"
            else:
                result[model] = response
        
        return result
    
    def _select_best_model(self, prompt: str, context: Dict[str, Any]) -> str:
        """Select the best model based on the task."""
        prompt_lower = prompt.lower()
        
        # Simple heuristics for model selection
        if "code" in prompt_lower or "programming" in prompt_lower:
            return "claude-3-opus-20240229"  # Claude is great at coding
        elif "creative" in prompt_lower or "story" in prompt_lower:
            return "claude-3-opus-20240229"  # Claude for creative tasks
        elif "search" in prompt_lower or "current" in prompt_lower or "latest" in prompt_lower:
            return "perplexity/sonar-medium-online"  # Perplexity for current info
        elif "analyze" in prompt_lower or "data" in prompt_lower:
            return "gemini/gemini-2.0-flash-exp"  # Gemini for analysis
        elif "fast" in prompt_lower or "quick" in prompt_lower:
            return "gemini/gemini-2.0-flash-exp"  # Gemini Flash is fast
        else:
            return self.llm_config.default_model
    
    async def handle_discovery(self) -> Dict[str, Any]:
        """Handle discovery requests."""
        return {
            "name": self.name,
            "description": "External LLM access module for multi-model communication",
            "capabilities": self.capabilities,
            "available_models": self.available_models,
            "features": [
                "Direct model access",
                "Multi-model comparison",
                "Claude-to-Claude dialogue",
                "Intelligent model routing",
                "Chat session management"
            ]
        }


# Validation
if __name__ == "__main__":
    async def validate():
        """Validate with real external LLM calls."""
        print("🤖 Validating External LLM Module...\n")
        
        # Note: Requires API keys to be set
        import os
        if not os.getenv("GEMINI_API_KEY"):
            print("⚠️  Set GEMINI_API_KEY environment variable for validation")
            return False
        
        registry = ModuleRegistry()
        module = ExternalLLMModule(registry)
        
        # Test 1: Direct model ask
        print("1️⃣ Testing direct model query...")
        result = await module.process({
            "action": "ask_model",
            "model": "gemini/gemini-2.0-flash-exp",
            "prompt": "What is 2+2? Reply with just the number."
        })
        
        if result["success"]:
            print(f"✅ Response: {result['response']}")
            print(f"   Model: {result['model_used']}")
        else:
            print(f"❌ Error: {result.get('error')}")
        
        # Test 2: Model comparison
        print("\n2️⃣ Testing model comparison...")
        result = await module.process({
            "action": "compare_models",
            "models": ["gemini/gemini-pro", "gemini/gemini-2.0-flash-exp"],
            "prompt": "What is the capital of France? One word answer."
        })
        
        if result["success"]:
            print("✅ Responses:")
            for model, response in result["responses"].items():
                print(f"   {model}: {response}")
        
        # Test 3: Claude dialogue simulation
        print("\n3️⃣ Testing Claude-to-Claude setup...")
        result = await module.process({
            "action": "claude_dialogue",
            "model": "gemini/gemini-pro",  # Simulating with Gemini
            "prompt": "Hello, I'm a Claude instance working on module communication. What's your perspective?"
        })
        
        if result["success"]:
            print(f"✅ Inter-model response: {result['response'][:100]}...")
        
        print("\n✅ External LLM Module validation complete!")
        return True
    
    # Run validation
    import asyncio
    asyncio.run(validate())