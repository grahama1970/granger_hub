"""
Service Discovery and Health Monitoring.
Module: __init__.py
Description: Package initialization and exports

This module provides automatic service discovery, health checking,
and failover capabilities for the Granger Hub.
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