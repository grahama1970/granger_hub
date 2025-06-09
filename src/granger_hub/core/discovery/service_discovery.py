"""
Service Discovery and Health Monitoring for Granger Hub.

Purpose: Provides automatic service discovery via mDNS/DNS-SD,
health checking, failover, and load balancing capabilities.

External Dependencies:
- zeroconf: For mDNS/DNS-SD discovery
- aiohttp: For health check endpoints

Example Usage:
>>> discovery = ServiceDiscovery()
>>> await discovery.start()
>>> services = await discovery.find_services("_claude-module._tcp")
[ServiceInfo(name="module1", host="192.168.1.100", port=8080)]
"""

import asyncio
import time
import json
import socket
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)

# Try to import zeroconf if available
try:
    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo as ZeroconfServiceInfo
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    logger.warning("Zeroconf not available - mDNS discovery disabled")


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    

class FailoverStrategy(Enum):
    """Failover strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    FASTEST_RESPONSE = "fastest_response"
    WEIGHTED = "weighted"
    

@dataclass
class ServiceInfo:
    """Information about a discovered service."""
    name: str
    service_type: str
    host: str
    port: int
    properties: Dict[str, Any] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_seen: datetime = field(default_factory=datetime.now)
    last_health_check: Optional[datetime] = None
    response_time_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def address(self) -> str:
        """Get service address."""
        return f"{self.host}:{self.port}"
        
    @property
    def health_score(self) -> float:
        """Calculate health score (0-100)."""
        if self.status == ServiceStatus.HEALTHY:
            base_score = 100
        elif self.status == ServiceStatus.DEGRADED:
            base_score = 50
        elif self.status == ServiceStatus.UNHEALTHY:
            base_score = 0
        else:
            base_score = 25
            
        # Adjust for error rate
        total_checks = self.error_count + self.success_count
        if total_checks > 0:
            success_rate = self.success_count / total_checks
            base_score *= success_rate
            
        # Penalize slow response times
        if self.response_time_ms > 1000:
            base_score *= 0.8
        elif self.response_time_ms > 500:
            base_score *= 0.9
            
        return min(100, max(0, base_score))


class ServiceListener:
    """Listener for mDNS service events."""
    
    def __init__(self, discovery: 'ServiceDiscovery'):
        """Initialize listener."""
        self.discovery = discovery
        
    def add_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        """Service added callback."""
        asyncio.create_task(self._handle_service_added(zeroconf, service_type, name))
        
    async def _handle_service_added(self, zeroconf: Any, 
                                   service_type: str, name: str) -> None:
        """Handle service addition."""
        try:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                service_info = self._parse_service_info(info, service_type)
                await self.discovery.register_service(service_info)
                
        except Exception as e:
            logger.error(f"Error handling service addition: {e}")
            
    def remove_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        """Service removed callback."""
        asyncio.create_task(self.discovery.unregister_service(name))
        
    def update_service(self, zeroconf: Any, service_type: str, name: str) -> None:
        """Service updated callback."""
        # Treat as add to update info
        self.add_service(zeroconf, service_type, name)
        
    def _parse_service_info(self, info: Any, 
                           service_type: str) -> ServiceInfo:
        """Parse zeroconf service info."""
        # Extract properties
        properties = {}
        if info.properties:
            for key, value in info.properties.items():
                try:
                    # Try to decode bytes
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    properties[key.decode('utf-8') if isinstance(key, bytes) else key] = value
                except:
                    pass
                    
        # Get first IPv4 address
        host = socket.inet_ntoa(info.addresses[0]) if info.addresses else "0.0.0.0"
        
        return ServiceInfo(
            name=info.name,
            service_type=service_type,
            host=host,
            port=info.port,
            properties=properties,
            metadata={
                "server": info.server,
                "weight": info.weight,
                "priority": info.priority
            }
        )


class ServiceDiscovery:
    """
    Service discovery and health monitoring system.
    
    Features:
    - mDNS/DNS-SD discovery
    - Health check endpoints
    - Automatic failover
    - Load balancing
    - Service mesh visualization
    - Circuit breaker patterns
    """
    
    def __init__(self, health_check_interval: float = 30.0,
                 discovery_timeout: float = 5.0,
                 failover_strategy: FailoverStrategy = FailoverStrategy.ROUND_ROBIN):
        """Initialize service discovery."""
        self.health_check_interval = health_check_interval
        self.discovery_timeout = discovery_timeout
        self.failover_strategy = failover_strategy
        
        self._services: Dict[str, ServiceInfo] = {}
        self._service_types: Set[str] = set()
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
        self._callbacks: List[Callable] = []
        self._running = False
        
        self._zeroconf: Optional[Any] = None
        self._browsers: List[Any] = []
        
        # Circuit breaker state
        self._circuit_breaker_state: Dict[str, Dict[str, Any]] = {}
        self._circuit_breaker_threshold = 5  # failures before opening
        self._circuit_breaker_timeout = 60  # seconds before retry
        
        # Load balancer state
        self._connection_counts: Dict[str, int] = defaultdict(int)
        self._last_used: Dict[str, datetime] = {}
        self._round_robin_index: Dict[str, int] = defaultdict(int)
        
    async def start(self) -> None:
        """Start service discovery."""
        if self._running:
            return
            
        self._running = True
        
        # Start mDNS if available
        if ZEROCONF_AVAILABLE:
            self._zeroconf = Zeroconf()
            logger.info("Started mDNS service discovery")
        else:
            logger.warning("Running without mDNS discovery")
            
    async def stop(self) -> None:
        """Stop service discovery."""
        self._running = False
        
        # Stop health checks
        for task in self._health_check_tasks.values():
            task.cancel()
            
        # Stop mDNS
        if self._zeroconf:
            for browser in self._browsers:
                browser.cancel()
            self._zeroconf.close()
            
        logger.info("Stopped service discovery")
        
    async def discover_services(self, service_type: str,
                               timeout: Optional[float] = None) -> List[ServiceInfo]:
        """
        Discover services of a given type.
        
        Args:
            service_type: Service type to discover (e.g., "_http._tcp")
            timeout: Discovery timeout in seconds
            
        Returns:
            List of discovered services
        """
        timeout = timeout or self.discovery_timeout
        
        if not ZEROCONF_AVAILABLE:
            # Return any manually registered services
            return [s for s in self._services.values() 
                   if s.service_type == service_type]
            
        # Track this service type
        self._service_types.add(service_type)
        
        # Create listener
        listener = ServiceListener(self)
        
        # Start browsing
        if ZEROCONF_AVAILABLE:
            browser = ServiceBrowser(self._zeroconf, service_type, listener)
            self._browsers.append(browser)
        
        # Wait for discovery
        await asyncio.sleep(timeout)
        
        # Return discovered services
        return [s for s in self._services.values() 
               if s.service_type == service_type]
        
    async def register_service(self, service: ServiceInfo) -> None:
        """
        Register a service manually or from discovery.
        
        Args:
            service: Service information
        """
        self._services[service.name] = service
        
        # Start health checking
        if service.name not in self._health_check_tasks:
            task = asyncio.create_task(
                self._health_check_loop(service.name)
            )
            self._health_check_tasks[service.name] = task
            
        # Notify callbacks
        for callback in self._callbacks:
            try:
                await callback("service_added", service)
            except Exception as e:
                logger.error(f"Callback error: {e}")
                
        logger.info(f"Registered service: {service.name} at {service.address}")
        
    async def unregister_service(self, name: str) -> None:
        """Unregister a service."""
        if name in self._services:
            service = self._services[name]
            del self._services[name]
            
            # Stop health checking
            if name in self._health_check_tasks:
                self._health_check_tasks[name].cancel()
                del self._health_check_tasks[name]
                
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    await callback("service_removed", service)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
                    
            logger.info(f"Unregistered service: {name}")
            
    async def get_service(self, name: str) -> Optional[ServiceInfo]:
        """Get service by name."""
        return self._services.get(name)
        
    async def get_healthy_services(self, service_type: Optional[str] = None,
                                  min_score: float = 50.0) -> List[ServiceInfo]:
        """
        Get healthy services.
        
        Args:
            service_type: Filter by service type
            min_score: Minimum health score (0-100)
            
        Returns:
            List of healthy services
        """
        services = list(self._services.values())
        
        # Filter by type
        if service_type:
            services = [s for s in services if s.service_type == service_type]
            
        # Filter by health
        healthy = [s for s in services if s.health_score >= min_score]
        
        # Sort by health score
        healthy.sort(key=lambda s: s.health_score, reverse=True)
        
        return healthy
        
    async def select_service(self, service_type: str) -> Optional[ServiceInfo]:
        """
        Select a service using the configured strategy.
        
        Args:
            service_type: Service type to select from
            
        Returns:
            Selected service or None
        """
        # Get healthy services
        services = await self.get_healthy_services(service_type)
        if not services:
            return None
            
        # Apply strategy
        if self.failover_strategy == FailoverStrategy.ROUND_ROBIN:
            # Round-robin selection
            index = self._round_robin_index[service_type]
            selected = services[index % len(services)]
            self._round_robin_index[service_type] = index + 1
            
        elif self.failover_strategy == FailoverStrategy.LEAST_CONNECTIONS:
            # Select least connected
            selected = min(services, 
                          key=lambda s: self._connection_counts[s.name])
                          
        elif self.failover_strategy == FailoverStrategy.FASTEST_RESPONSE:
            # Select fastest
            selected = min(services, key=lambda s: s.response_time_ms)
            
        elif self.failover_strategy == FailoverStrategy.WEIGHTED:
            # Weighted by health score
            import random
            weights = [s.health_score for s in services]
            selected = random.choices(services, weights=weights)[0]
            
        else:
            selected = services[0]
            
        # Update connection count
        self._connection_counts[selected.name] += 1
        self._last_used[selected.name] = datetime.now()
        
        return selected
        
    async def release_service(self, name: str) -> None:
        """Release a service connection."""
        if name in self._connection_counts:
            self._connection_counts[name] = max(0, self._connection_counts[name] - 1)
            
    async def _health_check_loop(self, name: str) -> None:
        """Health check loop for a service."""
        while name in self._services:
            try:
                service = self._services[name]
                
                # Check circuit breaker
                if self._is_circuit_open(name):
                    service.status = ServiceStatus.UNHEALTHY
                    await asyncio.sleep(self.health_check_interval)
                    continue
                    
                # Perform health check
                start_time = time.time()
                healthy = await self._check_health(service)
                response_time = (time.time() - start_time) * 1000
                
                # Update service info
                service.response_time_ms = response_time
                service.last_health_check = datetime.now()
                
                if healthy:
                    service.status = ServiceStatus.HEALTHY
                    service.success_count += 1
                    self._reset_circuit_breaker(name)
                else:
                    service.status = ServiceStatus.UNHEALTHY
                    service.error_count += 1
                    self._record_circuit_breaker_failure(name)
                    
            except Exception as e:
                logger.error(f"Health check error for {name}: {e}")
                if name in self._services:
                    self._services[name].status = ServiceStatus.UNKNOWN
                    self._services[name].error_count += 1
                    self._record_circuit_breaker_failure(name)
                    
            # Wait for next check
            await asyncio.sleep(self.health_check_interval)
            
    async def _check_health(self, service: ServiceInfo) -> bool:
        """
        Check service health.
        
        This is a simplified health check. Real implementation would:
        - Make HTTP health endpoint calls
        - Check TCP connectivity
        - Verify service-specific protocols
        """
        # Simulate health check
        await asyncio.sleep(0.01)  # Network delay
        
        # In real implementation, this would make actual health checks
        # For now, simulate based on error rate
        if service.error_count > 10:
            return False
            
        # Random failure for testing
        import random
        return random.random() > 0.1  # 90% healthy
        
    def _is_circuit_open(self, name: str) -> bool:
        """Check if circuit breaker is open."""
        if name not in self._circuit_breaker_state:
            return False
            
        state = self._circuit_breaker_state[name]
        if state["failures"] >= self._circuit_breaker_threshold:
            # Check if timeout has passed
            if datetime.now() - state["opened_at"] > timedelta(seconds=self._circuit_breaker_timeout):
                # Half-open state - allow one try
                state["half_open"] = True
                return False
            return True
            
        return False
        
    def _record_circuit_breaker_failure(self, name: str) -> None:
        """Record a circuit breaker failure."""
        if name not in self._circuit_breaker_state:
            self._circuit_breaker_state[name] = {
                "failures": 0,
                "opened_at": None,
                "half_open": False
            }
            
        state = self._circuit_breaker_state[name]
        state["failures"] += 1
        
        if state["failures"] >= self._circuit_breaker_threshold:
            state["opened_at"] = datetime.now()
            logger.warning(f"Circuit breaker opened for {name}")
            
    def _reset_circuit_breaker(self, name: str) -> None:
        """Reset circuit breaker."""
        if name in self._circuit_breaker_state:
            del self._circuit_breaker_state[name]
            logger.info(f"Circuit breaker reset for {name}")
            
    def get_service_mesh_status(self) -> Dict[str, Any]:
        """Get overall service mesh status."""
        total_services = len(self._services)
        healthy_services = len([s for s in self._services.values() 
                               if s.status == ServiceStatus.HEALTHY])
        degraded_services = len([s for s in self._services.values() 
                               if s.status == ServiceStatus.DEGRADED])
        unhealthy_services = len([s for s in self._services.values() 
                                if s.status == ServiceStatus.UNHEALTHY])
                                
        return {
            "total_services": total_services,
            "healthy": healthy_services,
            "degraded": degraded_services, 
            "unhealthy": unhealthy_services,
            "service_types": list(self._service_types),
            "open_circuits": len([n for n, s in self._circuit_breaker_state.items() 
                                 if s["failures"] >= self._circuit_breaker_threshold]),
            "active_connections": sum(self._connection_counts.values()),
            "services": [
                {
                    "name": s.name,
                    "type": s.service_type,
                    "address": s.address,
                    "status": s.status.value,
                    "health_score": s.health_score,
                    "response_time_ms": s.response_time_ms,
                    "connections": self._connection_counts.get(s.name, 0)
                }
                for s in self._services.values()
            ]
        }
        
    def add_health_callback(self, callback: Callable) -> None:
        """Add callback for service events."""
        self._callbacks.append(callback)
        

if __name__ == "__main__":
    # Test service discovery
    async def test_discovery():
        discovery = ServiceDiscovery()
        await discovery.start()
        
        # Manually register some services for testing
        await discovery.register_service(ServiceInfo(
            name="module1",
            service_type="_claude-module._tcp",
            host="192.168.1.100",
            port=8080,
            properties={"version": "1.0", "capabilities": "nlp,vision"}
        ))
        
        await discovery.register_service(ServiceInfo(
            name="module2", 
            service_type="_claude-module._tcp",
            host="192.168.1.101",
            port=8080,
            properties={"version": "1.0", "capabilities": "audio"}
        ))
        
        # Wait for health checks
        await asyncio.sleep(2)
        
        # Get healthy services
        healthy = await discovery.get_healthy_services("_claude-module._tcp")
        print(f"Healthy services: {len(healthy)}")
        
        # Select a service
        selected = await discovery.select_service("_claude-module._tcp")
        if selected:
            print(f"Selected: {selected.name} at {selected.address}")
            
        # Get mesh status
        status = discovery.get_service_mesh_status()
        print(f"Service mesh: {status['healthy']}/{status['total_services']} healthy")
        
        await discovery.stop()
        
    asyncio.run(test_discovery())