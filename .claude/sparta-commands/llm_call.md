# LLM Call Slash Commands

Universal LLM interface with smart routing, validation, and Claude Max proxy support.

## Quick Start

/llm-ask "[question]" [model]
Description: Ask a single question to any LLM
Arguments:
  - question: Your question or prompt
  - model: (optional) Model to use (default: claude-3-5-sonnet-20241022)
```bash
llm-cli ask "[question]"
# With specific model
llm-cli ask "[question]" --model gpt-4
# With Claude Max model
llm-cli ask "[question]" --model max/claude-3-5-sonnet-20241022
```

/llm-chat [model]
Description: Start interactive chat session
Arguments:
  - model: (optional) Model to use
```bash
llm-cli chat
# With specific model
llm-cli chat --model gpt-4
# With system prompt
llm-cli chat --system "You are a helpful coding assistant" --model max/claude-3-opus
```

/llm-models
Description: List all available models
Arguments: None
```bash
llm-cli models
# Show grouped by provider
llm-cli models --group-by-provider
```

## Validation Commands

/llm-validate-json "[prompt]"
Description: Generate and validate JSON output
Arguments:
  - prompt: Prompt that should produce JSON
```bash
llm-cli ask "[prompt]" --validate json
# With specific schema
llm-cli ask "[prompt]" --validate json --schema schema.json
```

/llm-validate-code "[prompt]" [language]
Description: Generate and validate code
Arguments:
  - prompt: Prompt for code generation
  - language: (optional) Programming language (python, javascript, sql)
```bash
llm-cli ask "[prompt]" --validate code
# With specific language
llm-cli ask "Write a Python function to sort a list" --validate python
# With retry on validation failure
llm-cli ask "[prompt]" --validate python --max-retries 3
```

/llm-validate-yaml "[prompt]"
Description: Generate and validate YAML output
Arguments:
  - prompt: Prompt that should produce YAML
```bash
llm-cli ask "[prompt]" --validate yaml
# With schema validation
llm-cli ask "[prompt]" --validate yaml --schema config-schema.yaml
```

/llm-validators
Description: Show all available validation strategies
Arguments: None
```bash
llm-cli validators
# With examples
llm-cli validators --show-examples
```

## Code Analysis Commands

/llm-analyze-code [file] [analysis_type]
Description: Analyze code with LLM
Arguments:
  - file: Path to code file
  - analysis_type: review, optimize, refactor, security, bugs
```bash
# Code review
llm-cli ask "Review this code: $(cat [file])" --model gpt-4

# Optimization suggestions
llm-cli ask "Optimize this code for performance: $(cat [file])" --model max/claude-3-opus

# Security analysis
llm-cli ask "Find security vulnerabilities in: $(cat [file])" --validate json
```

/llm-explain-code [file]
Description: Get detailed explanation of code
Arguments:
  - file: Path to code file
```bash
llm-cli ask "Explain this code in detail: $(cat [file])" --model claude-3-5-sonnet-20241022
# With specific focus
llm-cli ask "Explain the algorithm in this code: $(cat [file])"
```

/llm-generate-tests [file]
Description: Generate unit tests for code
Arguments:
  - file: Path to code file
```bash
llm-cli ask "Generate comprehensive unit tests for: $(cat [file])" --validate python
# With specific framework
llm-cli ask "Generate pytest tests for: $(cat [file])" --validate python
```

## Multi-Model Commands

/llm-compare "[prompt]" [models]
Description: Compare responses from multiple models
Arguments:
  - prompt: Question to ask all models
  - models: Comma-separated list of models
```bash
# Compare across providers
python -c "
import asyncio
from llm_call.core.llm_manager import LLMManager

async def compare():
    manager = LLMManager()
    models = ['gpt-4', 'claude-3-5-sonnet-20241022', 'gemini-pro']
    prompt = '[prompt]'
    
    for model in models:
        print(f'\n=== {model} ===')
        response = await manager.call_llm(prompt, model=model)
        print(response['content'])

asyncio.run(compare())
"
```

/llm-race "[prompt]"
Description: Race multiple models and return fastest response
Arguments:
  - prompt: Question to ask
```bash
# Race default models
llm-cli ask "[prompt]" --race

# Race specific models
llm-cli ask "[prompt]" --race --models gpt-4,claude-3-5-sonnet-20241022,gemini-pro
```

## Configuration Management

/llm-config-example [output_file]
Description: Generate example configuration file
Arguments:
  - output_file: (optional) Output filename
```bash
llm-cli config-example
# Save to file
llm-cli config-example --output my-config.json
# With comments
llm-cli config-example --with-comments
```

/llm-call [config_file]
Description: Execute LLM call with config file
Arguments:
  - config_file: Path to JSON/YAML config
```bash
llm-cli call config.json
# Override prompt
llm-cli call config.json --prompt "Override prompt"
# Override model
llm-cli call config.json --model gpt-4
```

/llm-env-check
Description: Check environment variables and API keys
Arguments: None
```bash
python -c "
import os
keys = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GROQ_API_KEY', 
        'LITELLM_VERTEX_PROJECT', 'LLM_DEFAULT_MODEL']
for key in keys:
    value = os.getenv(key, 'Not set')
    masked = value[:4] + '***' if value != 'Not set' and 'KEY' in key else value
    print(f'{key}: {masked}')
"
```

## Claude Max Proxy Commands

/llm-max "[prompt]"
Description: Use Claude Max models via CLI proxy
Arguments:
  - prompt: Your prompt
```bash
llm-cli ask "[prompt]" --model max/claude-3-5-sonnet-20241022
# With opus model
llm-cli ask "[prompt]" --model max/claude-3-opus-20240229
# Interactive chat
llm-cli chat --model max/claude-3-5-sonnet-20241022
```

/llm-max-models
Description: List available Claude Max models
Arguments: None
```bash
llm-cli models | grep "max/"
# Or specific check
echo "Available Claude Max models:
- max/claude-3-5-sonnet-20241022
- max/claude-3-opus-20240229
- max/claude-3-sonnet-20240229
- max/claude-3-haiku-20240307"
```

## Local Model Commands

/llm-local "[prompt]" [model]
Description: Use local Ollama models
Arguments:
  - prompt: Your prompt
  - model: (optional) Ollama model name
```bash
llm-cli ask "[prompt]" --model ollama/llama2
# List local models
ollama list
# Use specific local model
llm-cli ask "[prompt]" --model ollama/codellama
```

/llm-local-chat [model]
Description: Chat with local Ollama model
Arguments:
  - model: (optional) Ollama model name
```bash
llm-cli chat --model ollama/llama2
# With custom parameters
llm-cli chat --model ollama/llama2 --temperature 0.7
```

## POC Testing Commands

/llm-poc-test [pattern]
Description: Run proof-of-concept validation tests
Arguments:
  - pattern: (optional) File pattern to match POC tests
```bash
llm-cli test
# Run specific POC tests
llm-cli test "poc_*.py"
# Run in parallel
llm-cli test --parallel
# With specific model
llm-cli test --model gpt-4
```

/llm-poc-run [poc_file]
Description: Run a specific POC test
Arguments:
  - poc_file: Path to POC test file
```bash
llm-cli test-poc [poc_file]
# With verbose output
llm-cli test-poc [poc_file] --verbose
```

## MCP Server Commands

/llm-mcp-config
Description: Generate MCP configuration for Claude Desktop
Arguments: None
```bash
llm-cli generate-mcp-config
# Save to Claude config location
llm-cli generate-mcp-config > ~/.config/Claude/claude_desktop_config.json
```

/llm-mcp-serve
Description: Start LLM Call as MCP server
Arguments: None
```bash
llm-cli serve-mcp
# With custom port
llm-cli serve-mcp --port 3010
# With debug logging
llm-cli serve-mcp --debug
```

## Utility Commands

/llm-stream "[prompt]" [model]
Description: Stream response from LLM
Arguments:
  - prompt: Your prompt
  - model: (optional) Model to use
```bash
llm-cli ask "[prompt]" --stream
# With specific model
llm-cli ask "[prompt]" --model gpt-4 --stream
```

/llm-token-count "[text]"
Description: Count tokens in text
Arguments:
  - text: Text to count tokens for
```bash
python -c "
import tiktoken
enc = tiktoken.encoding_for_model('gpt-4')
text = '[text]'
tokens = len(enc.encode(text))
print(f'Token count: {tokens}')
"
```

/llm-cost-estimate "[prompt]" [model]
Description: Estimate cost for prompt
Arguments:
  - prompt: Your prompt
  - model: Model to estimate for
```bash
# Rough estimation based on token count
python -c "
import tiktoken

prompt = '[prompt]'
model = '[model]'

# Rough cost estimates per 1M tokens
costs = {
    'gpt-4': {'input': 30, 'output': 60},
    'gpt-3.5-turbo': {'input': 0.5, 'output': 1.5},
    'claude-3-5-sonnet-20241022': {'input': 3, 'output': 15}
}

enc = tiktoken.encoding_for_model('gpt-4')
tokens = len(enc.encode(prompt))
cost = costs.get(model, costs['gpt-4'])
estimate = (tokens / 1_000_000) * cost['input']
print(f'Estimated cost for {tokens} tokens: ${estimate:.4f}')
"
```

## Docker Commands

/llm-docker-build
Description: Build LLM Call Docker image
Arguments: None
```bash
cd /home/graham/workspace/experiments/claude_max_proxy
docker build -t llm-call .
```

/llm-docker-run
Description: Run LLM Call in Docker
Arguments: None
```bash
docker run -d \
  -p 3010:3010 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  --name llm-call \
  llm-call
```

/llm-docker-compose
Description: Run with Docker Compose (includes Redis)
Arguments: None
```bash
cd /home/graham/workspace/experiments/claude_max_proxy
docker-compose up -d
```

## Integration Examples

### SPARTA Integration
```bash
# Process SPARTA results with LLM
llm-cli ask "Analyze these cybersecurity resources: $(cat sparta_results.json)" \
  --model max/claude-3-opus \
  --validate json
```

### ArangoDB Integration
```bash
# Generate graph queries
llm-cli ask "Generate AQL query to find all entities related to 'malware': $(cat schema.json)" \
  --model gpt-4 \
  --validate code
```

### Report Generation
```bash
# Generate analysis report
llm-cli ask "Create a comprehensive analysis report from: $(cat data.json)" \
  --model claude-3-5-sonnet-20241022 \
  --validate markdown \
  > analysis_report.md
```

---

## Common Workflows

### 1. Code Development Workflow
```bash
# Generate code
/llm-ask "Write a Python function to process CSV files" --validate python

# Review code
/llm-analyze-code my_function.py review

# Generate tests
/llm-generate-tests my_function.py

# Optimize
/llm-analyze-code my_function.py optimize
```

### 2. Multi-Model Analysis
```bash
# Compare model responses
/llm-compare "Explain quantum computing" gpt-4,claude-3-5-sonnet,gemini-pro

# Use best model for task
/llm-max "Complex reasoning task requiring deep analysis"
```

### 3. Validation Pipeline
```bash
# Generate validated JSON
/llm-validate-json "Create a config file for a web server"

# Validate and retry
/llm-validate-code "Write a sorting algorithm" python --max-retries 3
```