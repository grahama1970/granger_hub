# Conversation Test Validation Report

Generated: 2025-06-02T06:47:47.949490

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 3 |
| REAL Tests | 3 (100.0%) |
| FAKE Tests | 0 |
| Average Confidence | 86.7% |
| Honeypots | 1/1 correct |

## Test Results

| Test | Verdict | Confidence | Why | Evidence |
|------|---------|------------|-----|----------|
| test_initiate_conversation | **REAL** | 95.0% | Found 4 conversation indicators | conversation_id: e0ddc184-c236-48d3-bd48-59660e018f83; turn_number: 2; total_duration: 0.05072927474... |
| test_multi_turn_exchange | **REAL** | 95.0% | Found 4 conversation indicators | conversation_id: 05918e05-2799-4dd0-ab4d-0041859e5d68; turn_number: 6; total_duration: 0.60807561874... |
| test_no_message_exchange | **REAL** | 70.0% | Honeypot behaved as expected | Test outcome matches honeypot design; Cross-examination: Only 0/4 critical evidence pieces found |

## Suspicious Patterns Detected

- ⚠️ ALL non-honeypot tests passed - could be overconfident!
- ⚠️ 2 tests have ≥95% confidence - check for overconfidence!

## Recommendations

Strengthen evidence in tests with weak validation:
  - tests/test_conversation_protocol.py::test_no_message_exchange: Add more conversation indicators
