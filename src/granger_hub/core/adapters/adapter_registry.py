"""
Adapter Registry and Factory for Protocol Adapters.

Purpose: Provides centralized registration and creation of protocol adapters,
enabling dynamic adapter selection based on protocol type.

External Dependencies: None (uses only internal adapters)

Example Usage:
>>> registry = AdapterRegistry()
>>> registry.register("cli", CLIAdapter)
>>> adapter = registry.create("cli", config, command="ls")
"""

from typing import Dict, Type, Any, Optional, List
from dataclasses import dataclass
import importlib
import logging

from .base_adapter import ProtocolAdapter, AdapterConfig
from .cli_adapter import CLIAdapter
from .rest_adapter import RESTAdapter
from .mcp_adapter import MCPAdapter

logger = logging.getLogger(__name__)


@dataclass
class AdapterInfo:
    """Information about a registered adapter."""
    protocol: str
    adapter_class: Type[ProtocolAdapter]
    description: str
    required_params: List[str]
    optional_params: List[str]


class AdapterRegistry:
    """Registry for protocol adapters."""
    
    def __init__(self):
        """Initialize adapter registry with built-in adapters."""
        self._adapters: Dict[str, AdapterInfo] = {}
        self._register_builtin_adapters()
        
    def _register_builtin_adapters(self):
        """Register built-in protocol adapters."""
        # CLI Adapter
        self.register(
            protocol="cli",
            adapter_class=CLIAdapter,
            description="Execute command-line tools and parse output",
            required_params=["command"],
            optional_params=["working_dir"]
        )
        
        # REST Adapter
        self.register(
            protocol="rest",
            adapter_class=RESTAdapter,
            description="Communicate with REST APIs via HTTP",
            required_params=["base_url"],
            optional_params=["headers", "auth"]
        )
        
        # MCP Adapter
        self.register(
            protocol="mcp",
            adapter_class=MCPAdapter,
            description="Communicate with MCP (Model Context Protocol) servers",
            required_params=[],
            optional_params=["server_url", "transport"]
        )
        
    def register(self, protocol: str, adapter_class: Type[ProtocolAdapter],
                 description: str = "", required_params: List[str] = None,
                 optional_params: List[str] = None) -> bool:
        """Register a new protocol adapter.
        
        Args:
            protocol: Protocol identifier (e.g., 'cli', 'rest', 'mcp')
            adapter_class: Adapter class that extends ProtocolAdapter
            description: Human-readable description
            required_params: List of required constructor parameters
            optional_params: List of optional constructor parameters
            
        Returns:
            True if registered successfully
        """
        if not issubclass(adapter_class, ProtocolAdapter):
            raise ValueError(f"{adapter_class} must inherit from ProtocolAdapter")
            
        self._adapters[protocol.lower()] = AdapterInfo(
            protocol=protocol.lower(),
            adapter_class=adapter_class,
            description=description,
            required_params=required_params or [],
            optional_params=optional_params or []
        )
        
        logger.info(f"Registered adapter for protocol: {protocol}")
        return True
        
    def unregister(self, protocol: str) -> bool:
        """Unregister a protocol adapter.
        
        Args:
            protocol: Protocol identifier
            
        Returns:
            True if unregistered successfully
        """
        if protocol.lower() in self._adapters:
            del self._adapters[protocol.lower()]
            logger.info(f"Unregistered adapter for protocol: {protocol}")
            return True
        return False
        
    def get_adapter_info(self, protocol: str) -> Optional[AdapterInfo]:
        """Get information about a registered adapter.
        
        Args:
            protocol: Protocol identifier
            
        Returns:
            AdapterInfo or None if not found
        """
        return self._adapters.get(protocol.lower())
        
    def list_protocols(self) -> List[str]:
        """List all registered protocols.
        
        Returns:
            List of protocol identifiers
        """
        return list(self._adapters.keys())
        
    def create(self, protocol: str, config: AdapterConfig, **kwargs) -> ProtocolAdapter:
        """Create an adapter instance.
        
        Args:
            protocol: Protocol identifier
            config: Adapter configuration
            **kwargs: Additional parameters for adapter constructor
            
        Returns:
            Configured adapter instance
            
        Raises:
            ValueError: If protocol not registered or required params missing
        """
        adapter_info = self.get_adapter_info(protocol)
        if not adapter_info:
            raise ValueError(
                f"Unknown protocol: {protocol}. "
                f"Available: {', '.join(self.list_protocols())}"
            )
            
        # Check required parameters
        missing_params = []
        for param in adapter_info.required_params:
            if param not in kwargs:
                missing_params.append(param)
                
        if missing_params:
            raise ValueError(
                f"Missing required parameters for {protocol} adapter: "
                f"{', '.join(missing_params)}"
            )
            
        # Create adapter instance
        try:
            adapter = adapter_info.adapter_class(config, **kwargs)
            logger.info(f"Created {protocol} adapter: {config.name}")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to create {protocol} adapter: {e}")
            raise


class AdapterFactory:
    """Factory for creating protocol adapters with automatic protocol detection."""
    
    def __init__(self, registry: Optional[AdapterRegistry] = None):
        """Initialize factory with optional custom registry.
        
        Args:
            registry: Custom adapter registry (uses default if None)
        """
        self.registry = registry or AdapterRegistry()
        
    def create_from_url(self, url: str, config: Optional[AdapterConfig] = None,
                        **kwargs) -> ProtocolAdapter:
        """Create adapter based on URL scheme.
        
        Args:
            url: URL with protocol scheme (e.g., "rest://api.example.com")
            config: Optional adapter configuration
            **kwargs: Additional adapter parameters
            
        Returns:
            Configured adapter instance
        """
        # Parse protocol from URL
        if "://" in url:
            protocol, rest = url.split("://", 1)
            
            # Handle special cases
            if protocol in ["http", "https"]:
                protocol = "rest"
                kwargs["base_url"] = url
            elif protocol == "cli":
                kwargs["command"] = rest
            elif protocol == "mcp":
                kwargs["server_url"] = rest if rest else None
        else:
            raise ValueError(f"Invalid URL format: {url}")
            
        # Create default config if not provided
        if not config:
            config = AdapterConfig(
                name=f"{protocol}_adapter",
                protocol=protocol
            )
            
        return self.registry.create(protocol, config, **kwargs)
        
    def create_for_module(self, module_info: Dict[str, Any],
                          config: Optional[AdapterConfig] = None) -> ProtocolAdapter:
        """Create adapter based on module information.
        
        Args:
            module_info: Module information including protocol hints
            config: Optional adapter configuration
            
        Returns:
            Configured adapter instance
        """
        # Detect protocol from module info
        if "protocol" in module_info:
            protocol = module_info["protocol"]
        elif "command" in module_info:
            protocol = "cli"
        elif "base_url" in module_info or "api_endpoint" in module_info:
            protocol = "rest"
        elif "mcp_server" in module_info:
            protocol = "mcp"
        else:
            raise ValueError("Cannot detect protocol from module info")
            
        # Extract adapter parameters
        params = {}
        if protocol == "cli":
            params["command"] = module_info.get("command")
            params["working_dir"] = module_info.get("working_dir")
        elif protocol == "rest":
            params["base_url"] = module_info.get("base_url") or module_info.get("api_endpoint")
            params["headers"] = module_info.get("headers")
        elif protocol == "mcp":
            params["server_url"] = module_info.get("mcp_server")
            params["transport"] = module_info.get("transport", "stdio")
            
        # Create config if not provided
        if not config:
            config = AdapterConfig(
                name=module_info.get("name", f"{protocol}_adapter"),
                protocol=protocol,
                metadata=module_info
            )
            
        return self.registry.create(protocol, config, **params)


# Global registry instance
default_registry = AdapterRegistry()

# Convenience functions
def register_adapter(protocol: str, adapter_class: Type[ProtocolAdapter], **kwargs):
    """Register an adapter with the default registry."""
    return default_registry.register(protocol, adapter_class, **kwargs)

def create_adapter(protocol: str, config: AdapterConfig, **kwargs):
    """Create an adapter using the default registry."""
    return default_registry.create(protocol, config, **kwargs)

def list_protocols():
    """List all registered protocols."""
    return default_registry.list_protocols()


# Validation
if __name__ == "__main__":
    import asyncio
    
    async def test_registry():
        """Test adapter registry and factory."""
        registry = AdapterRegistry()
        factory = AdapterFactory(registry)
        
        # Test protocol listing
        protocols = registry.list_protocols()
        assert "cli" in protocols
        assert "rest" in protocols
        assert "mcp" in protocols
        print(f" Registered protocols: {protocols}")
        
        # Test CLI adapter creation
        config = AdapterConfig(name="test_cli", protocol="cli")
        cli_adapter = registry.create("cli", config, command="echo test")
        assert isinstance(cli_adapter, CLIAdapter)
        print(" Created CLI adapter")
        
        # Test REST adapter creation
        config = AdapterConfig(name="test_rest", protocol="rest")
        rest_adapter = registry.create("rest", config, base_url="https://api.example.com")
        assert isinstance(rest_adapter, RESTAdapter)
        print(" Created REST adapter")
        
        # Test factory URL parsing
        adapter = factory.create_from_url("https://api.example.com/v1")
        assert isinstance(adapter, RESTAdapter)
        print(" Factory created REST adapter from URL")
        
        # Test factory module detection
        module_info = {
            "name": "test_module",
            "command": "test-cli --json",
            "working_dir": "/tmp"
        }
        adapter = factory.create_for_module(module_info)
        assert isinstance(adapter, CLIAdapter)
        print(" Factory detected CLI protocol from module info")
        
        # Test missing required params
        try:
            registry.create("cli", config)  # Missing 'command'
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Missing required parameters" in str(e)
            print(" Correctly validated required parameters")
            
        return True
        
    # Run test
    result = asyncio.run(test_registry())
    assert result == True
    print("\n Adapter registry validation passed!")