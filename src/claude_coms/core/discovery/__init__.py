"""
Service Discovery and Health Monitoring.

This module provides automatic service discovery, health checking,
and failover capabilities for the Claude Module Communicator.
"""

from .service_discovery import (
    ServiceDiscovery,
    ServiceInfo,
    ServiceStatus,
    FailoverStrategy,
    ServiceListener
)

__all__ = [
    "ServiceDiscovery",
    "ServiceInfo", 
    "ServiceStatus",
    "FailoverStrategy",
    "ServiceListener"
]