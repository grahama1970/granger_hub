# LLM Integration Guide for Granger Hub

This guide explains how to integrate claude_max_proxy and LLM capabilities into your Granger Hub modules.

## Overview

The LLM integration provides:
- Natural language processing capabilities for modules
- Intelligent analysis and pattern recognition
- Predictive behavior modeling
- Natural language query interfaces
- Automated insights and recommendations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Granger Hub                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │   Module A   │    │   Module B   │    │   Module C   │   │
│  │ (LLM-enabled)│    │ (Standard)   │    │ (LLM-enabled)│   │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘   │
│         │                   │                   │           │
│         └───────────────────┴───────────────────┘           │
│                             │                               │
│                    ┌────────┴────────┐                      │
│                    │ LLM Integration │                      │
│                    │     Layer       │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│                    ┌────────┴────────┐                      │
│                    │ claude_max_proxy│                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Installation

```bash
# Install claude_max_proxy (assuming it's available)
pip install claude_max_proxy

# Install optional dependencies
pip install pydantic python-dotenv
```

### 2. Configuration

Create a `llm_config.json` file:

```json
{
  "providers": {
    "anthropic": {
      "api_key": "your-anthropic-api-key",
      "default_model": "claude-3-haiku-20240307"
    }
  },
  "default_provider": "anthropic",
  "default_model": "claude-3-haiku-20240307",
  "module_configs": {
    "YourModule": {
      "enabled": true,
      "preferred_model": "claude-3-sonnet-20240229",
      "temperature": 0.5
    }
  }
}
```

Or use environment variables:
```bash
export ANTHROPIC_API_KEY="your-key"
export LLM_DEFAULT_MODEL="claude-3-haiku-20240307"
export LLM_TEMPERATURE="0.7"
```

### 3. Basic Usage

#### Creating an LLM-Enabled Module

```python
from claude_coms import BaseModule, ModuleRegistry
from claude_coms.llm_integration import LLMCapableMixin, LLMConfig
from claude_coms.llm_config import get_llm_config

class MyIntelligentModule(LLMCapableMixin, BaseModule):
    def __init__(self, registry: ModuleRegistry):
        # Get module-specific LLM config
        llm_config = get_llm_config("MyIntelligentModule")
        
        super().__init__(
            name="MyIntelligentModule",
            system_prompt="You are an intelligent module with LLM capabilities.",
            capabilities=["analysis", "natural_language"],
            registry=registry,
            llm_config=llm_config
        )
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Use LLM for analysis
        analysis = await self.llm_analyze(data, "pattern_detection")
        
        # Process a custom prompt
        response = await self.llm_process(
            "Explain this data in simple terms",
            context={"data": data}
        )
        
        # Get recommendations
        recommendations = await self.llm_recommend(
            context={"analysis": analysis},
            constraints={"max_items": 5}
        )
        
        return {
            "analysis": analysis,
            "explanation": response.content,
            "recommendations": recommendations
        }
```

## Advanced Features

### 1. Natural Language Queries

The enhanced ArangoDB expert module supports natural language queries:

```python
expert = ArangoExpertLLMModule(registry)

result = await expert.process({
    "action": "natural_query",
    "parameters": {
        "query": "Which modules are the most critical for system communication?"
    }
})
```

### 2. Pattern Explanation

Get intelligent explanations of discovered patterns:

```python
result = await expert.process({
    "action": "explain_pattern",
    "parameters": {
        "pattern": "hub_spoke",
        "min_connections": 5
    }
})
```

### 3. Behavior Prediction

Predict future system behavior:

```python
result = await expert.process({
    "action": "predict_behavior",
    "parameters": {
        "timeframe": "next_6_hours",
        "modules": ["data_producer", "processor"]
    }
})
```

### 4. Graph Optimization

Get AI-powered optimization suggestions:

```python
result = await expert.process({
    "action": "optimize_graph",
    "parameters": {
        "goal": "reliability",
        "constraints": {
            "max_connections_per_module": 10,
            "preserve_existing": True
        }
    }
})
```

## Integration Patterns

### 1. Mixin Pattern (Recommended)

Use `LLMCapableMixin` to add LLM capabilities to any module:

```python
class YourModule(LLMCapableMixin, BaseModule):
    # Your module implementation
```

### 2. Direct Integration

For more control, use `LLMIntegration` directly:

```python
from claude_coms.llm_integration import LLMIntegration, LLMRequest

class YourModule(BaseModule):
    def __init__(self, registry):
        super().__init__(...)
        self.llm = LLMIntegration(config)
    
    async def process(self, data):
        await self.llm.initialize()
        
        request = LLMRequest(
            prompt="Your prompt",
            model=LLMModel.CLAUDE_3_SONNET,
            temperature=0.5
        )
        
        response = await self.llm.process(request)
```

### 3. Configuration Management

Use the configuration manager for centralized setup:

```python
from claude_coms.llm_config import init_llm_config, get_llm_config

# Initialize global config
init_llm_config("path/to/llm_config.json")

# Get module-specific config
config = get_llm_config("YourModule")
```

## Best Practices

### 1. Model Selection

- **Claude 3 Haiku**: Fast, cost-effective for simple tasks
- **Claude 3 Sonnet**: Balanced performance for analysis
- **Claude 3 Opus**: Most capable for complex reasoning

### 2. Temperature Settings

- `0.0 - 0.3`: Deterministic, factual responses (analysis, queries)
- `0.4 - 0.7`: Balanced creativity and accuracy (general use)
- `0.8 - 1.0`: Creative, varied responses (brainstorming)

### 3. Token Management

```python
# Set appropriate token limits
config = LLMConfig(
    max_tokens=4096,  # Default
    # Adjust based on use case:
    # - Analysis: 2048-4096
    # - Summaries: 1024-2048
    # - Complex reasoning: 4096-8192
)
```

### 4. Error Handling

```python
response = await self.llm_process(prompt)

if response.success:
    # Process response
    content = response.content
else:
    # Handle error
    logger.error(f"LLM error: {response.error}")
    # Fallback logic
```

### 5. Caching and Performance

```python
# Enable caching in config
{
    "enable_caching": true,
    "cache_ttl_seconds": 3600
}

# Or implement custom caching
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_analysis(data_hash):
    return await self.llm_analyze(data, "pattern_detection")
```

## Example Use Cases

### 1. Intelligent Data Processing

```python
class DataProcessor(LLMCapableMixin, BaseModule):
    async def process(self, data):
        # Understand natural language instructions
        if data.get("instruction"):
            understanding = await self.llm_process(
                f"How should I process this data: {data['instruction']}"
            )
        
        # Perform intelligent analysis
        insights = await self.llm_analyze(
            data["values"],
            "pattern_detection"
        )
        
        return {"processed": data, "insights": insights}
```

### 2. Natural Language Interface

```python
class NLInterface(LLMCapableMixin, BaseModule):
    async def process(self, data):
        user_query = data["query"]
        
        # Understand intent
        intent = await self.llm_process(
            f"What is the user asking for: {user_query}",
            temperature=0.3
        )
        
        # Route to appropriate module
        target_module = self._determine_target(intent.content)
        result = await self.send_to(target_module, "process", data)
        
        # Explain results
        explanation = await self.llm_process(
            f"Explain these results to a user: {result}"
        )
        
        return {"explanation": explanation.content}
```

### 3. Anomaly Detection and Explanation

```python
class AnomalyDetector(LLMCapableMixin, BaseModule):
    async def process(self, data):
        # Detect anomalies
        anomalies = self._detect_anomalies(data)
        
        if anomalies:
            # Get LLM explanation
            explanation = await self.llm_analyze(
                {
                    "data": data,
                    "anomalies": anomalies
                },
                "anomaly_explanation"
            )
            
            # Generate recommendations
            recommendations = await self.llm_recommend(
                context={"anomalies": anomalies},
                constraints={"urgency": "high"}
            )
        
        return {
            "anomalies": anomalies,
            "explanation": explanation,
            "recommendations": recommendations
        }
```

## Monitoring and Debugging

### 1. Usage Statistics

```python
# Get module LLM stats
stats = module.llm.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Total tokens: {stats['total_tokens']}")
print(f"Average duration: {stats['avg_duration_ms']}ms")
print(f"Success rate: {stats['success_rate']*100}%")
```

### 2. Request History

```python
# Get recent requests
history = module.llm.get_request_history(limit=10)
for response in history:
    print(f"Model: {response.model}")
    print(f"Tokens: {response.tokens_used}")
    print(f"Duration: {response.duration_ms}ms")
```

### 3. Debugging

Enable request logging in configuration:

```json
{
    "log_requests": true,
    "log_level": "DEBUG"
}
```

## Security Considerations

1. **API Key Management**
   - Never commit API keys to version control
   - Use environment variables or secure key management
   - Rotate keys regularly

2. **Input Validation**
   - Sanitize user inputs before sending to LLM
   - Implement rate limiting
   - Monitor for prompt injection attempts

3. **Output Filtering**
   - Validate LLM responses before using in critical operations
   - Implement content filtering if needed
   - Log suspicious responses

## Troubleshooting

### Common Issues

1. **"claude_max_proxy not available"**
   - Ensure claude_max_proxy is installed
   - Check Python path and imports

2. **"API key not found"**
   - Set ANTHROPIC_API_KEY environment variable
   - Check llm_config.json file
   - Verify key format and validity

3. **"Request timeout"**
   - Increase timeout in configuration
   - Check network connectivity
   - Consider using a faster model

4. **"Token limit exceeded"**
   - Reduce max_tokens in configuration
   - Chunk large inputs
   - Use summarization for long texts

## Next Steps

1. Review the [example implementation](../../examples/llm_integration_example.py)
2. Create your own LLM-enhanced modules
3. Experiment with different models and settings
4. Monitor usage and optimize for your use case

For more information, see the claude_max_proxy documentation and the Anthropic API reference.