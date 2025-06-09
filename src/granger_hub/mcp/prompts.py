"""
Prompt infrastructure for Granger Hub.
Module: prompts.py

This module provides a flexible prompt management system that allows
for dynamic prompt registration, categorization, and rendering.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from pathlib import Path
import json
import yaml
from datetime import datetime
import re
from jinja2 import Template, Environment, FileSystemLoader


@dataclass
class Prompt:
    """Represents a single prompt with metadata and template."""
    
    name: str
    description: str
    template: str
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def render(self, **kwargs) -> str:
        """Render the prompt template with provided parameters."""
        # Validate required parameters
        missing = set(self.required_params) - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")
        
        # Use Jinja2 for template rendering
        template = Template(self.template)
        return template.render(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "template": self.template,
            "category": self.category,
            "tags": self.tags,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "examples": self.examples,
            "version": self.version,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prompt':
        """Create prompt from dictionary representation."""
        # Handle datetime conversion
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class PromptRegistry:
    """Central registry for managing prompts."""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize the prompt registry.
        
        Args:
            prompts_dir: Optional directory to load prompts from
        """
        self._prompts: Dict[str, Prompt] = {}
        self._categories: Dict[str, Set[str]] = {}
        self._tags: Dict[str, Set[str]] = {}
        
        # Setup Jinja2 environment if prompts_dir provided
        if prompts_dir and prompts_dir.exists():
            self.env = Environment(loader=FileSystemLoader(str(prompts_dir)))
            self._load_prompts_from_dir(prompts_dir)
        else:
            self.env = Environment()
    
    def register(self, prompt: Prompt) -> None:
        """Register a new prompt.
        
        Args:
            prompt: The prompt to register
        """
        self._prompts[prompt.name] = prompt
        
        # Update category index
        if prompt.category:
            if prompt.category not in self._categories:
                self._categories[prompt.category] = set()
            self._categories[prompt.category].add(prompt.name)
        
        # Update tag index
        for tag in prompt.tags:
            if tag not in self._tags:
                self._tags[tag] = set()
            self._tags[tag].add(prompt.name)
    
    def get_prompt(self, name: str) -> Optional[Prompt]:
        """Get a prompt by name.
        
        Args:
            name: The prompt name
            
        Returns:
            The prompt if found, None otherwise
        """
        return self._prompts.get(name)
    
    def list_prompts(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Prompt]:
        """List prompts with optional filtering.
        
        Args:
            category: Filter by category
            tags: Filter by tags (prompts must have all specified tags)
            
        Returns:
            List of matching prompts
        """
        prompts = set(self._prompts.keys())
        
        # Filter by category
        if category:
            prompts &= self._categories.get(category, set())
        
        # Filter by tags
        if tags:
            for tag in tags:
                prompts &= self._tags.get(tag, set())
        
        return [self._prompts[name] for name in sorted(prompts)]
    
    def list_categories(self) -> List[str]:
        """List all available categories."""
        return sorted(self._categories.keys())
    
    def list_tags(self) -> List[str]:
        """List all available tags."""
        return sorted(self._tags.keys())
    
    def remove(self, name: str) -> bool:
        """Remove a prompt from the registry.
        
        Args:
            name: The prompt name to remove
            
        Returns:
            True if removed, False if not found
        """
        if name not in self._prompts:
            return False
        
        prompt = self._prompts[name]
        
        # Remove from category index
        if prompt.category and prompt.category in self._categories:
            self._categories[prompt.category].discard(name)
            if not self._categories[prompt.category]:
                del self._categories[prompt.category]
        
        # Remove from tag index
        for tag in prompt.tags:
            if tag in self._tags:
                self._tags[tag].discard(name)
                if not self._tags[tag]:
                    del self._tags[tag]
        
        # Remove prompt
        del self._prompts[name]
        return True
    
    def save_to_file(self, path: Path, format: str = "json") -> None:
        """Save all prompts to a file.
        
        Args:
            path: The file path to save to
            format: Output format ('json' or 'yaml')
        """
        data = {
            "version": "1.0.0",
            "prompts": [prompt.to_dict() for prompt in self._prompts.values()]
        }
        
        if format == "json":
            path.write_text(json.dumps(data, indent=2, default=str))
        elif format == "yaml":
            import yaml
            path.write_text(yaml.dump(data, default_flow_style=False))
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def load_from_file(self, path: Path) -> None:
        """Load prompts from a file.
        
        Args:
            path: The file path to load from
        """
        if path.suffix == ".json":
            data = json.loads(path.read_text())
        elif path.suffix in [".yaml", ".yml"]:
            import yaml
            data = yaml.safe_load(path.read_text())
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        # Load prompts
        for prompt_data in data.get("prompts", []):
            prompt = Prompt.from_dict(prompt_data)
            self.register(prompt)
    
    def _load_prompts_from_dir(self, prompts_dir: Path) -> None:
        """Load prompts from a directory.
        
        Args:
            prompts_dir: Directory containing prompt files
        """
        # Load JSON/YAML prompt files
        for path in prompts_dir.glob("*.json"):
            self.load_from_file(path)
        
        for path in prompts_dir.glob("*.yaml"):
            self.load_from_file(path)
        
        for path in prompts_dir.glob("*.yml"):
            self.load_from_file(path)
        
        # Load template files
        for path in prompts_dir.glob("*.j2"):
            self._load_template_prompt(path)
    
    def _load_template_prompt(self, path: Path) -> None:
        """Load a prompt from a Jinja2 template file.
        
        Args:
            path: Path to the template file
        """
        # Extract metadata from template front matter
        content = path.read_text()
        
        # Look for YAML front matter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                metadata = yaml.safe_load(parts[1])
                template = parts[2].strip()
            else:
                metadata = {}
                template = content
        else:
            metadata = {}
            template = content
        
        # Create prompt from metadata and template
        name = metadata.get("name", path.stem)
        prompt = Prompt(
            name=name,
            description=metadata.get("description", f"Prompt from {path.name}"),
            template=template,
            category=metadata.get("category"),
            tags=metadata.get("tags", []),
            parameters=metadata.get("parameters", {}),
            required_params=metadata.get("required_params", []),
            examples=metadata.get("examples", []),
            version=metadata.get("version", "1.0.0")
        )
        
        self.register(prompt)
    
    def create_prompt_from_function(self, func, category: Optional[str] = None) -> Prompt:
        """Create a prompt from a function's docstring and signature.'
        
        Args:
            func: The function to create a prompt from
            category: Optional category for the prompt
            
        Returns:
            The created prompt
        """
        import inspect
        
        # Extract function metadata
        name = func.__name__
        docstring = inspect.getdoc(func) or "No description available"
        
        # Parse docstring for description
        lines = docstring.split('\n')
        description = lines[0] if lines else "No description"
        
        # Extract parameters from signature
        sig = inspect.signature(func)
        parameters = {}
        required_params = []
        
        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'cls']:
                continue
            
            param_info = {
                "type": "string",
                "description": f"Parameter {param_name}"
            }
            
            # Infer type from annotation
            if param.annotation != param.empty:
                if param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation == float:
                    param_info["type"] = "number"
            
            parameters[param_name] = param_info
            
            if param.default == param.empty:
                required_params.append(param_name)
        
        # Create template from docstring
        template = f"""Task: {description}

Parameters:
{{% for param, info in parameters.items() %}}
- {{{{ param }}}}: {{{{ info.description }}}} ({{{{ info.type }}}})
{{% endfor %}}

Instructions:
{docstring}
"""
        
        return Prompt(
            name=name,
            description=description,
            template=template,
            category=category,
            parameters=parameters,
            required_params=required_params
        )


# Global registry instance
_global_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """Get the global prompt registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = PromptRegistry()
    return _global_registry


def set_prompt_registry(registry: PromptRegistry) -> None:
    """Set the global prompt registry instance."""
    global _global_registry
    _global_registry = registry


if __name__ == "__main__":
    # Validation with real data
    print(f"Validating {__file__}...")
    
    # Create test registry
    registry = PromptRegistry()
    
    # Create test prompt
    test_prompt = Prompt(
        name="test_prompt",
        description="A test prompt for validation",
        template="Hello {{ name }}! Your task is: {{ task }}",
        category="testing",
        tags=["test", "validation"],
        parameters={
            "name": {"type": "string", "description": "User name"},
            "task": {"type": "string", "description": "Task description"}
        },
        required_params=["name", "task"]
    )
    
    # Register prompt
    registry.register(test_prompt)
    
    # Test retrieval
    retrieved = registry.get_prompt("test_prompt")
    assert retrieved is not None, "Failed to retrieve prompt"
    assert retrieved.name == "test_prompt", "Prompt name mismatch"
    
    # Test rendering
    rendered = retrieved.render(name="Claude", task="validate the system")
    expected = "Hello Claude! Your task is: validate the system"
    assert rendered == expected, f"Expected '{expected}', got '{rendered}'"
    
    # Test filtering
    by_category = registry.list_prompts(category="testing")
    assert len(by_category) == 1, "Category filtering failed"
    
    by_tags = registry.list_prompts(tags=["test"])
    assert len(by_tags) == 1, "Tag filtering failed"
    
    print(" Validation passed")