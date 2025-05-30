# Negotiate Schema

Negotiate compatible schema between two modules.

## Usage

```bash
claude-comm negotiate-schema <source> <target> [--sample-data <file>]
```

## Arguments

- `source`: Source module name
- `target`: Target module name
- `--sample-data`: Sample data for schema inference

## Examples

```bash
# Basic negotiation
/communicate-negotiate-schema marker sparta

# With sample data
/communicate-negotiate-schema sparta arangodb --sample-data sample.json
```

## Negotiation Process

1. Retrieve source output schema
2. Retrieve target input schema
3. Find compatible subset
4. Propose transformations if needed
5. Return negotiated schema

---
*Claude Module Communicator*
