# Register Module

Register a new module with the Granger Hub.

## Usage

```bash
claude-comm register <module_name> <capabilities_json> [--schema <schema_file>]
```

## Arguments

- `module_name`: Unique module identifier
- `capabilities_json`: JSON array of module capabilities
- `--schema`: Path to schema definition file

## Examples

```bash
# Register a module
/communicate-register marker '["pdf_extraction", "text_extraction"]'

# Register with schema
/communicate-register sparta '["data_ingestion", "processing"]' --schema sparta_schema.json
```

## Schema Format

```json
{
  "input": {
    "type": "object",
    "properties": {
      "data": {"type": "array"}
    }
  },
  "output": {
    "type": "object",
    "properties": {
      "processed": {"type": "array"}
    }
  }
}
```

---
*Granger Hub*
