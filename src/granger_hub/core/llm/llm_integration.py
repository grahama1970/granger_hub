"""
LLM Integration for Granger Hub.

Purpose: Provides integration with claude_max_proxy to enable modules to make
LLM calls to various providers including Gemini, Claude, GPT, etc.

Third-party packages:
- claude_max_proxy: Universal LLM interface
- llm_call: Main API from claude_max_proxy

Sample Input:
- prompt: "Analyze this module communication pattern"
- model: "gemini/gemini-pro" or "claude-3-opus-20240229"
- context: {"module": "data_processor", "pattern": "hub_spoke"}

Expected Output:
- LLM response with analysis, recommendations, or generated content
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import json
from datetime import datetime
from enum import Enum

try:
    from llm_call import ask, chat, call
    from llm_call.core.caller import make_llm_request
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning("claude_max_proxy not available. LLM features disabled.")

logger = logging.getLogger(__name__)


class LLMModel(Enum):
    """Available LLM models."""
    # Claude models
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    
    # Gemini models
    GEMINI_PRO = "gemini/gemini-pro"
    GEMINI_FLASH = "gemini/gemini-2.0-flash-exp"
    
    # GPT models
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_35_TURBO = "gpt-3.5-turbo"


@dataclass
class LLMRequest:
    """Request structure for LLM calls."""
    prompt: str
    model: Union[str, LLMModel]
    context: Optional[Dict[str, Any]] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    def model_string(self) -> str:
        """Get model as string."""
        return self.model.value if isinstance(self.model, LLMModel) else self.model


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    default_model: str = "gemini/gemini-pro"
    fallback_models: List[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30
    retry_count: int = 3
    validate_json: bool = False
    
    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = [
                "gpt-4-turbo-preview",
                "claude-3-haiku-20240307"
            ]


class LLMIntegration:
    """Provides LLM capabilities to modules."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM integration.
        
        Args:
            config: LLM configuration
        """
        self.config = config or LLMConfig()
        self.usage_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "tokens_used": 0,
            "by_model": {}
        }
        self._chat_sessions = {}
    
    async def ask(self, 
                  prompt: str,
                  model: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None,
                  temperature: Optional[float] = None,
                  max_tokens: Optional[int] = None,
                  validate_json: Optional[bool] = None) -> Optional[str]:
        """Make a simple LLM request.
        
        Args:
            prompt: The prompt to send
            model: Model to use (defaults to config.default_model)
            context: Additional context to prepend to prompt
            temperature: Override temperature
            max_tokens: Override max tokens
            validate_json: Whether to validate JSON response
            
        Returns:
            LLM response or None if failed
        """
        if not LLM_AVAILABLE:
            logger.error("LLM integration not available")
            return None
        
        model = model or self.config.default_model
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens
        validate_json = validate_json if validate_json is not None else self.config.validate_json
        
        # Build full prompt with context
        full_prompt = prompt
        if context:
            context_str = f"Context:\n{json.dumps(context, indent=2)}\n\n"
            full_prompt = context_str + prompt
        
        # Try primary model
        try:
            self.usage_stats["total_calls"] += 1
            
            validation = ["json"] if validate_json else []
            
            response = await ask(
                prompt=full_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                validate=validation,
                timeout=self.config.timeout
            )
            
            self.usage_stats["successful_calls"] += 1
            self.usage_stats["by_model"][model] = self.usage_stats["by_model"].get(model, 0) + 1
            
            logger.debug(f"LLM call successful with {model}")
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed with {model}: {e}")
            
            # Try fallback models
            for fallback_model in self.config.fallback_models:
                try:
                    logger.info(f"Trying fallback model: {fallback_model}")
                    
                    response = await ask(
                        prompt=full_prompt,
                        model=fallback_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        validate=validation,
                        timeout=self.config.timeout
                    )
                    
                    self.usage_stats["successful_calls"] += 1
                    self.usage_stats["by_model"][fallback_model] = self.usage_stats["by_model"].get(fallback_model, 0) + 1
                    
                    logger.info(f"Fallback successful with {fallback_model}")
                    return response
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback {fallback_model} failed: {fallback_error}")
                    continue
            
            self.usage_stats["failed_calls"] += 1
            return None
    
    async def analyze_module_communication(self,
                                         communication_data: Dict[str, Any],
                                         analysis_type: str = "general") -> Optional[Dict[str, Any]]:
        """Analyze module communication patterns using LLM.
        
        Args:
            communication_data: Communication data to analyze
            analysis_type: Type of analysis (general, performance, anomaly, optimization)
            
        Returns:
            Analysis results
        """
        prompts = {
            "general": """Analyze this module communication data and provide insights:
1. What patterns do you observe?
2. Are there any potential issues?
3. What optimizations would you recommend?

Data: {data}

Provide response as JSON with keys: patterns, issues, recommendations""",
            
            "performance": """Analyze the performance characteristics of this module communication:
1. Identify bottlenecks
2. Calculate efficiency metrics
3. Suggest performance improvements

Data: {data}

Provide response as JSON with keys: bottlenecks, metrics, improvements""",
            
            "anomaly": """Detect anomalies in this module communication pattern:
1. Identify unusual behaviors
2. Flag potential security concerns
3. Highlight deviations from normal patterns

Data: {data}

Provide response as JSON with keys: anomalies, security_concerns, deviations""",
            
            "optimization": """Suggest optimizations for this module communication graph:
1. Recommend new connections
2. Suggest modules to remove or consolidate
3. Propose architectural improvements

Data: {data}

Provide response as JSON with keys: new_connections, consolidations, architecture_improvements"""
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        prompt = prompt.format(data=json.dumps(communication_data, indent=2))
        
        response = await self.ask(
            prompt=prompt,
            model="gemini/gemini-pro",  # Gemini is good for analysis
            temperature=0.3,  # Lower temperature for analysis
            validate_json=True
        )
        
        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"error": "Failed to parse LLM response", "raw_response": response}
        return None
    
    async def generate_module_recommendations(self,
                                            requirements: Dict[str, Any],
                                            existing_modules: List[str]) -> Optional[List[Dict[str, Any]]]:
        """Generate module recommendations based on requirements.
        
        Args:
            requirements: System requirements and constraints
            existing_modules: List of existing module names
            
        Returns:
            List of recommended modules
        """
        prompt = f"""Based on the following system requirements and existing modules, recommend new modules that would enhance the system:

Requirements:
{json.dumps(requirements, indent=2)}

Existing Modules:
{json.dumps(existing_modules, indent=2)}

For each recommended module, provide:
1. name: Module name
2. purpose: What it does
3. capabilities: List of capabilities
4. connections: Which existing modules it should connect to
5. rationale: Why this module is needed

Provide response as JSON array of module recommendations."""
        
        response = await self.ask(
            prompt=prompt,
            model="gpt-4-turbo-preview",  # GPT-4 for creative recommendations
            temperature=0.8,
            validate_json=True
        )
        
        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return None
        return None
    
    async def explain_pattern(self,
                             pattern_data: Dict[str, Any],
                             audience: str = "technical") -> Optional[str]:
        """Explain a communication pattern in natural language.
        
        Args:
            pattern_data: Pattern data to explain
            audience: Target audience (technical, business, simple)
            
        Returns:
            Natural language explanation
        """
        audience_prompts = {
            "technical": "Provide a detailed technical explanation with specific metrics and implementation details.",
            "business": "Explain in business terms focusing on impact, efficiency, and value.",
            "simple": "Explain in simple terms that anyone can understand, avoiding technical jargon."
        }
        
        prompt = f"""Explain this module communication pattern:

{json.dumps(pattern_data, indent=2)}

{audience_prompts.get(audience, audience_prompts["technical"])}"""
        
        return await self.ask(
            prompt=prompt,
            temperature=0.7,
            max_tokens=1000
        )
    
    async def create_chat_session(self,
                                 session_id: str,
                                 model: Optional[str] = None,
                                 system_prompt: Optional[str] = None) -> bool:
        """Create a chat session for ongoing conversations.
        
        Args:
            session_id: Unique session identifier
            model: Model to use
            system_prompt: System prompt for the session
            
        Returns:
            True if session created
        """
        if not LLM_AVAILABLE:
            return False
        
        try:
            model = model or self.config.default_model
            
            # Create chat session with optional system prompt
            if system_prompt:
                session = await chat(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}]
                )
            else:
                session = await chat(model=model)
            
            self._chat_sessions[session_id] = session
            logger.info(f"Created chat session {session_id} with model {model}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create chat session: {e}")
            return False
    
    async def chat(self,
                   session_id: str,
                   message: str) -> Optional[str]:
        """Send a message to a chat session.
        
        Args:
            session_id: Session identifier
            message: Message to send
            
        Returns:
            Response from the chat session
        """
        session = self._chat_sessions.get(session_id)
        if not session:
            logger.error(f"Chat session {session_id} not found")
            return None
        
        try:
            response = await session.send(message)
            return response
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return None
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics.
        
        Returns:
            Usage statistics
        """
        return {
            **self.usage_stats,
            "success_rate": (
                self.usage_stats["successful_calls"] / self.usage_stats["total_calls"]
                if self.usage_stats["total_calls"] > 0 else 0
            ),
            "active_sessions": len(self._chat_sessions)
        }
    
    async def close_chat_session(self, session_id: str):
        """Close a chat session.
        
        Args:
            session_id: Session to close
        """
        if session_id in self._chat_sessions:
            # Chat sessions don't have explicit close in llm_call
            del self._chat_sessions[session_id]
            logger.info(f"Closed chat session {session_id}")


class LLMCapableMixin:
    """Mixin to add LLM capabilities to any module."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._llm = LLMIntegration()
    
    async def llm_analyze(self, 
                         data: Any,
                         analysis_type: str = "general") -> Optional[Dict[str, Any]]:
        """Analyze data using LLM.
        
        Args:
            data: Data to analyze
            analysis_type: Type of analysis
            
        Returns:
            Analysis results
        """
        if isinstance(data, dict):
            return await self._llm.analyze_module_communication(data, analysis_type)
        else:
            # Convert to dict for analysis
            analysis_data = {"data": str(data), "type": type(data).__name__}
            return await self._llm.analyze_module_communication(analysis_data, analysis_type)
    
    async def llm_ask(self,
                      prompt: str,
                      **kwargs) -> Optional[str]:
        """Ask LLM a question.
        
        Args:
            prompt: Question to ask
            **kwargs: Additional arguments for ask()
            
        Returns:
            LLM response
        """
        return await self._llm.ask(prompt, **kwargs)
    
    async def llm_explain(self,
                         data: Any,
                         audience: str = "technical") -> Optional[str]:
        """Explain data in natural language.
        
        Args:
            data: Data to explain
            audience: Target audience
            
        Returns:
            Natural language explanation
        """
        if isinstance(data, dict):
            return await self._llm.explain_pattern(data, audience)
        else:
            # Convert to dict for explanation
            explain_data = {"data": str(data), "type": type(data).__name__}
            return await self._llm.explain_pattern(explain_data, audience)
    
    async def llm_recommend(self,
                           context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Get LLM recommendations.
        
        Args:
            context: Context for recommendations
            
        Returns:
            List of recommendations
        """
        requirements = context.get("requirements", {})
        existing = context.get("existing_modules", [])
        
        return await self._llm.generate_module_recommendations(
            requirements, existing
        )


if __name__ == "__main__":
    # Test the LLM integration
    async def test_llm_integration():
        llm = LLMIntegration()
        
        # Test simple ask
        response = await llm.ask(
            "What are the benefits of modular architecture?",
            model="gemini/gemini-pro"
        )
        print(f"Response: {response[:200]}...")
        
        # Test analysis
        test_data = {
            "modules": ["producer", "processor", "analyzer"],
            "connections": [
                {"from": "producer", "to": "processor", "count": 100},
                {"from": "processor", "to": "analyzer", "count": 95}
            ],
            "success_rate": 0.95
        }
        
        analysis = await llm.analyze_module_communication(test_data, "performance")
        print(f"Analysis: {json.dumps(analysis, indent=2)}")
        
        # Test pattern explanation
        explanation = await llm.explain_pattern(test_data, "simple")
        print(f"Explanation: {explanation}")
        
        # Print usage stats
        print(f"Usage stats: {json.dumps(llm.get_usage_stats(), indent=2)}")
    
    asyncio.run(test_llm_integration())