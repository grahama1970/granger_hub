# Test Suite Documentation

This directory contains all tests for the Claude Module Communicator project. The test structure mirrors the source code structure for easy navigation and maintenance.

## 📁 Test Organization

The test directory structure exactly mirrors `src/` for consistency:

```
tests/
├── adapters/                  # Protocol adapter tests (hub-spoke architecture)
│   ├── test_cli_adapter.py    # CLI command execution tests
│   ├── test_rest_adapter.py   # REST API communication tests
│   ├── test_mcp_adapter.py    # MCP protocol tests
│   ├── test_marker_adapter.py # PDF processing tests
│   └── test_adapter_honeypot.py # Testing integrity verification
├── claude_coms/
│   ├── cli/                   # CLI command tests
│   ├── core/
│   │   ├── conversation/      # Conversation system tests
│   │   ├── llm/              # LLM integration tests (TODO)
│   │   ├── modules/          # Module system tests
│   │   └── storage/          # Storage backend tests (TODO)
│   ├── forecast/             # Forecasting module tests
│   ├── mcp/                  # MCP server tests (TODO)
│   ├── rl/                   # Reinforcement learning tests (TODO)
│   └── test_integration.py   # Integration tests
├── fixtures/                 # Test data and fixtures
│   └── forecast/            # Real-world forecast data
└── conftest.py              # Pytest configuration
```

## ⚠️ Test Status

| Component | Directory | Status | Notes |
|-----------|-----------|--------|-------|
| Adapters | `tests/adapters/` | ✅ Complete | All protocol adapters tested |
| CLI | `tests/claude_coms/cli/` | ✅ Complete | Command interface tested |
| Conversation | `tests/claude_coms/core/conversation/` | ✅ Complete | Full conversation flow |
| Modules | `tests/claude_coms/core/modules/` | ✅ Complete | Core module functionality |
| Forecast | `tests/claude_coms/forecast/` | ✅ Complete | Real data fixtures |
| LLM | `tests/claude_coms/core/llm/` | ❌ TODO | Needs implementation |
| Storage | `tests/claude_coms/core/storage/` | ❌ TODO | Needs implementation |
| MCP | `tests/claude_coms/mcp/` | ❌ TODO | Needs implementation |
| RL | `tests/claude_coms/rl/` | ❌ TODO | Needs implementation |

## 🚀 Running Tests

### Quick Start - Run All Tests
```bash
# From project root
cd /home/graham/workspace/experiments/granger_hub
source .venv/bin/activate
pytest tests/ -v
```

### Run With Coverage
```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term

# View coverage in browser
xdg-open htmlcov/index.html  # Linux
open htmlcov/index.html       # macOS
```

### Run Specific Test Categories

```bash
# Protocol adapter tests (hub-spoke architecture)
pytest tests/adapters/ -v

# Module system tests
pytest tests/claude_coms/core/modules/ -v

# Conversation system tests
pytest tests/claude_coms/core/conversation/ -v

# CLI command tests
pytest tests/claude_coms/cli/ -v

# Forecasting tests with real data
pytest tests/claude_coms/forecast/ -v
```

### Run Individual Test Files
```bash
# Test module system
pytest tests/claude_coms/core/modules/test_modules.py -v

# Test conversation manager
pytest tests/claude_coms/core/conversation/test_conversation_manager.py -v
```

## 🧪 Test Categories

### Unit Tests
- **Location**: Individual module directories
- **Purpose**: Test individual components in isolation
- **Naming**: `test_<module_name>.py`

### Integration Tests
- **Location**: `claude_coms/test_integration.py`
- **Purpose**: Test interactions between multiple components
- **Coverage**: End-to-end workflows

### Fixture Tests
- **Location**: `fixtures/`
- **Purpose**: Real-world data for testing
- **Note**: NO mocking - all tests use real data

## ✅ Pre-Push Checklist

Before pushing changes, ensure:

1. **All tests pass**:
   ```bash
   pytest tests/ -v
   ```

2. **Coverage is maintained** (aim for >80%):
   ```bash
   pytest tests/ --cov=src --cov-report=term
   ```

3. **No test files in src/**:
   ```bash
   find src/ -name "*test*.py" -o -name "*_test.py" | grep -v __pycache__
   # Should return nothing
   ```

4. **Tests mirror src structure**:
   ```bash
   # Check that test directories match src directories
   diff <(find src/claude_coms -type d | sed 's/src/tests/' | sort) \
        <(find tests/claude_coms -type d | sort)
   ```

## 📋 Test Guidelines

Following `CLAUDE.md` standards:

1. **NO Mocking**: Use real data and real implementations
2. **Real Validation**: Test with actual expected outputs
3. **Type Hints**: All test functions should have type annotations
4. **Clear Names**: Test names should describe what they test
5. **Fixtures**: Use `fixtures/` for test data, not inline fake data

## 🔧 Adding New Tests

When adding new functionality:

1. Create test file in the mirrored location
2. Use real data from fixtures or generate real test cases
3. Test both success and failure cases
4. Update this README if adding new test categories

## 🐛 Debugging Failed Tests

```bash
# Run with verbose output
pytest tests/path/to/test.py -vv

# Run with print statements visible
pytest tests/path/to/test.py -s

# Run specific test function
pytest tests/path/to/test.py::TestClass::test_function -v

# Run with debugger
pytest tests/path/to/test.py --pdb
```

## 📊 Coverage Reports

Generate and view coverage reports:

```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Open coverage report (macOS)
open htmlcov/index.html

# Open coverage report (Linux)
xdg-open htmlcov/index.html
```

## 🍯 Honeypot Tests

The `tests/adapters/test_adapter_honeypot.py` file contains special tests that are **DESIGNED TO FAIL**. These tests verify that our testing framework is actually running real tests and not faking results.

```bash
# Run honeypot tests (SHOULD FAIL)
pytest tests/adapters/test_adapter_honeypot.py -v

# Expected: Tests should fail with "HONEYPOT DETECTED" messages
# If these tests pass, there's a problem with the testing framework!
```

## 🔄 Continuous Integration

Tests are automatically run on:
- Every push to main branch
- Every pull request
- Can be manually triggered

Ensure all tests pass locally before pushing!

## 🚨 Pre-Push Command

**Run this single command before every push to ensure nothing is broken:**

```bash
pytest tests/ -v --tb=short
```

All tests should pass (except honeypot tests which should fail).