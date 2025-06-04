"""
LLM Configuration and Setup for Claude Module Communicator.

Purpose: Provides easy configuration and setup for LLM integration
across all modules in the system.

Dependencies:
- pydantic: For configuration validation
- python-dotenv: For environment variable loading
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import json
import logging

# Try to import pydantic for validation
try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object

# Try to import dotenv for environment loading
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    load_dotenv = None

from .llm_integration import LLMConfig, LLMModel

logger = logging.getLogger(__name__)


class LLMProviderConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Configuration for a specific LLM provider."""
    
    if PYDANTIC_AVAILABLE:
        api_key: str = Field(..., description="API key for the provider")
        base_url: Optional[str] = Field(None, description="Optional base URL override")
        organization: Optional[str] = Field(None, description="Optional organization ID")
        default_model: Optional[str] = Field(None, description="Default model for this provider")
        rate_limit: Optional[int] = Field(None, description="Requests per minute limit")
        
        @validator('api_key')
        def validate_api_key(cls, v):
            if not v or v == "your-api-key":
                raise ValueError("Valid API key required")
            return v
    else:
        def __init__(self, api_key: str, base_url: Optional[str] = None,
                     organization: Optional[str] = None, default_model: Optional[str] = None,
                     rate_limit: Optional[int] = None):
            self.api_key = api_key
            self.base_url = base_url
            self.organization = organization
            self.default_model = default_model
            self.rate_limit = rate_limit


class ModuleLLMConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """LLM configuration for a specific module."""
    
    if PYDANTIC_AVAILABLE:
        enabled: bool = Field(True, description="Whether LLM is enabled for this module")
        preferred_model: Optional[LLMModel] = Field(None, description="Preferred model for this module")
        temperature: float = Field(0.7, ge=0, le=2, description="Temperature for this module")
        max_tokens: int = Field(4096, ge=1, description="Max tokens for responses")
        system_prompt_suffix: Optional[str] = Field(None, description="Additional system prompt")
    else:
        def __init__(self, enabled: bool = True, preferred_model: Optional[LLMModel] = None,
                     temperature: float = 0.7, max_tokens: int = 4096,
                     system_prompt_suffix: Optional[str] = None):
            self.enabled = enabled
            self.preferred_model = preferred_model
            self.temperature = temperature
            self.max_tokens = max_tokens
            self.system_prompt_suffix = system_prompt_suffix


class GlobalLLMConfig(BaseModel if PYDANTIC_AVAILABLE else object):
    """Global LLM configuration for the system."""
    
    if PYDANTIC_AVAILABLE:
        providers: Dict[str, LLMProviderConfig] = Field(
            default_factory=dict,
            description="Provider configurations"
        )
        default_provider: str = Field("anthropic", description="Default provider to use")
        default_model: LLMModel = Field(
            LLMModel.CLAUDE_3_HAIKU,
            description="Default model across system"
        )
        module_configs: Dict[str, ModuleLLMConfig] = Field(
            default_factory=dict,
            description="Module-specific configurations"
        )
        global_temperature: float = Field(0.7, ge=0, le=2, description="Global temperature")
        global_max_tokens: int = Field(4096, ge=1, description="Global max tokens")
        retry_attempts: int = Field(3, ge=0, description="Retry attempts on failure")
        timeout_seconds: int = Field(30, ge=1, description="Request timeout")
        enable_caching: bool = Field(True, description="Enable response caching")
        log_requests: bool = Field(False, description="Log all LLM requests")
    else:
        def __init__(self, **kwargs):
            self.providers = kwargs.get('providers', {})
            self.default_provider = kwargs.get('default_provider', 'anthropic')
            self.default_model = kwargs.get('default_model', LLMModel.CLAUDE_3_HAIKU)
            self.module_configs = kwargs.get('module_configs', {})
            self.global_temperature = kwargs.get('global_temperature', 0.7)
            self.global_max_tokens = kwargs.get('global_max_tokens', 4096)
            self.retry_attempts = kwargs.get('retry_attempts', 3)
            self.timeout_seconds = kwargs.get('timeout_seconds', 30)
            self.enable_caching = kwargs.get('enable_caching', True)
            self.log_requests = kwargs.get('log_requests', False)


class LLMConfigManager:
    """Manages LLM configuration for the entire system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path) if config_path else None
        self.config: Optional[GlobalLLMConfig] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file and environment."""
        # Load from environment first
        if DOTENV_AVAILABLE and load_dotenv:
            load_dotenv()
        
        # Initialize with defaults
        config_data = {
            "providers": {},
            "default_provider": "anthropic",
            "default_model": LLMModel.CLAUDE_3_HAIKU
        }
        
        # Load from file if exists
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    config_data.update(file_config)
                logger.info(f"Loaded LLM config from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
        
        # Override with environment variables
        self._load_from_env(config_data)
        
        # Create config object
        if PYDANTIC_AVAILABLE:
            try:
                self.config = GlobalLLMConfig(**config_data)
            except Exception as e:
                logger.error(f"Config validation failed: {e}")
                self.config = GlobalLLMConfig()
        else:
            self.config = GlobalLLMConfig(**config_data)
    
    def _load_from_env(self, config_data: Dict[str, Any]):
        """Load configuration from environment variables."""
        # Load API keys
        if os.getenv("ANTHROPIC_API_KEY"):
            if "providers" not in config_data:
                config_data["providers"] = {}
            config_data["providers"]["anthropic"] = {
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "default_model": "claude-3-haiku-20240307"
            }
        
        if os.getenv("OPENAI_API_KEY"):
            if "providers" not in config_data:
                config_data["providers"] = {}
            config_data["providers"]["openai"] = {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "organization": os.getenv("OPENAI_ORGANIZATION"),
                "default_model": "gpt-4-turbo-preview"
            }
        
        # Load global settings
        if os.getenv("LLM_DEFAULT_PROVIDER"):
            config_data["default_provider"] = os.getenv("LLM_DEFAULT_PROVIDER")
        
        if os.getenv("LLM_DEFAULT_MODEL"):
            try:
                config_data["default_model"] = LLMModel(os.getenv("LLM_DEFAULT_MODEL"))
            except ValueError:
                logger.warning(f"Invalid LLM model in env: {os.getenv('LLM_DEFAULT_MODEL')}")
        
        if os.getenv("LLM_TEMPERATURE"):
            try:
                config_data["global_temperature"] = float(os.getenv("LLM_TEMPERATURE"))
            except ValueError:
                pass
        
        if os.getenv("LLM_MAX_TOKENS"):
            try:
                config_data["global_max_tokens"] = int(os.getenv("LLM_MAX_TOKENS"))
            except ValueError:
                pass
    
    def get_module_config(self, module_name: str) -> LLMConfig:
        """Get LLM configuration for a specific module.
        
        Args:
            module_name: Name of the module
            
        Returns:
            LLM configuration for the module
        """
        if not self.config:
            return LLMConfig()
        
        # Start with global config
        llm_config = LLMConfig(
            default_model=self.config.default_model,
            temperature=self.config.global_temperature,
            max_tokens=self.config.global_max_tokens,
            timeout=self.config.timeout_seconds,
            retry_attempts=self.config.retry_attempts
        )
        
        # Add API keys
        api_keys = {}
        for provider, provider_config in self.config.providers.items():
            if provider == "anthropic":
                api_keys["anthropic"] = provider_config.api_key
            elif provider == "openai":
                api_keys["openai"] = provider_config.api_key
        llm_config.api_keys = api_keys
        
        # Apply module-specific overrides
        if module_name in self.config.module_configs:
            module_config = self.config.module_configs[module_name]
            if not module_config.enabled:
                # Return config with no API keys to disable
                llm_config.api_keys = {}
            else:
                if module_config.preferred_model:
                    llm_config.default_model = module_config.preferred_model
                if module_config.temperature:
                    llm_config.temperature = module_config.temperature
                if module_config.max_tokens:
                    llm_config.max_tokens = module_config.max_tokens
        
        return llm_config
    
    def save_config(self, path: Optional[str] = None):
        """Save configuration to file.
        
        Args:
            path: Optional path override
        """
        save_path = Path(path) if path else self.config_path
        if not save_path:
            logger.warning("No path specified for saving config")
            return
        
        try:
            config_dict = self.config.dict() if PYDANTIC_AVAILABLE else self.config.__dict__
            
            # Convert enums to strings
            if isinstance(config_dict.get("default_model"), LLMModel):
                config_dict["default_model"] = config_dict["default_model"].value
            
            # Don't save API keys
            if "providers" in config_dict:
                for provider in config_dict["providers"].values():
                    if "api_key" in provider:
                        provider["api_key"] = "***"
            
            with open(save_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            logger.info(f"Saved LLM config to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def create_example_config(self, path: str = "llm_config.example.json"):
        """Create an example configuration file.
        
        Args:
            path: Path for example file
        """
        example = {
            "providers": {
                "anthropic": {
                    "api_key": "your-anthropic-api-key",
                    "default_model": "claude-3-haiku-20240307"
                },
                "openai": {
                    "api_key": "your-openai-api-key",
                    "organization": "your-org-id",
                    "default_model": "gpt-4-turbo-preview"
                }
            },
            "default_provider": "anthropic",
            "default_model": "claude-3-haiku-20240307",
            "module_configs": {
                "ArangoExpert": {
                    "enabled": True,
                    "preferred_model": "claude-3-sonnet-20240229",
                    "temperature": 0.3,
                    "max_tokens": 8192,
                    "system_prompt_suffix": "Focus on graph database expertise."
                },
                "DataAnalyzer": {
                    "enabled": True,
                    "preferred_model": "claude-3-opus-20240229",
                    "temperature": 0.5,
                    "max_tokens": 4096
                }
            },
            "global_temperature": 0.7,
            "global_max_tokens": 4096,
            "retry_attempts": 3,
            "timeout_seconds": 30,
            "enable_caching": True,
            "log_requests": False
        }
        
        with open(path, 'w') as f:
            json.dump(example, f, indent=2)
        
        print(f"Created example config at {path}")
        print("Remember to:")
        print("1. Copy to llm_config.json")
        print("2. Add your actual API keys")
        print("3. Or set environment variables:")
        print("   - ANTHROPIC_API_KEY")
        print("   - OPENAI_API_KEY")


# Global configuration instance
_config_manager: Optional[LLMConfigManager] = None


def init_llm_config(config_path: Optional[str] = None) -> LLMConfigManager:
    """Initialize global LLM configuration.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Configuration manager instance
    """
    global _config_manager
    _config_manager = LLMConfigManager(config_path)
    return _config_manager


def get_llm_config(module_name: str) -> LLMConfig:
    """Get LLM configuration for a module.
    
    Args:
        module_name: Name of the module
        
    Returns:
        LLM configuration
    """
    if not _config_manager:
        init_llm_config()
    return _config_manager.get_module_config(module_name)


if __name__ == "__main__":
    # Create example configuration
    manager = LLMConfigManager()
    manager.create_example_config()
    
    # Test loading configuration
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    manager = LLMConfigManager("llm_config.example.json")
    
    # Get module configs
    arango_config = manager.get_module_config("ArangoExpert")
    print(f"ArangoExpert config: {arango_config}")
    
    analyzer_config = manager.get_module_config("DataAnalyzer")
    print(f"DataAnalyzer config: {analyzer_config}")
    
    default_config = manager.get_module_config("UnknownModule")
    print(f"Default config: {default_config}")