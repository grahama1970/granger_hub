# List Registered Modules

List all modules registered with the Module Communicator.

## Usage

```bash
claude-comm list-modules [--status] [--capabilities]
```

## Arguments

- `--status`: Show module connection status
- `--capabilities`: Show module capabilities

## Examples

```bash
# List all modules
/communicate-list-modules

# List with status
/communicate-list-modules --status

# List with capabilities
/communicate-list-modules --capabilities
```

## Output

Shows registered modules with their:
- Name and version
- Registration time
- Capabilities
- Connection status
- Input/Output schemas

---
*Claude Module Communicator*
