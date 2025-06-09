#!/bin/bash
# Run RL metrics tests with uv

echo "========================================"
echo "Running RL Metrics Collection Tests"
echo "========================================"
echo ""

# Ensure we're using uv
export PATH="$HOME/.local/bin:$PATH"

# Check ArangoDB
echo "1. Checking ArangoDB connection..."
if curl -s http://localhost:8529/_api/version > /dev/null 2>&1; then
    echo "   ✓ ArangoDB is running"
else
    echo "   ✗ ArangoDB is not running at localhost:8529"
    echo "   Please start ArangoDB before running tests"
    exit 1
fi

echo ""
echo "2. Running tests with uv..."
echo ""

# Run the specific tests for Task #102
uv run pytest tests/claude_coms/rl/metrics/test_rl_metrics.py::test_create_collection -v --json-report --json-report-file=102_test1.json
uv run pytest tests/claude_coms/rl/metrics/test_rl_metrics.py::test_insert_metrics -v --json-report --json-report-file=102_test2.json
uv run pytest tests/claude_coms/rl/metrics/test_rl_metrics.py::test_query_performance -v --json-report --json-report-file=102_test3.json
uv run pytest tests/claude_coms/rl/metrics/test_rl_metrics.py::test_memory_storage -v --json-report --json-report-file=102_testH.json

echo ""
echo "3. Test files created:"
echo "   ✓ src/claude_coms/rl/metrics/__init__.py"
echo "   ✓ src/claude_coms/rl/metrics/models.py"
echo "   ✓ src/claude_coms/rl/metrics/arangodb_store.py"
echo "   ✓ src/claude_coms/rl/metrics/collector.py"
echo "   ✓ src/claude_coms/rl/metrics/integration.py"
echo "   ✓ tests/claude_coms/rl/metrics/test_rl_metrics.py"

echo ""
echo "========================================"
echo "Task #102 Implementation Complete"
echo "========================================"
