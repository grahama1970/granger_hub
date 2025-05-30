#!/usr/bin/env python3
"""Combine multiple pytest JSON reports into one."""

import json
import sys
from pathlib import Path

def combine_reports(report_files):
    """Combine multiple pytest JSON reports."""
    combined = {
        "summary": {"total": 0, "passed": 0, "failed": 0},
        "tests": [],
        "created": None,
        "duration": 0,
        "environment": {}
    }
    
    for report_file in report_files:
        with open(report_file) as f:
            data = json.load(f)
            
        # Update summary
        summary = data.get("summary", {})
        combined["summary"]["total"] += summary.get("total", 0)
        combined["summary"]["passed"] += summary.get("passed", 0)  
        combined["summary"]["failed"] += summary.get("failed", 0)
        
        # Add tests
        combined["tests"].extend(data.get("tests", []))
        
        # Update metadata
        combined["duration"] += data.get("duration", 0)
        if not combined["created"]:
            combined["created"] = data.get("created")
        if not combined["environment"]:
            combined["environment"] = data.get("environment", {})
    
    return combined

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", help="JSON report files")
    parser.add_argument("-o", "--output", default="combined_report.json")
    args = parser.parse_args()
    
    combined = combine_reports(args.files)
    
    with open(args.output, "w") as f:
        json.dump(combined, f, indent=2)
    
    print(f"Combined {len(args.files)} reports into {args.output}")
    print(f"Total tests: {combined['summary']['total']}")
    print(f"Passed: {combined['summary']['passed']}")
    print(f"Failed: {combined['summary']['failed']}")