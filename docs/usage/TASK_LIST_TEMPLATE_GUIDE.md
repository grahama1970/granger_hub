# Task List Template Guide v3 - Dynamic Module Communication

This guide extends v2 with requirements for dynamic inter-module communication using Claude instances.

## New Requirements: Module Communication

### 1. Schema Negotiation in Tasks

Every task that involves data transfer between modules MUST include schema negotiation:

```markdown
# Task [NUMBER]: [Description]

## Pre-Task Module Communication

### Schema Negotiation
```bash
# Negotiate schema between modules
/negotiate-schema --from SPARTA --to Marker --sample sample_data.json

# Verify compatibility
/verify-compatibility --from SPARTA --to Marker --format negotiated_format.json
```

### Expected Negotiation Output
```json
{
  "schema_version": "1.0",
  "required_fields": ["file_id", "local_path", "file_type"],
  "optional_fields": ["enrichments", "metadata"],
  "negotiated": true
}
```

## Task Implementation
[Rest of task content...]
```

### 2. Slash Commands for Module Communication

Available slash commands that MUST be used in task lists:

#### `/negotiate-schema`
Negotiate data schema between two modules.
```bash
/negotiate-schema --from MODULE1 --to MODULE2 --sample sample.json [--requirements REQ1 REQ2]
```

#### `/verify-compatibility`
Verify if a data format is compatible with target module.
```bash
/verify-compatibility --from MODULE1 --to MODULE2 --format format.json
```

#### `/ask-module`
Ask a module a specific question.
```bash
/ask-module --from MODULE1 --to MODULE2 --question "Your question" [--context context.json]
```

#### `/check-pipeline`
Verify entire pipeline compatibility.
```bash
/check-pipeline --modules SPARTA Marker ArangoDB Unsloth
```

#### `/module-handshake`
Perform bidirectional introduction between modules.
```bash
/module-handshake --module1 SPARTA --module2 Marker
```

### 3. Task Template with Module Communication

```markdown
# Task [NUMBER]: [Task Title]

**Modules Involved**: [List modules]
**Data Flow**: MODULE1 → MODULE2 → MODULE3
**Communication Required**: YES

## 1. Pre-Task Validation

### Module Handshake
```bash
/module-handshake --module1 [SOURCE] --module2 [TARGET]
```

### Schema Negotiation
```bash
# Create sample data file
cat > sample_data.json << EOF
{
  "your": "sample",
  "data": "here"
}
EOF

# Negotiate schema
/negotiate-schema --from [SOURCE] --to [TARGET] --sample sample_data.json
```

### Compatibility Check
```bash
/verify-compatibility --from [SOURCE] --to [TARGET] --format negotiated_schema.json
```

## 2. Task Implementation

[Your existing task content...]

## 3. Post-Task Validation

### Verify Output Schema
```bash
# Ensure output matches negotiated schema
/ask-module --from [TARGET] --to [SOURCE] --question "Did you receive all required fields?"
```

### Pipeline Health Check
```bash
/check-pipeline --modules [ALL_MODULES_IN_PIPELINE]
```
```

### 4. Example: Complete Task with Communication

```markdown
# Task 15: Implement SPARTA to Marker Data Transfer

**Modules Involved**: SPARTA, Marker
**Data Flow**: SPARTA → Marker
**Communication Required**: YES

## 1. Pre-Task Validation

### Module Handshake
```bash
/module-handshake --module1 SPARTA --module2 Marker
```
**Expected**: Both modules acknowledge each other

### Schema Negotiation
```bash
# Create sample SPARTA output
cat > sparta_sample.json << EOF
{
  "file_id": "aerospace_123",
  "local_path": "/data/resources/aerospace_123.pdf",
  "file_type": "pdf",
  "source_stix": {
    "id": "attack-pattern--123",
    "name": "Gather Spacecraft Design Information",
    "type": "attack-pattern"
  },
  "enrichments": {
    "nist_controls": ["AC-2", "SC-7"],
    "mitre_techniques": ["T1591", "T1592"],
    "confidence_score": 0.85
  }
}
EOF

# Negotiate schema
/negotiate-schema --from SPARTA --to Marker --sample sparta_sample.json
```

### Compatibility Check
```bash
/verify-compatibility --from SPARTA --to Marker --format sparta_sample.json
```

## 2. Task Implementation

### Update SPARTA Manifest Generator
```python
# In manifest_generator.py, use negotiated schema
negotiator = DynamicSchemaNegotiator("SPARTA")
schema = await negotiator.negotiate_schema("Marker", sample_file_entry)

# Generate manifest according to negotiated schema
manifest_entry = self._conform_to_schema(file_entry, schema)
```

### Update Marker Ingestion
```python
# In marker ingestion, validate against negotiated schema
negotiator = DynamicSchemaNegotiator("Marker")
cached_schema = negotiator.get_cached_schema("SPARTA", "Marker")

# Validate incoming data
if not self._validate_against_schema(data, cached_schema):
    raise SchemaValidationError("Data doesn't match negotiated schema")
```

## 3. Post-Task Validation

### Verify Data Transfer
```bash
# Ask Marker if it received the data correctly
/ask-module --from SPARTA --to Marker \
  --question "Did you successfully receive and process the manifest?"
```

### Pipeline Check
```bash
/check-pipeline --modules SPARTA Marker ArangoDB
```

## Success Criteria
- [ ] Module handshake successful
- [ ] Schema negotiated without errors
- [ ] Compatibility verified
- [ ] Data transfer matches negotiated schema
- [ ] Pipeline health check passes
```

### 5. Key Principles

1. **No Hardcoded Schemas**: Every data exchange must use dynamically negotiated schemas
2. **Verify Before Transfer**: Always check compatibility before implementation
3. **Claude as Mediator**: Use Claude instances for all inter-module communication
4. **Document Negotiations**: Save negotiated schemas for reference
5. **Pipeline Integrity**: Regular pipeline health checks

### 6. Common Patterns

#### Pattern: Multi-Module Pipeline Setup
```bash
# Check entire pipeline before starting work
/check-pipeline --modules SPARTA Marker ArangoDB Unsloth

# If issues found, negotiate pair by pair
/negotiate-schema --from SPARTA --to Marker --sample sparta_out.json
/negotiate-schema --from Marker --to ArangoDB --sample marker_out.json
/negotiate-schema --from ArangoDB --to Unsloth --sample arango_out.json
```

#### Pattern: Schema Evolution
```bash
# When adding new fields
/ask-module --from SPARTA --to Marker \
  --question "Can you handle a new field 'extraction_timestamp'?"

# Re-negotiate if needed
/negotiate-schema --from SPARTA --to Marker \
  --sample updated_sample.json \
  --requirements "must handle extraction_timestamp"
```

#### Pattern: Debugging Communication Issues
```bash
# Get detailed capabilities
/ask-module --from SPARTA --to Marker \
  --question "What are your current data processing capabilities?"

# Check specific field handling
/ask-module --from SPARTA --to Marker \
  --question "How do you handle the 'enrichments' field?"
```

### 7. Anti-Patterns to Avoid

❌ Implementing data transfer without schema negotiation
❌ Hardcoding expected data formats
❌ Skipping compatibility checks
❌ Ignoring negotiation failures
❌ Manual schema definitions

### 8. Good Patterns to Follow

✅ Always negotiate before implementing
✅ Cache negotiated schemas for reuse
✅ Verify compatibility at each step
✅ Use Claude instances for all communication
✅ Document negotiation results in tasks

## Integration with CI/CD

For automated validation:

```yaml
# .github/workflows/module_communication.yml
name: Module Communication Tests

on: [push, pull_request]

jobs:
  schema-negotiation:
    runs-on: ubuntu-latest
    steps:
      - name: Check Module Communication
        run: |
          # Test schema negotiation
          python -m sparta.communication.slash_commands \
            /check-pipeline --modules SPARTA Marker ArangoDB Unsloth
          
      - name: Verify Schemas
        run: |
          # Ensure all connections have negotiated schemas
          python scripts/verify_all_schemas.py
```

## Summary

Every task involving data transfer between modules MUST:
1. Start with module handshake
2. Negotiate schemas dynamically
3. Verify compatibility
4. Implement according to negotiated schema
5. Validate successful transfer
6. Check pipeline health

This ensures robust, self-documenting, and adaptive module integration.