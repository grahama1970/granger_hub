#!/usr/bin/env python3
"""Check which external services are required by failed tests."""

import json
import re
from collections import defaultdict

# Load test results
with open('test_results_final.json', 'r') as f:
    results = json.load(f)

# Categorize failed tests by external dependency
external_deps = defaultdict(list)
patterns = {
    'ArangoDB': r'(arango|ArangoDB|arangoexport|graph_backend)',
    'Ollama': r'(ollama|Ollama|forecast|llm)',
    'Playwright': r'(playwright|Playwright|browser|automation)',
    'Redis': r'(redis|Redis)',
    'WebSocket': r'(websocket|WebSocket)',
    'FastAPI': r'(fastapi|FastAPI|server)',
}

for test in results['tests']:
    if test['outcome'] != 'passed':
        nodeid = test['nodeid']
        error_msg = ''
        
        # Extract error message
        if isinstance(test.get('longrepr'), dict):
            error_msg = test['longrepr'].get('reprcrash', {}).get('message', '')
        elif isinstance(test.get('longrepr'), str):
            error_msg = test['longrepr']
        
        # Check for external dependencies
        test_text = f"{nodeid} {error_msg}"
        for dep, pattern in patterns.items():
            if re.search(pattern, test_text, re.IGNORECASE):
                external_deps[dep].append({
                    'test': nodeid,
                    'outcome': test['outcome'],
                    'error': error_msg[:100] if error_msg else 'No error message'
                })
                break
        else:
            # Check if it's a connection error
            if re.search(r'(connection|refused|timeout|not found|mock)', error_msg, re.IGNORECASE):
                external_deps['Connection Issues'].append({
                    'test': nodeid,
                    'outcome': test['outcome'],
                    'error': error_msg[:100] if error_msg else 'No error message'
                })

# Print summary
print("# External Service Dependencies in Failed Tests\n")
print(f"Total failed tests: {results['summary']['failed'] + results['summary']['error']}")
print(f"Total tests: {results['summary']['total']}\n")

for dep, tests in sorted(external_deps.items()):
    print(f"## {dep} ({len(tests)} tests)")
    for test_info in tests[:5]:  # Show first 5
        print(f"  - {test_info['test']}")
        print(f"    Status: {test_info['outcome']}")
        print(f"    Error: {test_info['error']}")
    if len(tests) > 5:
        print(f"  ... and {len(tests) - 5} more\n")
    else:
        print()

# Check which services are actually running
print("\n## Service Status Check\n")
import subprocess

services = [
    ('ArangoDB', 'curl -s http://localhost:8529/_api/version'),
    ('Ollama', 'curl -s http://localhost:11434/api/tags'),
    ('Redis', 'redis-cli ping'),
]

for name, cmd in services:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            print(f" {name}: Running")
        else:
            print(f" {name}: Not running or not accessible")
    except subprocess.TimeoutExpired:
        print(f" {name}: Timeout (not running)")
    except Exception as e:
        print(f" {name}: Error checking status: {e}")
