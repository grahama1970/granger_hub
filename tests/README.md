# Test Suite Documentation

This directory contains all tests for the Claude Module Communicator project. The test structure mirrors the source code structure for easy navigation and maintenance.

## 📁 Test Organization

The test directory structure exactly mirrors `src/` for consistency:

```
tests/
├── claude_coms/
│   ├── cli/                    # CLI command tests
│   ├── core/
│   │   ├── conversation/       # Conversation system tests
│   │   ├── llm/               # LLM integration tests
│   │   ├── modules/           # Module system tests
│   │   └── storage/           # Storage backend tests
│   ├── forecast/              # Forecasting module tests
│   ├── mcp/                   # MCP server tests
│   ├── rl/                    # Reinforcement learning tests
│   └── test_integration.py    # Integration tests
├── fixtures/                  # Test data and fixtures
│   └── forecast/             # Real-world forecast data
└── conftest.py               # Pytest configuration
```

## 🚀 Running Tests

### Run All Tests
```bash
# From project root
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/claude_coms/core/ -v

# Integration tests
pytest tests/claude_coms/test_integration.py -v

# Conversation system tests
pytest tests/claude_coms/core/conversation/ -v

# Forecasting tests
pytest tests/claude_coms/forecast/ -v

# MCP server tests
pytest tests/claude_coms/mcp/ -v
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

## 🔄 Continuous Integration

Tests are automatically run on:
- Every push to main branch
- Every pull request
- Can be manually triggered

Ensure all tests pass locally before pushing!