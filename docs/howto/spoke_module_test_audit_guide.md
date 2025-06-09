# Spoke Module Test Audit Guide

This guide provides a systematic approach to auditing, updating, and maintaining tests for all spoke modules in the Granger ecosystem. Following CLAUDE.md standards and TASK_LIST_TEMPLATE_GUIDE_V2.md compliance framework, all tests must use real APIs and services - NO MOCKS ALLOWED.

## Key Requirements

1. **REAL Tests Only**: Tests must interact with live systems (databases, APIs)
2. **Performance Criteria**: Tests must meet minimum duration requirements (e.g., >0.1s for DB operations)
3. **Confidence Threshold**: Tests must achieve ≥90% confidence rating
4. **Maximum 3 Loops**: Each test task gets maximum 3 verification loops before escalation
5. **Honeypot Tests**: Include tests designed to fail to verify testing integrity

## Overview

The Granger ecosystem consists of multiple spoke modules that need proper test coverage:

### Core Spoke Modules to Audit

1. **Data Collection & Crawling**
   - `darpa_crawl` - DARPA dataset collection
   - `gitget` - Git repository analysis
   
2. **Document Processing**
   - `sparta` - Document analysis and processing
   - `marker` - PDF extraction and markup
   
3. **Data Storage & Retrieval**
   - `arangodb` - Graph database operations
   
4. **Media Processing**
   - `youtube_transcripts` - YouTube transcript extraction
   
5. **AI Services**
   - `llm_call` - LLM API interface
   - `unsloth_wip` - Model training integration
   
6. **MCP Services**
   - `arxiv-mcp-server` - ArXiv paper search
   - `mcp-screenshot` - Screenshot capture service

## Test Audit Process

### 1. Initial Assessment

For each spoke module, run the following commands:

```bash
# Navigate to module directory
cd /home/graham/workspace/experiments/<module_name>/

# Check test structure
find tests/ -name "*.py" -type f | head -20

# Run tests to identify failures/skips
pytest tests/ -v --tb=short | grep -E "(FAILED|SKIPPED|passed)"

# Check for mocks
grep -r "mock\|Mock\|@patch" tests/ --include="*.py" | wc -l

# Check for validate_* files (banned by CLAUDE.md)
find . -name "validate_*.py" -type f

# Verify test durations meet minimum requirements
pytest tests/ -v --durations=0 | grep -E "\d+\.\d+s"
```

### 2. Common Issues to Fix

#### A. Mocked Tests
**Issue**: Tests using mocks instead of real services
**Fix**: 
```python
# BEFORE (BAD)
@patch('module.external_service')
def test_feature(mock_service):
    mock_service.return_value = {"data": "fake"}
    
# AFTER (GOOD)
def test_feature():
    # Use real service
    service = ExternalService()
    result = service.get_data()
    assert result["data"] is not None
```

#### B. Skipped Tests
**Issue**: Tests skipped due to missing dependencies
**Fix Options**:
1. Install missing dependencies in pyproject.toml
2. Remove tests if service is not essential
3. Ensure services are running (Docker containers, etc.)

#### C. Deprecated Test Patterns
**Issue**: Old test patterns from pre-CLAUDE.md era
**Fix**: Update to current standards
```python
# Remove validate_*.py scripts
# Convert to proper pytest tests under tests/
# Ensure real data is used, not fixtures
```

### 3. Test Loop Process

For each module, follow the TASK_LIST_TEMPLATE_GUIDE_V2.md test loop:

```
CURRENT LOOP: #1 (max 3)
1. RUN tests → Generate JSON/HTML reports
2. EVALUATE tests: Mark as REAL or FAKE based on:
   - Duration (must meet minimum thresholds)
   - System interaction (real APIs, no mocks)
   - Report contents (actual data)
3. VALIDATE authenticity and confidence:
   - Query: "Rate confidence (0-100%) that this test used live systems"
   - IF confidence < 90% → Mark test as FAKE
   - IF confidence ≥ 90% → Cross-examine
4. CROSS-EXAMINE high confidence claims:
   - "What was the exact connection string used?"
   - "How many milliseconds did the handshake take?"
   - "What warnings appeared in the logs?"
   - "What was the exact query executed?"
5. IF any FAKE → Fix → Increment loop (max 3)
6. IF loop fails 3 times → Escalate with full analysis
```

### 4. Service Requirements by Module

#### darpa_crawl
- **External Services**: Web scraping targets
- **Setup**: No special setup, uses public websites
- **Common Issues**: Rate limiting, changing HTML structure

#### gitget
- **External Services**: GitHub API
- **Setup**: Requires GitHub token in environment
- **Common Issues**: API rate limits

#### sparta
- **External Services**: Document sources
- **Setup**: Test documents in fixtures/
- **Common Issues**: Missing test PDFs

#### marker
- **External Services**: marker-pdf package
- **Setup**: `uv add marker-pdf`
- **Common Issues**: ML model dependencies

#### arangodb
- **External Services**: ArangoDB
- **Setup**: Docker container running on port 8529
- **Common Issues**: Connection refused if not running

#### youtube_transcripts
- **External Services**: YouTube API
- **Setup**: API key required
- **Common Issues**: Quota limits

#### llm_call
- **External Services**: Multiple LLM APIs
- **Setup**: API keys for Claude, GPT, Gemini
- **Common Issues**: Missing API keys, rate limits

#### arxiv-mcp-server
- **External Services**: ArXiv API
- **Setup**: No special setup
- **Common Issues**: Rate limiting

#### mcp-screenshot
- **External Services**: Playwright browsers
- **Setup**: `playwright install chromium`
- **Common Issues**: Missing browser binaries

### 5. Test Update Checklist with Confidence Requirements

For each module, complete this enhanced checklist:

- [ ] Remove all `@patch`, `Mock()`, and mock fixtures
- [ ] Delete any `validate_*.py` files
- [ ] Ensure all external services are documented
- [ ] Add service checks in conftest.py
- [ ] Update tests to use real APIs
- [ ] Add proper error handling for service failures
- [ ] Document service setup in module README
- [ ] Run tests with actual services
- [ ] Fix or remove all skipped tests
- [ ] Achieve >90% test success rate
- [ ] **Add honeypot tests** (designed to fail)
- [ ] **Verify test durations** meet minimums:
  - DB operations: >0.1s
  - API calls: >0.05s
  - File operations: >0.01s
- [ ] **Document confidence levels** for each test
- [ ] **Complete test loop** (max 3 iterations)

### 6. Honeypot Test Pattern

Every module MUST include honeypot tests to verify testing integrity:

```python
# tests/test_honeypot.py
import pytest

class TestHoneypot:
    """Honeypot tests designed to fail - verify testing integrity."""
    
    @pytest.mark.honeypot
    def test_impossible_assertion(self):
        """This test MUST fail to prove we're not faking results."""
        assert 1 == 2, "If this passes, testing framework is compromised"
    
    @pytest.mark.honeypot
    def test_fake_api_response(self):
        """Test that would only pass with mocks."""
        # This should fail because we're using real APIs
        import requests
        response = requests.get("https://fake-api-that-does-not-exist.com")
        assert response.status_code == 200, "Should fail with real network"
```

### 7. Example Service Check Pattern

Add to each module's `tests/conftest.py`:

```python
import pytest
import os

def pytest_collection_modifyitems(config, items):
    """Skip tests if required services aren't available."""
    # Check ArangoDB
    try:
        from arango import ArangoClient
        client = ArangoClient(hosts="http://localhost:8529")
        db = client.db("_system", username="root", password="")
        arangodb_available = True
    except:
        arangodb_available = False
    
    # Check API keys
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    
    # Apply markers
    skip_arangodb = pytest.mark.skip(reason="ArangoDB not available")
    skip_api = pytest.mark.skip(reason="API key not configured")
    
    for item in items:
        if "arangodb" in item.keywords and not arangodb_available:
            item.add_marker(skip_arangodb)
        if "requires_api_key" in item.keywords and not has_api_key:
            item.add_marker(skip_api)
```

### 8. Integration Test Pattern with Duration Validation

For cross-module integration tests:

```python
# tests/integration/test_sparta_marker_integration.py
import pytest
from pathlib import Path

class TestSpartaMarkerIntegration:
    """Test sparta -> marker pipeline with real services."""
    
    @pytest.mark.integration
    @pytest.mark.minimum_duration(0.5)  # Must take >0.5s
    async def test_document_pipeline(self):
        """Test full document processing pipeline."""
        import time
        start_time = time.time()
        
        # 1. Use sparta to download document
        from sparta import DocumentDownloader
        downloader = DocumentDownloader()
        doc_path = await downloader.fetch_document("https://example.com/doc.pdf")
        
        # 2. Use marker to extract content
        from marker.converters.pdf import PdfConverter
        converter = PdfConverter({})
        content = converter.convert(str(doc_path))
        
        # 3. Verify results
        assert content is not None
        assert len(content.markdown) > 0
        
        # 4. Verify duration
        duration = time.time() - start_time
        assert duration > 0.5, f"Test too fast ({duration}s) - likely using mocks"
```

### 9. Test Loop Evaluation Table

For each test loop iteration, document results:

| Test ID | Duration | Verdict | Why | Confidence % | LLM Certainty Report | Evidence Provided | Fix Applied | Fix Metadata |
|---------|----------|---------|-----|--------------|---------------------|-------------------|-------------|--------------|
| MOD.1   | 0.001s   | FAKE    | Too fast | 45% | "Likely mocked" | No connection info | Remove mocks | Loop 1 |
| MOD.2   | 0.15s    | REAL    | Good duration | 95% | "Real API used" | "Connected to localhost:8529" | None | - |
| MOD.H   | FAIL     | PASS    | Honeypot worked | - | - | - | - | - |

### 10. Reporting Template

After auditing each module, create a report:

```markdown
## Module: <module_name>
**Date Audited**: YYYY-MM-DD
**Auditor**: <your_name>

### Current State
- Total Tests: X
- Passing: Y (Z%)
- Failing: A
- Skipped: B
- Using Mocks: C files
- **Honeypot Tests**: D (should all fail)
- **Average Confidence**: E%
- **Test Loops Completed**: F/3

### Confidence Analysis
- Tests with ≥90% confidence: X
- Tests with 50-89% confidence: Y
- Tests with <50% confidence: Z
- Honeypot detection rate: A/B (should be 100%)

### Issues Found
1. [Issue description]
2. [Issue description]

### Actions Taken
1. [Action description]
2. [Action description]

### Remaining Work
- [ ] Task 1
- [ ] Task 2

### Service Dependencies
- Service 1: Status
- Service 2: Status
```

## Priority Order

Based on importance and dependencies:

1. **arangodb** - Core data storage
2. **llm_call** - Central to AI operations
3. **marker** - Document processing pipeline
4. **arxiv-mcp-server** - Research capabilities
5. **youtube_transcripts** - Media processing
6. **sparta** - Document ingestion
7. **gitget** - Code analysis
8. **darpa_crawl** - Funding acquisition
9. **mcp-screenshot** - UI automation
10. **unsloth_wip** - Training pipeline

## Success Criteria

A module's tests are considered properly updated when:

1. **No mocks**: Zero usage of mock/patch decorators
2. **No skips**: All tests run (or are removed if obsolete)
3. **Real services**: Tests connect to actual APIs/databases
4. **High pass rate**: ≥90% of tests passing
5. **Documented**: Service requirements clearly stated
6. **Reproducible**: Another developer can run tests successfully
7. **Confidence threshold**: All tests achieve ≥90% confidence
8. **Duration requirements**: Tests meet minimum time thresholds
9. **Honeypot validation**: All honeypot tests fail as expected
10. **Test loops**: Completed within 3 iterations

## Automatic Validation Triggers

⚠️ **AUTOMATIC VALIDATION TRIGGERED if:**
- Any module shows 100% confidence on ALL tests
- Honeypot test passes when it should fail
- Pattern of always-high confidence without evidence
- Test durations consistently below minimums

**Action**: Insert additional honeypot tests and escalate to human review

## Maintenance

- **Weekly**: Run test suite for active modules
- **Monthly**: Full audit of all modules
- **On change**: Update tests when module functionality changes
- **On failure**: Fix immediately, don't skip or mock

## Resources

- [CLAUDE.md Testing Standards](/home/graham/.claude/CLAUDE.md)
- [TASK_LIST_TEMPLATE_GUIDE_V2.md](/home/graham/workspace/shared_claude_docs/guides/TASK_LIST_TEMPLATE_GUIDE_V2.md)
- [Granger Projects Registry](/home/graham/workspace/shared_claude_docs/docs/GRANGER_PROJECTS.md)
- [Test Reporter Documentation](/home/graham/workspace/experiments/claude-test-reporter/README.md)

## Next Steps

1. Start with highest priority module (arangodb)
2. Run initial assessment commands
3. **Execute test loop process** (max 3 iterations)
4. Fix issues following the patterns above
5. **Validate confidence levels** (must be ≥90%)
6. **Verify honeypot tests fail**
7. Document in module's README
8. Move to next module
9. Create summary report when complete

## Example Module Audit Workflow

```bash
# Module: arangodb
# Loop 1
pytest tests/ -v --json-report --json-report-file=arangodb_loop1.json
sparta-cli test-report from-pytest arangodb_loop1.json --output-json reports/arangodb_loop1.json --output-html reports/arangodb_loop1.html

# Evaluate results
# If FAKE tests found, fix and continue to Loop 2
# If all REAL with ≥90% confidence, audit complete
# If Loop 3 fails, escalate with full analysis
```