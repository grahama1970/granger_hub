# Task 001: Test Granger Hub Components

**Project**: granger_hub
**Goal**: Create comprehensive tests for all project components with real data validation

## Task Breakdown

### SubTask 1: Test CLI Communication Commands

**Module**: `src/cli/communication_commands.py`
**Test File**: `tests/cli/test_communication_commands.py`

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
import asyncio
import tempfile
from pathlib import Path
from typer import Typer
from typer.testing import CliRunner
from claude_coms.cli.communication_commands import app

runner = CliRunner()

def test_negotiate_schema_command():
    """Test schema negotiation between modules with real data."""
    # Real module configuration
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('''{
            "source_module": "stix_processor",
            "target_module": "ml_analyzer",
            "schema": {
                "input": {"type": "object", "properties": {"data": {"type": "array"}}},
                "output": {"type": "object", "properties": {"result": {"type": "string"}}}
            }
        }''')
        config_path = f.name
    
    result = runner.invoke(app, ["negotiate-schema", config_path])
    assert result.exit_code == 0
    assert "Schema negotiation successful" in result.stdout
    Path(config_path).unlink()

def test_verify_compatibility_command():
    """Test module compatibility verification with real schemas."""
    # Create real pipeline configuration
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('''{
            "modules": [
                {
                    "name": "stix_processor",
                    "version": "1.0.0",
                    "input_schema": null,
                    "output_schema": {"type": "object", "properties": {"stix_data": {"type": "array"}}}
                },
                {
                    "name": "ml_analyzer",
                    "version": "1.0.0",
                    "input_schema": {"type": "object", "properties": {"stix_data": {"type": "array"}}},
                    "output_schema": {"type": "object", "properties": {"predictions": {"type": "array"}}}
                }
            ]
        }''')
        pipeline_path = f.name
    
    result = runner.invoke(app, ["verify-compatibility", pipeline_path])
    assert result.exit_code == 0
    assert "Pipeline compatibility: PASS" in result.stdout
    Path(pipeline_path).unlink()

# Run tests
if __name__ == "__main__":
    test_negotiate_schema_command()
    test_verify_compatibility_command()
    print("✅ All CLI communication tests passed!")
```

## Test Details

**Expected Command**:
```bash
cd /home/graham/workspace/experiments/granger_hub
source .venv/bin/activate
pytest tests/cli/test_communication_commands.py -v
```

**Expected Output Structure**:
```
tests/cli/test_communication_commands.py::test_negotiate_schema_command PASSED
tests/cli/test_communication_commands.py::test_verify_compatibility_command PASSED
```

## Common Issues & Solutions

### Issue 1: Import Error - Module not found
```python
# Solution: Add project root to PYTHONPATH
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

### Issue 2: Async function testing
```python
# Solution: Use pytest-asyncio
import pytest
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

## Validation Requirements

```python
# Each test must:
assert result.exit_code == 0, "Command executed successfully"
assert expected_output in result.stdout, "Expected output present"
assert Path(output_file).exists(), "Output file created"
# Verify with real data - no mocks allowed
```

---

### SubTask 2: Test Core Progress Tracking

**Module**: `src/core/progress_utils.py`
**Test File**: `tests/core/test_progress_utils.py`

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
import aiosqlite
from claude_coms.core.progress_utils import (
    init_database, update_session_stats, get_session_statistics,
    log_file_operation, get_recent_file_operations
)

async def test_progress_tracking_with_real_db():
    """Test progress tracking with real SQLite database."""
    # Create real temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Initialize database
    await init_database(db_path)
    
    # Test session statistics
    session_id = "test_session_001"
    await update_session_stats(
        db_path=db_path,
        session_id=session_id,
        files_processed=10,
        errors_encountered=1,
        start_time=datetime.now().isoformat()
    )
    
    # Verify statistics
    stats = await get_session_statistics(db_path, session_id)
    assert stats["files_processed"] == 10
    assert stats["errors_encountered"] == 1
    assert stats["session_id"] == session_id
    
    # Test file operations logging
    await log_file_operation(
        db_path=db_path,
        session_id=session_id,
        operation_type="READ",
        file_path="/test/file.json",
        status="SUCCESS",
        details={"size": 1024, "duration": 0.5}
    )
    
    # Verify file operations
    operations = await get_recent_file_operations(db_path, session_id, limit=10)
    assert len(operations) == 1
    assert operations[0]["operation_type"] == "READ"
    assert operations[0]["status"] == "SUCCESS"
    
    # Cleanup
    Path(db_path).unlink()
    return True

# Run test
if __name__ == "__main__":
    result = asyncio.run(test_progress_tracking_with_real_db())
    if result:
        print("✅ Progress tracking test passed!")
```

## Test Details

**Expected Command**:
```bash
cd /home/graham/workspace/experiments/granger_hub
source .venv/bin/activate
pytest tests/core/test_progress_utils.py -v
```

**Expected Output**:
```
tests/core/test_progress_utils.py::test_progress_tracking_with_real_db PASSED
```

## Common Issues & Solutions

### Issue 1: Database lock errors
```python
# Solution: Use proper async context managers
async with aiosqlite.connect(db_path) as db:
    async with db.execute(query) as cursor:
        result = await cursor.fetchall()
```

### Issue 2: File cleanup in tests
```python
# Solution: Use try/finally or pytest fixtures
@pytest.fixture
async def temp_db():
    db_path = tempfile.mktemp(suffix='.db')
    yield db_path
    if Path(db_path).exists():
        Path(db_path).unlink()
```

---

### SubTask 3: Test Empty Module Directories

**Modules**: `src/claude_coms/`, `src/mcp/`
**Test Files**: `tests/claude_coms/test_init.py`, `tests/mcp/test_init.py`

## Working Code Example

```python
# COPY THIS PATTERN for empty module tests:
import importlib
import sys
from pathlib import Path

def test_module_imports():
    """Test that empty modules can be imported."""
    # Add project to path
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Test claude_coms module
    try:
        import claude_coms
        assert claude_coms is not None
        print("✅ claude_coms module imports successfully")
    except ImportError as e:
        assert False, f"Failed to import claude_coms: {e}"
    
    # Test mcp module
    try:
        import claude_coms.mcp
        assert claude_coms.mcp is not None
        print("✅ mcp module imports successfully")
    except ImportError as e:
        assert False, f"Failed to import mcp: {e}"

if __name__ == "__main__":
    test_module_imports()
```

---

### SubTask 4: Integration Test - Full Pipeline

**Test File**: `tests/test_integration.py`

## Working Code Example

```python
# COPY THIS INTEGRATION TEST PATTERN:
import asyncio
import tempfile
import json
from pathlib import Path
from typer.testing import CliRunner
from claude_coms.cli.communication_commands import app
from claude_coms.core.progress_utils import init_database, get_session_statistics

runner = CliRunner()

async def test_full_communication_pipeline():
    """Test complete module communication pipeline with real data."""
    # Setup test data
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        
        # Create database
        db_path = tmppath / "test.db"
        await init_database(str(db_path))
        
        # Create pipeline config
        pipeline_config = tmppath / "pipeline.json"
        pipeline_config.write_text(json.dumps({
            "session_id": "integration_test_001",
            "database": str(db_path),
            "modules": [
                {
                    "name": "data_collector",
                    "version": "1.0.0",
                    "output_schema": {"type": "object", "properties": {"data": {"type": "array"}}}
                },
                {
                    "name": "data_processor",
                    "version": "1.0.0",
                    "input_schema": {"type": "object", "properties": {"data": {"type": "array"}}},
                    "output_schema": {"type": "object", "properties": {"processed": {"type": "object"}}}
                }
            ]
        }))
        
        # Test pipeline validation
        result = runner.invoke(app, ["validate-pipeline", str(pipeline_config)])
        assert result.exit_code == 0
        assert "Pipeline validation: PASS" in result.stdout
        
        # Test monitoring
        monitor_result = runner.invoke(app, ["monitor-session", str(pipeline_config)])
        assert monitor_result.exit_code == 0
        
        # Verify session statistics
        stats = await get_session_statistics(str(db_path), "integration_test_001")
        assert stats is not None
        assert stats["session_id"] == "integration_test_001"
        
        return True

# Run integration test
if __name__ == "__main__":
    result = asyncio.run(test_full_communication_pipeline())
    if result:
        print("✅ Integration test passed!")
```

## Success Criteria (ALL MUST PASS)

- [ ] All CLI command tests pass with real data
- [ ] Progress tracking tests work with real SQLite database
- [ ] Module import tests confirm proper structure
- [ ] Integration test validates full pipeline
- [ ] No mocked functionality (per CLAUDE.md)
- [ ] All tests use real data and file operations
- [ ] Test coverage > 80% for implemented modules

## Validation Process

1. **Create test structure**:
   ```bash
   mkdir -p tests/cli tests/core tests/claude_coms tests/mcp
   touch tests/__init__.py tests/cli/__init__.py tests/core/__init__.py
   touch tests/claude_coms/__init__.py tests/mcp/__init__.py
   ```

2. **Run all tests**:
   ```bash
   cd /home/graham/workspace/experiments/granger_hub
   source .venv/bin/activate
   export PYTHONPATH="${PYTHONPATH}:${PWD}"
   pytest tests/ -v --tb=short
   ```

3. **Check coverage**:
   ```bash
   pytest tests/ --cov=src --cov-report=html --cov-report=term
   ```

## Expected Final Output

```
=================== test session starts ===================
tests/cli/test_communication_commands.py::test_negotiate_schema_command PASSED
tests/cli/test_communication_commands.py::test_verify_compatibility_command PASSED
tests/core/test_progress_utils.py::test_progress_tracking_with_real_db PASSED
tests/claude_coms/test_init.py::test_module_imports PASSED
tests/mcp/test_init.py::test_module_imports PASSED
tests/test_integration.py::test_full_communication_pipeline PASSED

=================== 6 passed in 2.3s ===================
```