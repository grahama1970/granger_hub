"""
Simple binary test validation script.

Purpose: Validate that binary tests demonstrate REAL compression, 
streaming, and data handling, not mocked operations.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List


def validate_binary_test(test_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a single binary test."""
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
    
    # Check for REAL binary handling indicators
    is_real = True
    reasons = []
    
    # Check test type
    test_type = evidence.get("test_type", "unknown")
    
    if "honeypot" in nodeid.lower() or evidence.get("honeypot"):
        is_real = False
        reasons.append("Identified as honeypot test")
    elif test_type == "compression_methods":
        # Compression test
        methods_tested = evidence.get("methods_tested", 0)
        results = evidence.get("results", {})
        
        if methods_tested > 1 and evidence.get("data_integrity_verified"):
            # Check compression ratios
            real_compression = False
            for method, result in results.items():
                if method != "none" and result.get("compression_ratio", 0) > 1.5:
                    real_compression = True
                    break
            
            if real_compression:
                reasons.append(f"Tested {methods_tested} real compression methods with verified integrity")
            else:
                is_real = False
                reasons.append("No significant compression achieved")
        else:
            is_real = False
            reasons.append("Insufficient compression testing")
    elif test_type == "streaming":
        # Streaming test
        if evidence.get("total_chunks", 0) > 1 and evidence.get("reassembly_verified"):
            reasons.append(f"Streamed {evidence.get('data_size_mb', 0)}MB in {evidence.get('total_chunks', 0)} chunks")
        else:
            is_real = False
            reasons.append("No real streaming demonstrated")
    elif test_type == "file_compression":
        # File compression test
        if evidence.get("compression_ratio", 0) > 1.0 and evidence.get("file_integrity_verified"):
            reasons.append(f"Compressed {evidence.get('file_size_kb', 0)}KB file with ratio {evidence.get('compression_ratio', 0):.2f}")
        else:
            is_real = False
            reasons.append("No real file compression")
    elif test_type == "adapter_compression":
        # Adapter compression test
        if evidence.get("compression_achieved") and evidence.get("compression_ratio", 0) > 1.0:
            reasons.append(f"Adapter compressed data with ratio {evidence.get('compression_ratio', 0):.2f}")
        else:
            is_real = False
            reasons.append("No real adapter compression")
    elif test_type == "adapter_streaming":
        # Adapter streaming test
        if evidence.get("chunks_sent", 0) > 1 and evidence.get("throughput_mbps", 0) > 0:
            reasons.append(f"Adapter streamed {evidence.get('data_size_kb', 0)}KB in {evidence.get('chunks_sent', 0)} chunks")
        else:
            is_real = False
            reasons.append("No real adapter streaming")
    
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


def validate_binary_tests(json_report_path: str) -> None:
    """Validate binary tests from pytest JSON report."""
    with open(json_report_path) as f:
        report = json.load(f)
    
    tests = report.get("tests", [])
    results = []
    
    for test in tests:
        result = validate_binary_test(test)
        results.append(result)
    
    # Print report
    print("\n=== BINARY TEST VALIDATION REPORT ===\n")
    
    real_count = sum(1 for r in results if r["is_real"])
    fake_count = len(results) - real_count
    
    print(f"Total tests: {len(results)}")
    print(f"REAL binary tests: {real_count}")
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
            if "compression_ratio" in result["evidence"]:
                print(f"  Compression ratio: {result['evidence']['compression_ratio']:.2f}")
            if "throughput_mbps" in result["evidence"]:
                print(f"  Throughput: {result['evidence']['throughput_mbps']:.2f} MB/s")
    
    # Overall verdict
    print("\n=== OVERALL VERDICT ===")
    if real_count >= len(results) - 1:  # Allow 1 honeypot
        print("✅ Test suite contains REAL binary handling!")
        print(f"   {real_count} real tests demonstrate actual compression and streaming.")
    else:
        print("❌ Test suite appears to be mostly mocked.")
        print(f"   Only {real_count} out of {len(results)} tests are real.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_binary_tests.py <json_report_path>")
        sys.exit(1)
    
    validate_binary_tests(sys.argv[1])