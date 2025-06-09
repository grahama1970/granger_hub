"""
Pipeline Data Isolation Implementation
Ensures data separation between pipeline instances.
"""

import threading
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class PipelineInstance:
    """Isolated pipeline instance with its own data context."""
    id: str
    created_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def get_data(self, key: str) -> Optional[Any]:
        """Thread-safe data retrieval."""
        with self._lock:
            return self.data.get(key)
    
    def set_data(self, key: str, value: Any):
        """Thread-safe data storage."""
        with self._lock:
            self.data[key] = value
            
    def clear(self):
        """Clear all instance data."""
        with self._lock:
            self.data.clear()


class PipelineIsolationManager:
    """Manages isolated pipeline instances."""
    
    def __init__(self):
        self.instances: Dict[str, PipelineInstance] = {}
        self._global_lock = threading.Lock()
        
    def create_instance(self) -> str:
        """Create a new isolated pipeline instance."""
        instance_id = str(uuid.uuid4())
        with self._global_lock:
            self.instances[instance_id] = PipelineInstance(
                id=instance_id,
                created_at=datetime.now()
            )
        return instance_id
    
    def get_instance(self, instance_id: str) -> Optional[PipelineInstance]:
        """Get a specific pipeline instance."""
        with self._global_lock:
            return self.instances.get(instance_id)
    
    def verify_isolation(self, instance_id1: str, instance_id2: str) -> bool:
        """Verify data isolation between two instances."""
        inst1 = self.get_instance(instance_id1)
        inst2 = self.get_instance(instance_id2)
        
        if not inst1 or not inst2:
            return False
            
        # Test isolation by setting data in one instance
        test_key = "isolation_test"
        test_value = f"data_from_{instance_id1}"
        
        inst1.set_data(test_key, test_value)
        
        # Verify other instance doesn't have this data
        return inst2.get_data(test_key) is None
    
    def cleanup_instance(self, instance_id: str):
        """Clean up a pipeline instance."""
        with self._global_lock:
            if instance_id in self.instances:
                self.instances[instance_id].clear()
                del self.instances[instance_id]

# Global manager instance
_isolation_manager = PipelineIsolationManager()

def get_isolation_manager() -> PipelineIsolationManager:
    """Get the global isolation manager."""
    return _isolation_manager
