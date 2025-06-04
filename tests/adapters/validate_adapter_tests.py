"""
Simple adapter test validation script.

Purpose: Validate that adapter tests are REAL protocol adapter tests, 
not mocked or unrealistic simulations.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List


def validate_adapter_test(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a single adapter test."""
    nodeid = test_data.get("nodeid", "")
    outcome = test_data.get("outcome", "")
    stdout = test_data.get("call", {}).get("stdout", "")
    
    # Extract evidence from stdout
    evidence = {}
    if "Test Evidence:" in stdout:
        try:
            evidence_str = stdout.split("Test Evidence:")[-1].strip()
            evidence = eval(evidence_str)  # Safe since we control the test output
        except:
            pass
    
    # Check for REAL adapter indicators
    is_real = True
    reasons = []
    
    # Check adapter type
    adapter_type = evidence.get("adapter_type", "unknown")
    
    if "honeypot" in nodeid.lower() or evidence.get("honeypot"):
        is_real = False
        reasons.append("Identified as honeypot test")
    elif adapter_type == "base_lifecycle":
        # Base adapter lifecycle test
        if evidence.get("connection_established") and evidence.get("health_check_passed"):
            reasons.append("Real connection lifecycle with health check")
        else:
            is_real = False
            reasons.append("Missing connection or health check")
    elif adapter_type == "cli":
        # CLI adapter test
        if evidence.get("commands_executed", 0) > 0 and evidence.get("output_captured"):
            reasons.append(f"Executed {evidence.get('commands_executed', 0)} real CLI commands")
        else:
            is_real = False
            reasons.append("No real CLI command execution")
    elif adapter_type == "rest":
        # REST adapter test
        if evidence.get("requests_made", 0) > 0 and evidence.get("latency_tracked"):
            reasons.append(f"Made {evidence.get('requests_made', 0)} real HTTP requests with latency tracking")
        else:
            is_real = False
            reasons.append("No real HTTP requests")
    elif adapter_type == "mcp":
        # MCP adapter test
        if evidence.get("tools_discovered", 0) > 0 and evidence.get("tool_invoked"):
            reasons.append(f"Discovered {evidence.get('tools_discovered', 0)} MCP tools and invoked them")
        else:
            is_real = False
            reasons.append("No real MCP tool interaction")
    
    # Check timing
    duration = evidence.get("duration_seconds", 0)
    if duration > 0:
        reasons.append(f"Test took {duration:.3f} seconds (realistic timing)")
    elif is_real:
        is_real = False
        reasons.append("Instant execution (unrealistic)")
    
    return {
        "test": nodeid,
        "passed": outcome == "passed",
        "is_real": is_real,
        "adapter_type": adapter_type,
        "evidence": evidence,
        "reasons": reasons
    }


def validate_adapter_tests(json_report_path: str) -> None:
    """Validate adapter tests from pytest JSON report."""
    with open(json_report_path) as f:
        report = json.load(f)
    
    tests = report.get("tests", [])
    results = []
    
    for test in tests:
        result = validate_adapter_test(test)
        results.append(result)
    
    # Print report
    print("\n=== ADAPTER TEST VALIDATION REPORT ===\n")
    
    real_count = sum(1 for r in results if r["is_real"])
    fake_count = len(results) - real_count
    
    print(f"Total tests: {len(results)}")
    print(f"REAL adapter tests: {real_count}")
    print(f"FAKE/Mock tests: {fake_count}")
    print()
    
    # Detailed results
    for result in results:
        verdict = "✅ REAL" if result["is_real"] else "❌ FAKE"
        status = "PASSED" if result["passed"] else "FAILED"
        
        print(f"\nTest: {result['test']}")
        print(f"Status: {status}")
        print(f"Verdict: {verdict}")
        print(f"Adapter Type: {result['adapter_type']}")
        print("Reasons:")
        for reason in result["reasons"]:
            print(f"  - {reason}")
        if result["evidence"]:
            print(f"Evidence: {result['evidence']}")
    
    # Overall verdict
    print("\n=== OVERALL VERDICT ===")
    if real_count >= len(results) - 1:  # Allow 1 honeypot
        print("✅ Test suite contains REAL adapter implementations!")
        print(f"   {real_count} real tests demonstrate actual protocol communication.")
    else:
        print("❌ Test suite appears to be mostly mocked.")
        print(f"   Only {real_count} out of {len(results)} tests are real.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_adapter_tests.py <json_report_path>")
        sys.exit(1)
    
    validate_adapter_tests(sys.argv[1])