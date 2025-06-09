#!/usr/bin/env python3
"""Generate test report from JSON results."""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))



from datetime import datetime
from pathlib import Path
import json

# Load test results
with open('test_results.json') as f:
    data = json.load(f)

# Generate report
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
report_path = Path(f'docs/reports/test_report_{timestamp}.md')
report_path.parent.mkdir(parents=True, exist_ok=True)

# Create report content
total_tests = data['summary']['total']
passed = data['summary']['passed']
failed = data['summary']['failed']
skipped = data['summary']['skipped']
errors = data['summary']['error']

content = f'''# Test Report - Granger Hub
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- **Total Tests**: {total_tests}
- **Passed**: {passed} 
- **Failed**: {failed} 
- **Errors**: {errors} ⚠️
- **Skipped**: {skipped} ⏭️
- **Success Rate**: {(passed / total_tests * 100 if total_tests > 0 else 0):.1f}%

## Test Results by Module

| Module | Tests | Passed | Failed | Errors | Status |
|--------|-------|--------|--------|--------|--------|
'''

# Group tests by module
modules = {}
for test in data['tests']:
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

# Add module results to report
for module, stats in sorted(modules.items()):
    status = '' if stats['failed'] == 0 and stats['error'] == 0 else ''
    content += f"| {module} | {stats['total']} | {stats['passed']} | {stats['failed']} | {stats['error']} | {status} |\n"

content += f'''

## Import Issues Fixed
- Fixed incorrect import paths from claude-module-communicator to granger_hub
- Fixed relative imports to use absolute imports per CLAUDE.md standards
- Added missing class definitions (LLMModel, LLMRequest)
- Fixed import paths for moved modules (BaseModule, ModuleRegistry, etc.)

## Remaining Issues
- Some test fixtures need updating for changed APIs
- Abstract method implementations needed in some test modules
- ArangoDB connection tests require running database

## Recommendations
1. Update test fixtures to match current module interfaces
2. Mock external dependencies (ArangoDB, Ollama) for unit tests
3. Create integration test suite with proper environment setup
'''

# Write report
report_path.write_text(content)
print(f'Report generated: {report_path}')