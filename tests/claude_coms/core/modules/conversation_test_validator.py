"""
Conversation Test Validator using Claude Test Reporter.

Purpose: Critically and skeptically analyze test results to determine if they
represent REAL multi-turn conversations or FAKE single-shot interactions.

This module extends claude-test-reporter with conversation-specific validation.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from claude_test_reporter import UniversalReportGenerator, TestReporter
except ImportError:
    # Fallback if claude_test_reporter not available
    UniversalReportGenerator = None
    TestReporter = None


class ConversationTestValidator:
    """
    Validates conversation tests with skeptical analysis.
    
    Uses claude-test-reporter for report generation while adding
    conversation-specific validation logic.
    """
    
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
        
        # Configure report generator for conversation tests
        try:
            self.report_generator = UniversalReportGenerator(
                title="Multi-Turn Conversation Test Results",
                theme_color="#8B5CF6",  # Purple for conversations
                logo="💬",
                custom_css="""
                .verdict-real { color: #10B981; font-weight: bold; }
                .verdict-fake { color: #EF4444; font-weight: bold; }
                .confidence-high { background-color: #FEE2E2; }
                .evidence { font-family: monospace; font-size: 0.9em; }
                """
            )
        except TypeError:
            # Fallback without custom_css if not supported
            self.report_generator = UniversalReportGenerator(
                title="Multi-Turn Conversation Test Results",
                theme_color="#8B5CF6",  # Purple for conversations
                logo="💬"
            )
    
    def validate_pytest_results(self, json_report_path: str) -> Dict[str, Any]:
        """
        Validate pytest JSON report for conversation authenticity.
        
        Args:
            json_report_path: Path to pytest JSON report
            
        Returns:
            Validation results with verdict, confidence, and evidence
        """
        # Use PytestReportRunner to parse the JSON
        runner = PytestReportRunner()
        test_results = runner.parse_json_report(json_report_path)
        
        # Enhance results with conversation validation
        validated_results = []
        
        for result in test_results:
            validated = self._validate_single_test(result)
            validated_results.append(validated)
        
        # Generate skeptical report
        report_data = {
            "tests": validated_results,
            "summary": self._generate_summary(validated_results),
            "suspicious_patterns": self._detect_suspicious_patterns(validated_results),
            "recommendations": self._generate_recommendations(validated_results)
        }
        
        return report_data
    
    def _validate_single_test(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single test for conversation authenticity."""
        # Start with original test data
        validated = test_result.copy()
        
        # Check if it's a honeypot
        test_name = test_result.get("test", "")
        if self._is_honeypot(test_name):
            validated.update(self._validate_honeypot(test_result))
        else:
            validated.update(self._validate_conversation_test(test_result))
        
        # Add confidence assessment
        validated = self._assess_confidence(validated)
        
        return validated
    
    def _is_honeypot(self, test_name: str) -> bool:
        """Check if test is a honeypot."""
        return any(pattern in test_name.lower() for pattern in self.honeypot_patterns)
    
    def _validate_honeypot(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate honeypot test - should fail."""
        if test_result.get("status") == "PASS":
            return {
                "verdict": "FAKE",
                "confidence": 100.0,
                "why": "Honeypot test passed when it should fail",
                "evidence": ["Test designed to fail but passed"]
            }
        else:
            return {
                "verdict": "REAL", 
                "confidence": 100.0,
                "why": "Honeypot correctly failed",
                "evidence": ["Test failed as expected"]
            }
    
    def _validate_conversation_test(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate regular test for conversation authenticity."""
        duration = test_result.get("duration", 0.0)
        output = test_result.get("output", "")
        
        # Check duration
        if duration < self.max_instant_duration:
            return {
                "verdict": "FAKE",
                "confidence": 95.0,
                "why": f"Duration {duration}s is impossibly fast for multi-turn conversation",
                "evidence": [f"Duration: {duration}s (min expected: {self.min_conversation_duration}s)"]
            }
        
        # Look for conversation evidence
        evidence = []
        conversation_score = 0
        
        # Check for conversation patterns
        patterns = {
            "conversation_id": r'conversation[_\s]*id["\s:]+([a-zA-Z0-9-]+)',
            "turn_number": r'turn[_\s]+(?:number|num)?["\s:]+(\d+)',
            "message_count": r'(\d+)\s+messages?\s+exchanged',
            "context_reference": r'(based on|following up|in response to|referring to)',
            "history_mention": r'(conversation history|previous message|earlier)',
        }
        
        for pattern_name, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                conversation_score += 20
                evidence.append(f"{pattern_name}: {match.group(1) if match.lastindex else 'found'}")
        
        # Determine verdict based on score
        if conversation_score >= 60:
            verdict = "REAL"
            confidence = min(70 + conversation_score / 2, 95)
            why = f"Found {conversation_score/20:.0f} conversation indicators"
        else:
            verdict = "FAKE"
            confidence = 85.0
            why = f"Only found {conversation_score/20:.0f} conversation indicators"
            evidence.append("Missing critical conversation context")
        
        return {
            "verdict": verdict,
            "confidence": confidence,
            "why": why,
            "evidence": evidence
        }
    
    def _assess_confidence(self, validated_test: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-examine high confidence claims."""
        if validated_test.get("confidence", 0) >= 90 and validated_test.get("verdict") == "REAL":
            # Look for specific evidence
            evidence = validated_test.get("evidence", [])
            
            critical_evidence = [
                "conversation_id",
                "turn_number", 
                "message_count"
            ]
            
            found_critical = sum(1 for e in evidence for c in critical_evidence if c in str(e))
            
            if found_critical < 2:
                # Reduce confidence due to weak evidence
                validated_test["confidence"] *= 0.8
                validated_test["evidence"].append(
                    f"Cross-examination: Only {found_critical}/3 critical evidence pieces found"
                )
                
                if validated_test["confidence"] < 90:
                    validated_test["verdict"] = "FAKE"
                    validated_test["why"] += " (failed cross-examination)"
        
        return validated_test
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics."""
        total = len(results)
        real_count = sum(1 for r in results if r.get("verdict") == "REAL")
        fake_count = sum(1 for r in results if r.get("verdict") == "FAKE")
        avg_confidence = sum(r.get("confidence", 0) for r in results) / total if total > 0 else 0
        
        return {
            "total_tests": total,
            "real_tests": real_count,
            "fake_tests": fake_count,
            "real_percentage": (real_count / total * 100) if total > 0 else 0,
            "average_confidence": avg_confidence
        }
    
    def _detect_suspicious_patterns(self, results: List[Dict[str, Any]]) -> List[str]:
        """Detect suspicious patterns in test results."""
        patterns = []
        
        # All tests passing
        non_honeypot = [r for r in results if not self._is_honeypot(r.get("test", ""))]
        if non_honeypot and all(r.get("status") == "PASS" for r in non_honeypot):
            patterns.append("⚠️ ALL non-honeypot tests passed - suspicious!")
        
        # Uniform durations
        durations = [r.get("duration", 0) for r in results]
        if durations and max(durations) - min(durations) < 0.1:
            patterns.append("⚠️ Test durations are suspiciously uniform!")
        
        # High confidence
        high_conf = [r for r in results if r.get("confidence", 0) >= 95]
        if len(high_conf) > len(results) * 0.5:
            patterns.append(f"⚠️ {len(high_conf)} tests have ≥95% confidence - unrealistic!")
        
        return patterns
    
    def _generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []
        
        fake_tests = [r for r in results if r.get("verdict") == "FAKE"]
        if fake_tests:
            recommendations.append("Fix FAKE tests by implementing real conversation logic:")
            for test in fake_tests[:3]:  # Show first 3
                recommendations.append(f"  - {test['test']}: {test['why']}")
        
        avg_confidence = self._generate_summary(results)["average_confidence"]
        if avg_confidence > 95:
            recommendations.append("Results show unrealistic confidence - add more complex test cases")
        
        return recommendations
    
    def generate_html_report(self, validation_data: Dict[str, Any], output_path: str) -> str:
        """Generate HTML report using claude-test-reporter."""
        # Transform data for report generator
        report_tests = []
        
        for test in validation_data["tests"]:
            # Add verdict and confidence to metadata
            test_entry = {
                "test": test["test"],
                "status": test["status"],
                "duration": test["duration"],
                "metadata": {
                    "verdict": test.get("verdict", "UNKNOWN"),
                    "confidence": f"{test.get('confidence', 0):.1f}%",
                    "why": test.get("why", ""),
                    "evidence": test.get("evidence", [])
                }
            }
            report_tests.append(test_entry)
        
        # Add summary section
        summary_html = self._generate_summary_html(validation_data)
        
        # Generate report with custom sections
        return self.report_generator.generate(
            report_tests,
            output_path,
            custom_sections={
                "summary": summary_html,
                "suspicious_patterns": validation_data.get("suspicious_patterns", []),
                "recommendations": validation_data.get("recommendations", [])
            }
        )
    
    def _generate_summary_html(self, validation_data: Dict[str, Any]) -> str:
        """Generate HTML for summary section."""
        summary = validation_data["summary"]
        
        return f"""
        <div class="summary-stats">
            <h3>Validation Summary</h3>
            <ul>
                <li>Total Tests: {summary['total_tests']}</li>
                <li class="verdict-real">REAL Tests: {summary['real_tests']} ({summary['real_percentage']:.1f}%)</li>
                <li class="verdict-fake">FAKE Tests: {summary['fake_tests']}</li>
                <li>Average Confidence: {summary['average_confidence']:.1f}%</li>
            </ul>
        </div>
        """


# CLI integration
def main():
    """Command line interface for conversation test validation."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m granger_hub.conversation_test_validator <pytest_json_report>")
        sys.exit(1)
    
    json_report = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "conversation_test_report.html"
    
    validator = ConversationTestValidator()
    validation_data = validator.validate_pytest_results(json_report)
    
    # Generate HTML report
    report_path = validator.generate_html_report(validation_data, output_path)
    print(f"Validation report generated: {report_path}")
    
    # Print summary to console
    summary = validation_data["summary"]
    print(f"\nValidation Summary:")
    print(f"  REAL tests: {summary['real_tests']}/{summary['total_tests']}")
    print(f"  Average confidence: {summary['average_confidence']:.1f}%")
    
    if validation_data["suspicious_patterns"]:
        print("\nSuspicious Patterns:")
        for pattern in validation_data["suspicious_patterns"]:
            print(f"  {pattern}")


if __name__ == "__main__":
    main()