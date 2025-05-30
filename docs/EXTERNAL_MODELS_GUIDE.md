# External Models Integration Guide

## Overview
The Claude Module Communicator now has seamless integration with external LLMs through the `claude_max_proxy` project, enabling Claude instances to:
- Communicate with other Claude instances
- Query Gemini, GPT-4, and other models
- Compare responses from multiple models
- Route queries intelligently to the best model

## Setup

### 1. Installation
The `claude_max_proxy` dependency is already included in `pyproject.toml`:
```toml
dependencies = [
    # ... other deps
    "claude_max_proxy @ file:///home/graham/workspace/experiments/claude_max_proxy",
]
```

### 2. API Keys
Set environment variables for the models you want to use:
```bash
export ANTHROPIC_API_KEY="your-claude-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
export OPENAI_API_KEY="your-openai-api-key"
```

Or use a `.env` file:
```env
ANTHROPIC_API_KEY=your-claude-api-key
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
```

## Usage

### 1. ExternalLLMModule
The `ExternalLLMModule` provides easy access to all external models:

```python
from claude_coms import ModuleRegistry
from claude_coms.external_llm_module import ExternalLLMModule

# Create and start the module
registry = ModuleRegistry()
external_llm = ExternalLLMModule(registry)
await external_llm.start()
```

### 2. Available Actions

#### Direct Model Query
```python
result = await external_llm.process({
    "action": "ask_model",
    "model": "gemini/gemini-2.0-flash-exp",
    "prompt": "Explain quantum computing"
})
```

#### Claude-to-Claude Communication
```python
result = await external_llm.process({
    "action": "claude_dialogue",
    "model": "claude-3-opus-20240229",
    "prompt": "Let's collaborate on solving this problem..."
})
```

#### Multi-Model Comparison
```python
result = await external_llm.process({
    "action": "compare_models",
    "models": ["gemini/gemini-pro", "claude-3-opus-20240229", "gpt-4"],
    "prompt": "What's the best approach to distributed systems?"
})
```

#### Intelligent Routing
```python
result = await external_llm.process({
    "action": "route_to_best",
    "prompt": "Write a Python web scraper"  # Will route to Claude (good at code)
})
```

### 3. Available Models

#### Claude Models
- `claude-3-opus-20240229` - Most capable
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-haiku-20240307` - Fast and efficient

#### Gemini Models  
- `gemini/gemini-2.0-flash-exp` - Latest, very fast
- `gemini/gemini-pro` - Standard Gemini
- `gemini/gemini-pro-vision` - Multimodal

#### OpenAI Models
- `gpt-4-turbo-preview` - Latest GPT-4
- `gpt-4` - Standard GPT-4
- `gpt-3.5-turbo` - Fast and cheap

#### Perplexity (Online Search)
- `perplexity/sonar-medium-online` - For current information

## Integration with Modules

### Adding LLM Capabilities to Any Module
Use the `LLMCapableMixin`:

```python
from claude_coms.base_module import BaseModule
from claude_coms.llm_integration import LLMCapableMixin, LLMConfig

class MySmartModule(LLMCapableMixin, BaseModule):
    def __init__(self, registry):
        llm_config = LLMConfig(
            default_model="gemini/gemini-2.0-flash-exp",
            fallback_models=["claude-3-haiku-20240307"]
        )
        super().__init__(
            name="MySmartModule",
            system_prompt="...",
            capabilities=["..."],
            registry=registry,
            llm_config=llm_config
        )
    
    async def process(self, data):
        # Use LLM for processing
        result = await self.llm_process(
            "Analyze this data and suggest improvements",
            context=data
        )
        return {"analysis": result.content}
```

### Module-to-Module LLM Queries
Modules can ask the ExternalLLM module for help:

```python
# From within any module
response = await self.send_to(
    "ExternalLLM",
    "process",
    {
        "action": "ask_model",
        "model": "gemini/gemini-2.0-flash-exp", 
        "prompt": "Help me analyze this pattern"
    }
)
```

## Examples

### Running the Demo
```bash
cd examples
python claude_external_models_demo.py
```

### Quick Test
```python
# Test if LLM integration is working
from llm_call import ask

response = await ask(
    "What is 2+2?",
    model="gemini/gemini-2.0-flash-exp"
)
print(response)
```

## Best Practices

1. **Model Selection**
   - Use Claude for: Code, creative writing, complex reasoning
   - Use Gemini for: Fast responses, data analysis, general queries
   - Use GPT-4 for: Broad knowledge, instruction following
   - Use Perplexity for: Current events, fact-checking

2. **Error Handling**
   - Always check `result["success"]`
   - Configure fallback models
   - Handle rate limits gracefully

3. **Cost Optimization**
   - Use faster/cheaper models when appropriate
   - Cache responses when possible
   - Batch similar queries

4. **Claude-to-Claude Communication**
   - Use the `claude_dialogue` action for Claude instances
   - Provide context about the collaborative nature
   - Each Claude can have different specializations

## Troubleshooting

### LLM Not Available Error
```python
if not LLM_AVAILABLE:
    print("Install claude_max_proxy: pip install claude_max_proxy")
```

### API Key Issues
```python
import os
if not os.getenv("GEMINI_API_KEY"):
    print("Set GEMINI_API_KEY environment variable")
```

### Model Not Found
Check available models:
```python
print(external_llm.available_models)
```

## Advanced Features

### Custom Model Routing
Override `_select_best_model()` in ExternalLLMModule:
```python
def _select_best_model(self, prompt: str, context: Dict[str, Any]) -> str:
    # Your custom logic
    if "urgent" in prompt.lower():
        return "gemini/gemini-2.0-flash-exp"  # Fastest
    # ... more rules
```

### Session Management
Maintain conversations across multiple interactions:
```python
# Start a chat session
result1 = await external_llm.process({
    "action": "chat_with_model",
    "model": "claude-3-opus-20240229",
    "prompt": "Let's discuss module architecture",
    "session_id": "architecture_discussion"
})

# Continue the same conversation
result2 = await external_llm.process({
    "action": "chat_with_model",
    "model": "claude-3-opus-20240229",
    "prompt": "What about scalability concerns?",
    "session_id": "architecture_discussion"
})
```

This integration makes it trivial for any Claude instance in the module system to leverage the capabilities of other AI models, enabling true multi-model collaboration!