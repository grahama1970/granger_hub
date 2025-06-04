"""
Simple event system test validation script.

Purpose: Validate that event tests demonstrate REAL pub/sub communication,
event patterns, and module integration, not mocked behavior.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List


def validate_event_test(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a single event test."""
    nodeid = test_data.get("nodeid", "")
    outcome = test_data.get("outcome", "")
    stdout = test_data.get("call", {}).get("stdout", "")
    
    # Extract evidence from stdout
    evidence = {}
    if "Test Evidence:" in stdout:
        try:
            evidence_str = stdout.split("Test Evidence:")[-1].strip()
            if "Honeypot Evidence:" in evidence_str:
                evidence_str = evidence_str.split("Honeypot Evidence:")[0].strip()
            evidence = eval(evidence_str)  # Safe since we control the test output
        except:
            pass
    elif "Honeypot Evidence:" in stdout:
        try:
            evidence_str = stdout.split("Honeypot Evidence:")[-1].strip()
            evidence = eval(evidence_str)
        except:
            pass
    
    # Check for REAL event system indicators
    is_real = True
    reasons = []
    
    # Check test type
    test_type = evidence.get("test_type", "unknown")
    
    if "honeypot" in nodeid.lower() or evidence.get("honeypot"):
        is_real = False
        reasons.append("Identified as honeypot test")
    elif test_type == "basic_pub_sub":
        # Basic pub/sub test
        if evidence.get("subscription_worked") and evidence.get("unsubscription_worked"):
            reasons.append("Real pub/sub with working subscriptions")
        else:
            is_real = False
            reasons.append("No real pub/sub behavior")
    elif test_type == "pattern_subscriptions":
        # Pattern subscription test
        if evidence.get("patterns_used") and evidence.get("double_match_handled"):
            reasons.append(f"Real pattern matching with {len(evidence.get('patterns_used', []))} patterns")
        else:
            is_real = False
            reasons.append("No real pattern matching")
    elif test_type == "priority_handling":
        # Priority test
        handler_order = evidence.get("handler_order", [])
        if handler_order == ["high", "normal", "low"]:
            reasons.append("Real priority-based handler execution")
        else:
            is_real = False
            reasons.append("Incorrect priority ordering")
    elif test_type == "event_history":
        # History test
        if evidence.get("history_maintained") and evidence.get("events_replayed", 0) > 0:
            reasons.append(f"Real event history with {evidence.get('events_replayed', 0)} events replayed")
        else:
            is_real = False
            reasons.append("No real event history")
    elif test_type == "event_aware_module":
        # Module integration test
        if evidence.get("lifecycle_events") and evidence.get("message_events"):
            reasons.append(f"Real module integration with {evidence.get('events_emitted', 0)} events")
        else:
            is_real = False
            reasons.append("No real module event integration")
    elif test_type == "event_aware_communicator":
        # Communicator integration test
        if evidence.get("subscriber_working") and evidence.get("total_events", 0) > 0:
            reasons.append(f"Real communicator integration with {evidence.get('total_events', 0)} events")
        else:
            is_real = False
            reasons.append("No real communicator integration")
    elif test_type == "error_handling":
        # Error handling test
        if evidence.get("errors_caught", 0) > 0:
            reasons.append(f"Real error handling for {evidence.get('error_types', [])}")
        else:
            is_real = False
            reasons.append("No real error handling")
    
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
        "test_type": test_type,
        "evidence": evidence,
        "reasons": reasons
    }


def validate_event_tests(json_report_path: str) -> None:
    """Validate event tests from pytest JSON report."""
    with open(json_report_path) as f:
        report = json.load(f)
    
    tests = report.get("tests", [])
    results = []
    
    for test in tests:
        result = validate_event_test(test)
        results.append(result)
    
    # Print report
    print("\n=== EVENT SYSTEM TEST VALIDATION REPORT ===\n")
    
    real_count = sum(1 for r in results if r["is_real"])
    fake_count = len(results) - real_count
    
    print(f"Total tests: {len(results)}")
    print(f"REAL event tests: {real_count}")
    print(f"FAKE/Mock tests: {fake_count}")
    print()
    
    # Detailed results
    for result in results:
        verdict = "✅ REAL" if result["is_real"] else "❌ FAKE"
        status = "PASSED" if result["passed"] else "FAILED"
        
        print(f"\nTest: {result['test']}")
        print(f"Status: {status}")
        print(f"Verdict: {verdict}")
        print(f"Test Type: {result['test_type']}")
        print("Reasons:")
        for reason in result["reasons"]:
            print(f"  - {reason}")
        if result["evidence"]:
            # Print key evidence
            if "total_events" in result["evidence"]:
                print(f"  Total events: {result['evidence']['total_events']}")
            if "events_emitted" in result["evidence"]:
                print(f"  Events emitted: {result['evidence']['events_emitted']}")
    
    # Overall verdict
    print("\n=== OVERALL VERDICT ===")
    if real_count >= len(results) - 1:  # Allow 1 honeypot
        print("✅ Test suite contains REAL event system implementation!")
        print(f"   {real_count} real tests demonstrate actual pub/sub communication.")
    else:
        print("❌ Test suite appears to be mostly mocked.")
        print(f"   Only {real_count} out of {len(results)} tests are real.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_event_tests.py <json_report_path>")
        sys.exit(1)
    
    validate_event_tests(sys.argv[1])