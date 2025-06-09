"""
Simple Conversation Test Validator.

Purpose: Validate conversation test results without complex dependencies.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List


def validate_conversation_tests(json_report_path: str) -> Dict[str, Any]:
    """Validate pytest JSON report for conversation authenticity."""
    with open(json_report_path, 'r') as f:
        report_data = json.load(f)
    
    tests = report_data.get("tests", [])
    results = []
    
    for test in tests:
        test_name = test.get("nodeid", "").split("::")[-1]
        outcome = test.get("outcome", "")
        # Get duration from call section
        call_data = test.get("call", {})
        duration = call_data.get("duration", 0.0)
        
        # Check for honeypot
        if "impossible" in test_name.lower() or "honeypot" in test_name.lower():
            if outcome == "failed":
                verdict = "REAL"
                reason = "Honeypot correctly failed"
            else:
                verdict = "FAKE" 
                reason = "Honeypot passed when it should fail"
        else:
            # Regular test validation
            if duration < 0.01:  # Less than 10ms is too fast
                verdict = "FAKE"
                reason = f"Duration {duration}s is too fast for real conversation"
            elif duration > 0.015:  # More than 15ms is realistic for db operations
                verdict = "REAL"
                reason = f"Duration {duration}s indicates real processing"
            else:
                verdict = "SUSPICIOUS"
                reason = f"Duration {duration}s is borderline"
        
        results.append({
            "test": test_name,
            "outcome": outcome,
            "duration": duration,
            "verdict": verdict,
            "reason": reason
        })
    
    # Summary
    real_count = sum(1 for r in results if r["verdict"] == "REAL")
    fake_count = sum(1 for r in results if r["verdict"] == "FAKE")
    total = len(results)
    
    return {
        "tests": results,
        "summary": {
            "total": total,
            "real": real_count,
            "fake": fake_count,
            "real_percentage": (real_count / total * 100) if total > 0 else 0
        }
    }


def main():
    """CLI for simple validation."""
    if len(sys.argv) < 2:
        print("Usage: python simple_conversation_validator.py <pytest_json_report>")
        sys.exit(1)
    
    json_report = sys.argv[1]
    
    # Validate
    results = validate_conversation_tests(json_report)
    
    # Print results
    print("\n=== CONVERSATION TEST VALIDATION ===")
    print(f"\nTotal tests: {results['summary']['total']}")
    print(f"REAL tests: {results['summary']['real']} ({results['summary']['real_percentage']:.1f}%)")
    print(f"FAKE tests: {results['summary']['fake']}")
    
    print("\nDetailed Results:")
    for test in results["tests"]:
        status = "" if test["verdict"] == "REAL" else ""
        print(f"{status} {test['test']}: {test['verdict']} - {test['reason']}")
    
    # Overall verdict
    if results['summary']['real_percentage'] >= 60:
        print("\n VERDICT: Tests appear to be REAL multi-turn conversations!")
    else:
        print("\n⚠️  VERDICT: Tests appear to be FAKE - implement real conversation logic!")


if __name__ == "__main__":
    main()