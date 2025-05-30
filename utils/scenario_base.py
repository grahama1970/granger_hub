"""
Base class for scenarios
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import json

@dataclass
class Message:
    """Represents a message between modules"""
    from_module: str
    to_module: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class ScenarioBase(ABC):
    """Base class for all scenarios"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.results = {}
    
    @abstractmethod
    def setup_modules(self) -> Dict[str, Dict[str, Any]]:
        """Define the modules required for this scenario"""
        pass
    
    @abstractmethod
    def create_workflow(self) -> List[Message]:
        """Create the message workflow for this scenario"""
        pass
    
    @abstractmethod
    def process_results(self, results: List[Dict[str, Any]]) -> None:
        """Process the results from the workflow"""
        pass
    
    def run(self) -> Dict[str, Any]:
        """Run the scenario (simulated)"""
        print(f"Running scenario: {self.name}")
        
        # Setup modules
        modules = self.setup_modules()
        print(f"Modules configured: {list(modules.keys())}")
        
        # Create workflow
        workflow = self.create_workflow()
        print(f"Workflow created with {len(workflow)} steps")
        
        # Simulate execution
        simulated_results = []
        for msg in workflow:
            print(f"  {msg.from_module} → {msg.to_module}")
            simulated_results.append({
                "from": msg.from_module,
                "to": msg.to_module,
                "content": {"status": "simulated", **msg.content}
            })
        
        # Process results
        self.process_results(simulated_results)
        
        return {
            "scenario": self.name,
            "success": True,
            "results": self.results
        }
    
    def to_json(self) -> str:
        """Convert scenario to JSON representation"""
        return json.dumps({
            "name": self.name,
            "description": self.description,
            "modules": self.setup_modules(),
            "workflow": [
                {
                    "from": msg.from_module,
                    "to": msg.to_module,
                    "content": msg.content,
                    "metadata": msg.metadata
                }
                for msg in self.create_workflow()
            ]
        }, indent=2)
