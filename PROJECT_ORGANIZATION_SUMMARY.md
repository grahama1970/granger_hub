# Project Organization Summary

## Cleanup Completed ✅

### 1. **Root Directory Cleanup**
- ✅ Moved all test JSON files to `archive/test_results/`
- ✅ Moved all test Python files to `archive/`
- ✅ Moved scenario documentation to `archive/scenario_docs/`
- ✅ Moved Gemini-related docs to `archive/gemini_docs/`
- ✅ Moved status reports to `archive/status_reports/`
- ✅ Moved shell scripts to `scripts/` directory

### 2. **Test Directory Organization**
- ✅ Removed obsolete `test_basic.py` that referenced old package structure
- ✅ Created placeholder test files for TODO components (LLM, Storage, MCP, RL)
- ✅ Updated `tests/README.md` with comprehensive testing guide
- ✅ Maintained test directory structure that mirrors `src/` exactly

### 3. **Documentation**
- ✅ Created `repos/README.md` to document external repositories
- ✅ Updated test README with clear instructions for running tests
- ✅ Added honeypot test documentation

## Current Project Structure

```
claude-module-communicator/
├── src/                    # Source code (hub-spoke architecture)
│   └── claude_coms/       # Main package
│       ├── cli/           # CLI commands
│       ├── core/          # Core functionality
│       │   ├── adapters/  # Protocol adapters (hub components)
│       │   ├── conversation/
│       │   ├── llm/
│       │   ├── modules/
│       │   └── storage/
│       ├── forecast/      # Forecasting module
│       ├── mcp/          # MCP server
│       └── rl/           # Reinforcement learning
├── tests/                 # Test suite (mirrors src/)
│   ├── adapters/         # Adapter tests
│   ├── claude_coms/      # Package tests
│   └── fixtures/         # Test data
├── docs/                  # Documentation
├── examples/              # Example scripts
├── scripts/              # Utility scripts
├── scenarios/            # Test scenarios
├── reports/              # Test reports
├── archive/              # Archived files
│   ├── test_results/     # Old test JSONs
│   ├── scenario_docs/    # Scenario documentation
│   ├── gemini_docs/      # Gemini-related docs
│   └── status_reports/   # Project status files
├── repos/                # External repositories (413MB)
└── logs/                 # Log files

Key files:
- pyproject.toml          # Project configuration
- README.md              # Project documentation
- CLAUDE.md              # Coding standards
```

## Test Organization

### Active Tests
- `tests/adapters/` - Protocol adapter tests ✅
- `tests/claude_coms/cli/` - CLI tests ✅
- `tests/claude_coms/core/conversation/` - Conversation tests ✅
- `tests/claude_coms/core/modules/` - Module tests ✅
- `tests/claude_coms/forecast/` - Forecast tests ✅

### TODO Tests (placeholders created)
- `tests/claude_coms/core/llm/` - LLM integration tests
- `tests/claude_coms/core/storage/` - Storage backend tests
- `tests/claude_coms/mcp/` - MCP server tests
- `tests/claude_coms/rl/` - Reinforcement learning tests

## Running Tests

```bash
# Quick test before push
cd /home/graham/workspace/experiments/claude-module-communicator
source .venv/bin/activate
pytest tests/ -v --tb=short

# All tests should pass except honeypot tests
```

## Recommendations

1. **External Repos**: Consider removing `repos/` directory (413MB) or moving to separate research repo
2. **Empty Test Dirs**: Implement tests for LLM, Storage, MCP, and RL components
3. **Archive**: Periodically review and clean `archive/` directory
4. **Logs**: Set up log rotation for `logs/` directory

## Hub-Spoke Architecture

The project follows a hub-spoke architecture where:
- **Hub**: `src/claude_coms/core/adapters/` - Routes messages between services
- **Spokes**: External services (Marker, mcp-screenshot, forecast, etc.)
- **No business logic in hub**: All domain logic in external services