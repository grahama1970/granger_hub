#!/usr/bin/env python3
"""
Example test runner for Level 0 scenarios
Tests single module CLI invocations through claude-module-communicator
"""

import json
import subprocess
import sys
from pathlib import Path

# Example Level 0 test scenarios
LEVEL_0_TESTS = [
    {
        "id": "screenshot_01",
        "description": "Full screen capture with high quality",
        "command": ["claude-comm", "screenshot", "--output", "test_dashboard.png", "--quality", "95"],
        "expected": {"type": "file", "extension": ".png"}
    },
    {
        "id": "arangodb_01", 
        "description": "Create memory with tags",
        "command": ["claude-comm", "send", "arangodb", "memory", "create",
                   "--user", "How do transformers work?",
                   "--agent", "Transformers use attention mechanisms",
                   "--tags", "ml,nlp,architecture"],
        "expected": {"type": "response", "contains": "memory_id"}
    },
    {
        "id": "llm_01",
        "description": "Ask Gemini Flash a question",
        "command": ["claude-comm", "send", "claude_max_proxy", "ask",
                   "--model", "gemini/gemini-2.0-flash-exp",
                   "--prompt", "Explain quantum entanglement in one sentence"],
        "expected": {"type": "response", "min_length": 50}
    }
]

def run_test(test_case):
    """Run a single test scenario"""
    print(f"\n🧪 Testing: {test_case['description']}")
    print(f"   Command: {' '.join(test_case['command'])}")
    
    try:
        # Run the command
        result = subprocess.run(
            test_case['command'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check basic success
        if result.returncode != 0:
            print(f"   ❌ Failed with return code: {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False
            
        # Validate based on expected type
        expected = test_case['expected']
        
        if expected['type'] == 'file':
            # Check if output file was created
            output_file = None
            for arg in test_case['command']:
                if arg.endswith(expected['extension']):
                    output_file = arg
                    break
            
            if output_file and Path(output_file).exists():
                print(f"   ✅ Success: File created - {output_file}")
                return True
            else:
                print(f"   ❌ Failed: Expected file not created")
                return False
                
        elif expected['type'] == 'response':
            # Check response content
            output = result.stdout
            
            if 'contains' in expected and expected['contains' ] in output:
                print(f"   ✅ Success: Response contains '{expected['contains']}'")
                return True
            elif 'min_length' in expected and len(output) >= expected['min_length']:
                print(f"   ✅ Success: Response length {len(output)} >= {expected['min_length']}")
                return True
            else:
                print(f"   ❌ Failed: Response validation failed")
                print(f"   Output: {output[:200]}...")
                return False
                
    except subprocess.TimeoutExpired:
        print(f"   ❌ Failed: Command timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"   ❌ Failed with exception: {e}")
        return False

def main():
    """Run all Level 0 tests"""
    print("🚀 Level 0 Test Runner - Single Module CLI Operations")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test in LEVEL_0_TESTS:
        if run_test(test):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✨ All tests passed! Ready for Level 1 testing.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
