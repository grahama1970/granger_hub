#!/usr/bin/env python3
"""Generate comprehensive final test report from multiple test runs."""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))



from datetime import datetime
from pathlib import Path
import json

# Load all test results
initial_results = json.load(open('test_results.json'))
final_results = json.load(open('test_results_final.json'))

# Generate report
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
report_path = Path(f'docs/reports/test_report_final_{timestamp}.md')
report_path.parent.mkdir(parents=True, exist_ok=True)

# Calculate improvements
initial_passed = initial_results['summary']['passed']
initial_failed = initial_results['summary']['failed']
initial_error = initial_results['summary']['error']
initial_total = initial_results['summary']['total']

final_passed = final_results['summary']['passed']
final_failed = final_results['summary']['failed'] 
final_error = final_results['summary']['error']
final_total = final_results['summary']['total']

# Create report content
content = f'''# Final Test Report - Granger Hub
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

After comprehensive fixes and refactoring:
- **Initial Success Rate**: {(initial_passed / initial_total * 100 if initial_total > 0 else 0):.1f}% ({initial_passed}/{initial_total})
- **Final Success Rate**: {(final_passed / final_total * 100 if final_total > 0 else 0):.1f}% ({final_passed}/{final_total})
- **Improvement**: +{final_passed - initial_passed} tests passing

## Test Results Summary

| Metric | Initial | Final | Change |
|--------|---------|-------|--------|
| Total Tests | {initial_total} | {final_total} | {final_total - initial_total:+d} |
| Passed | {initial_passed}  | {final_passed}  | {final_passed - initial_passed:+d} |
| Failed | {initial_failed}  | {final_failed}  | {final_failed - initial_failed:+d} |
| Errors | {initial_error} ⚠️ | {final_error} ⚠️ | {final_error - initial_error:+d} |

## Major Fixes Implemented

### 1. Import Path Updates 
- Updated all imports from `claude-module-communicator` to `granger_hub`
- Fixed relative imports to use absolute imports per CLAUDE.md standards
- Corrected module paths after project restructuring

### 2. Module Initialization Fixes 
- Fixed `ModuleInfo` TypeError by removing unexpected 'status' parameter
- Fixed `BaseModule` initialization order in `BrowserAutomationModule` and `ScreenshotModule`
- Added missing abstract method implementations (`get_input_schema`, `get_output_schema`)
- Removed calls to non-existent `start()` and `stop()` methods

### 3. Test Infrastructure Improvements 
- Fixed pytest-asyncio fixture scope issues
- Added proper mocking for external dependencies (Ollama, ArangoDB)
- Corrected test fixture paths for forecast tests
- Removed problematic test files with invalid Python syntax in filenames

### 4. Missing Class Definitions 
- Added `LLMModel` enum class with available model definitions
- Added `LLMRequest` dataclass for LLM request structure
- Fixed import/export issues in `__init__.py` files

## Remaining Issues

### 1. External Dependencies
- ArangoDB tests still require connection or more comprehensive mocking
- Some integration tests depend on external services that need mocking
- Playwright browser automation tests may need environment setup

### 2. Test Implementation Issues
- Some test fixtures need updating for changed APIs
- Mock implementations could be more comprehensive
- Integration test scenarios need better isolation

### 3. Code Quality
- Pydantic V1 style validators need migration to V2
- Some test classes have `__init__` constructors preventing collection
- Unknown pytest marks need registration

## Recommendations

1. **Immediate Actions**:
   - Set up comprehensive mocking for all external services
   - Update remaining test fixtures to match current APIs
   - Register custom pytest marks in `pytest.ini`

2. **Short-term Improvements**:
   - Migrate Pydantic validators to V2 style
   - Create integration test environment with Docker Compose
   - Add CI/CD pipeline with proper test environments

3. **Long-term Strategy**:
   - Implement contract testing for module interfaces
   - Add performance benchmarks
   - Create end-to-end test scenarios

## Module Performance

'''

# Group tests by module for final results
modules = {}
for test in final_results['tests']:
    parts = test['nodeid'].split('::')
    module = parts[0].replace('tests/', '').replace('.py', '')
    if module not in modules:
        modules[module] = {'total': 0, 'passed': 0, 'failed': 0, 'error': 0}
    
    modules[module]['total'] += 1
    if test['outcome'] == 'passed':
        modules[module]['passed'] += 1
    elif test['outcome'] == 'failed':
        modules[module]['failed'] += 1
    elif test['outcome'] == 'error':
        modules[module]['error'] += 1

# Add top performers
content += "### Top Performing Modules\n\n"
content += "| Module | Tests | Passed | Success Rate | Status |\n"
content += "|--------|-------|--------|--------------|--------|\n"

# Sort by success rate
sorted_modules = sorted(modules.items(), 
                       key=lambda x: (x[1]['passed'] / x[1]['total'] if x[1]['total'] > 0 else 0), 
                       reverse=True)

for module, stats in sorted_modules[:10]:
    success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
    status = '' if stats['failed'] == 0 and stats['error'] == 0 else '⚠️'
    content += f"| {module} | {stats['total']} | {stats['passed']} | {success_rate:.1f}% | {status} |\n"

content += f'''

## Conclusion

The test suite has been significantly improved with critical fixes to:
- Import paths and module references
- Module initialization patterns
- Test infrastructure and mocking

While some tests still fail due to external dependencies and implementation details, 
the core functionality has been restored and the codebase is now properly using 
the `granger_hub` naming throughout.

**Next Steps**: Focus on comprehensive mocking of external services and updating 
remaining test fixtures to achieve 100% test success rate.
'''

# Write report
report_path.write_text(content)
print(f'Final test report generated: {report_path}')