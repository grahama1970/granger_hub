# Communication Status

Check the status of module communication system.

## Usage

```bash
claude-comm status [--module <name>] [--sessions] [--metrics]
```

## Arguments

- `--module`: Check specific module status
- `--sessions`: Show active sessions
- `--metrics`: Show communication metrics

## Examples

```bash
# Overall status
/communicate-status

# Module-specific status
/communicate-status --module sparta

# Show active sessions
/communicate-status --sessions

# Show metrics
/communicate-status --metrics
```

## Status Information

- Active modules
- Message queue status
- Failed deliveries
- Average response times
- Schema validation errors

---
*Claude Module Communicator*
