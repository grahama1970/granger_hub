# Execute Module Pipeline

Execute a predefined pipeline of module operations.

## Usage

```bash
claude-comm pipeline <config_file> [--validate-only] [--async]
```

## Arguments

- `config_file`: Pipeline configuration JSON file
- `--validate-only`: Only validate, don't execute
- `--async`: Run pipeline asynchronously

## Examples

```bash
# Execute pipeline
/communicate-pipeline extraction_pipeline.json

# Validate pipeline
/communicate-pipeline processing_pipeline.json --validate-only

# Async execution
/communicate-pipeline full_pipeline.json --async
```

## Pipeline Configuration

```json
{
  "name": "extraction_to_training",
  "steps": [
    {
      "module": "marker",
      "action": "extract",
      "input": {"file": "document.pdf"}
    },
    {
      "module": "sparta",
      "action": "process",
      "input": "$previous.output"
    },
    {
      "module": "arangodb",
      "action": "store",
      "input": "$previous.output"
    }
  ]
}
```

---
*Granger Hub*
