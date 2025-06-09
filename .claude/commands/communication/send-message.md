# Send Message Between Modules

Route a message from one module to another.

## Usage

```bash
claude-comm send <source> <target> <message> [--type <message_type>]
```

## Arguments

- `source`: Source module name
- `target`: Target module name
- `message`: Message content (JSON or string)
- `--type`: Message type (request, response, data)

## Examples

```bash
# Send simple message
/communicate-send marker sparta "extraction complete"

# Send data message
/communicate-send sparta arangodb '{"records": 100, "status": "ready"}' --type data

# Send request
/communicate-send llm_proxy unsloth '{"action": "prepare_dataset"}' --type request
```

## Message Routing

The communicator will:
1. Validate source and target modules exist
2. Check schema compatibility
3. Route the message
4. Track delivery status

---
*Granger Hub*
