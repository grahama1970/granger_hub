"""
Test Result Analyzer for Multi-Turn Conversation Tests.

Purpose: Critically and skeptically analyze test results to determine if they
represent REAL multi-turn conversations or FAKE single-shot interactions.

This module implements the validation logic described in the task list,
including confidence assessment and evidence examination.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import subprocess
import re


@dataclass
class TestResult:
    """Represents a single test result with analysis."""
    test_id: str
    description: str
    duration: float
    passed: bool
    output: str
    verdict: str = "PENDING"  # REAL or FAKE
    confidence: float = 0.0
    evidence: List[str] = None
    why: str = ""
    fix_applied: str = ""
    
    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []


class ConversationTestAnalyzer:
    """Analyzes test results to determine if they demonstrate real conversations."""
    
    def __init__(self):
        self.min_conversation_duration = 0.1  # seconds
        self.max_instant_duration = 0.05  # anything faster is suspicious
        self.honeypot_patterns = [
            "test_impossible",
            "test_instant",
            "test_telepathic",
            "test_perfect",
            "test_infinite",
            "HONEYPOT"
        ]
    
    def analyze_test_results(self, test_output_file: str) -> Dict[str, TestResult]:
        """Analyze pytest JSON output to determine test authenticity."""
        results = {}
        
        # Parse test output
        with open(test_output_file, 'r') as f:
            test_data = json.load(f)
        
        # Analyze each test
        for test in test_data.get('tests', []):
            result = self._analyze_single_test(test)
            results[result.test_id] = result
        
        return results
    
    def _analyze_single_test(self, test_data: Dict[str, Any]) -> TestResult:
        """Analyze a single test for authenticity."""
        test_id = test_data.get('nodeid', 'unknown')
        duration = test_data.get('duration', 0.0)
        outcome = test_data.get('outcome', 'failed')
        
        result = TestResult(
            test_id=test_id,
            description=test_data.get('keywords', []),
            duration=duration,
            passed=(outcome == 'passed'),
            output=test_data.get('call', {}).get('stdout', '')
        )
        
        # Check if it's a honeypot
        if self._is_honeypot(test_id):
            result = self._analyze_honeypot(result)
        else:
            result = self._analyze_regular_test(result)
        
        return result
    
    def _is_honeypot(self, test_id: str) -> bool:
        """Check if test is a honeypot."""
        return any(pattern in test_id for pattern in self.honeypot_patterns)
    
    def _analyze_honeypot(self, result: TestResult) -> TestResult:
        """Analyze honeypot test - should fail."""
        if result.passed:
            result.verdict = "FAKE"
            result.confidence = 100.0
            result.why = "Honeypot test passed when it should fail"
            result.evidence.append("Test designed to fail but passed")
        else:
            result.verdict = "REAL"
            result.confidence = 100.0
            result.why = "Honeypot correctly failed"
            result.evidence.append("Test failed as expected")
        
        return result
    
    def _analyze_regular_test(self, result: TestResult) -> TestResult:
        """Analyze regular test for conversation authenticity."""
        # Check duration
        if result.duration < self.max_instant_duration:
            result.verdict = "FAKE"
            result.confidence = 95.0
            result.why = f"Duration {result.duration}s is impossibly fast"
            result.evidence.append(f"Duration: {result.duration}s (min expected: {self.min_conversation_duration}s)")
            return result
        
        # Look for conversation evidence in output
        conversation_indicators = [
            "conversation_id",
            "turn_number",
            "context",
            "history",
            "previous",
            "response to",
            "following up",
            "based on earlier"
        ]
        
        found_indicators = []
        output_lower = result.output.lower()
        
        for indicator in conversation_indicators:
            if indicator in output_lower:
                found_indicators.append(indicator)
        
        # Calculate confidence based on evidence
        if len(found_indicators) >= 3:
            result.verdict = "REAL"
            result.confidence = 90.0 + min(len(found_indicators) * 2, 10)
            result.why = f"Found {len(found_indicators)} conversation indicators"
            result.evidence.extend([f"Found: {ind}" for ind in found_indicators])
        else:
            result.verdict = "FAKE"
            result.confidence = 80.0
            result.why = f"Only found {len(found_indicators)} conversation indicators"
            result.evidence.append(f"Missing conversation context indicators")
        
        # Extract specific evidence from output
        self._extract_conversation_evidence(result)
        
        return result
    
    def _extract_conversation_evidence(self, result: TestResult):
        """Extract specific conversation evidence from test output."""
        # Look for conversation IDs
        conv_id_match = re.search(r'conversation_id["\s:]+([a-zA-Z0-9-]+)', result.output)
        if conv_id_match:
            result.evidence.append(f"Conversation ID: {conv_id_match.group(1)}")
        
        # Look for turn numbers
        turn_match = re.search(r'turn[_\s]+number["\s:]+(\d+)', result.output)
        if turn_match:
            result.evidence.append(f"Turn number: {turn_match.group(1)}")
        
        # Look for message counts
        msg_count_match = re.search(r'(\d+)\s+messages?\s+exchanged', result.output)
        if msg_count_match:
            result.evidence.append(f"Messages exchanged: {msg_count_match.group(1)}")
    
    def generate_skeptical_report(self, results: Dict[str, TestResult]) -> str:
        """Generate a skeptical analysis report."""
        report = []
        report.append("# Skeptical Test Analysis Report")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # Summary statistics
        total_tests = len(results)
        real_tests = sum(1 for r in results.values() if r.verdict == "REAL")
        fake_tests = sum(1 for r in results.values() if r.verdict == "FAKE")
        avg_confidence = sum(r.confidence for r in results.values()) / total_tests if total_tests > 0 else 0
        
        report.append("## Summary")
        report.append(f"- Total Tests: {total_tests}")
        report.append(f"- REAL Tests: {real_tests} ({real_tests/total_tests*100:.1f}%)")
        report.append(f"- FAKE Tests: {fake_tests} ({fake_tests/total_tests*100:.1f}%)")
        report.append(f"- Average Confidence: {avg_confidence:.1f}%")
        report.append("")
        
        # Suspicious patterns
        report.append("## Suspicious Patterns")
        
        # Check for all tests passing
        if all(r.passed for r in results.values() if not self._is_honeypot(r.test_id)):
            report.append("⚠️ ALL non-honeypot tests passed - suspicious!")
        
        # Check for uniform durations
        durations = [r.duration for r in results.values()]
        if durations and max(durations) - min(durations) < 0.1:
            report.append("⚠️ Test durations are suspiciously uniform!")
        
        # Check for high confidence
        high_confidence = [r for r in results.values() if r.confidence >= 95]
        if len(high_confidence) > total_tests * 0.5:
            report.append(f"⚠️ {len(high_confidence)} tests have ≥95% confidence - unrealistic!")
        
        report.append("")
        
        # Detailed results
        report.append("## Detailed Test Analysis")
        for test_id, result in results.items():
            report.append(f"\n### {test_id}")
            report.append(f"- **Verdict**: {result.verdict}")
            report.append(f"- **Confidence**: {result.confidence}%")
            report.append(f"- **Duration**: {result.duration}s")
            report.append(f"- **Why**: {result.why}")
            report.append(f"- **Evidence**:")
            for evidence in result.evidence:
                report.append(f"  - {evidence}")
        
        # Recommendations
        report.append("\n## Recommendations")
        if fake_tests > 0:
            report.append("1. Fix FAKE tests by implementing real conversation logic:")
            for test_id, result in results.items():
                if result.verdict == "FAKE":
                    report.append(f"   - {test_id}: {result.why}")
        
        if avg_confidence > 95:
            report.append("2. Results show unrealistic confidence - add more complex test cases")
        
        return "\n".join(report)
    
    def cross_examine_claims(self, result: TestResult) -> TestResult:
        """Cross-examine high confidence claims with specific questions."""
        if result.confidence >= 90 and result.verdict == "REAL":
            questions = [
                "What was the exact conversation_id used?",
                "How many messages were in the conversation history?",
                "What was the context from the previous turn?",
                "How long did message processing take?",
                "What module initiated the conversation?",
                "What was the final conversation state?"
            ]
            
            # In a real implementation, we'd query the test for these answers
            # For now, we'll look for them in the output
            answered = 0
            for question in questions:
                # Simple heuristic - look for related content
                if any(word in result.output.lower() for word in question.lower().split()):
                    answered += 1
            
            if answered < 3:
                result.confidence *= 0.7  # Reduce confidence
                result.evidence.append(f"Cross-examination: Only answered {answered}/6 questions")
                if result.confidence < 90:
                    result.verdict = "FAKE"
                    result.why += " (failed cross-examination)"
        
        return result


# Example usage and validation
if __name__ == "__main__":
    # This would be run after pytest generates JSON output
    analyzer = ConversationTestAnalyzer()
    
    # Example test data (in real use, this comes from pytest)
    sample_test_data = {
        "tests": [
            {
                "nodeid": "test_conversation::test_multi_turn",
                "duration": 1.5,
                "outcome": "passed",
                "call": {
                    "stdout": "Starting conversation_id: abc-123\nTurn 1: Hello\nTurn 2: Response based on earlier greeting\nTurn 3: Following up on previous context\n3 messages exchanged"
                }
            },
            {
                "nodeid": "test_conversation::test_instant_response",
                "duration": 0.001,
                "outcome": "passed",
                "call": {"stdout": "Response sent"}
            },
            {
                "nodeid": "test_conversation::test_impossible_telepathy",
                "duration": 0.5,
                "outcome": "passed",  # This should fail!
                "call": {"stdout": "Modules communicated without messages"}
            }
        ]
    }
    
    # Save sample data
    with open("/tmp/sample_test.json", "w") as f:
        json.dump(sample_test_data, f)
    
    # Analyze
    results = analyzer.analyze_test_results("/tmp/sample_test.json")
    
    # Cross-examine high confidence claims
    for test_id, result in results.items():
        results[test_id] = analyzer.cross_examine_claims(result)
    
    # Generate report
    report = analyzer.generate_skeptical_report(results)
    print(report)
    
    # Validate our analyzer is working
    assert results["test_conversation::test_multi_turn"].verdict == "REAL"
    assert results["test_conversation::test_instant_response"].verdict == "FAKE"
    assert results["test_conversation::test_impossible_telepathy"].verdict == "FAKE"  # Honeypot
    
    print("\n✅ Test analyzer validation passed!")