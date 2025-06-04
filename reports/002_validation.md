# Conversation Test Validation Report

Generated: 2025-06-01T18:24:30.538113

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 4 |
| REAL Tests | 4 (100.0%) |
| FAKE Tests | 0 |
| Average Confidence | 88.8% |
| Honeypots | 1/1 correct |

## Test Results

| Test | Verdict | Confidence | Why | Evidence |
|------|---------|------------|-----|----------|
| test_create_conversation | **REAL** | 95.0% | Found 5 conversation indicators | conversation_id: 66c5f243-c8e2-4256-90af-e4ee26684af2; turn_number: 0; history_maintained: found; co... |
| test_message_routing | **REAL** | 95.0% | Found 4 conversation indicators | conversation_id: 8d9f260f-5f68-4ade-a692-b6421bf78408; turn_number: 1; total_duration: 0.25652909278... |
| test_state_persistence | **REAL** | 95.0% | Found 3 conversation indicators | conversation_id: cae8a5a3-6b23-4267-8ec2-0985afcc8c2c; total_duration: 0.12964081764221191; Test pro... |
| test_impossible_routing | **REAL** | 70.0% | Honeypot behaved as expected | Test outcome matches honeypot design; Cross-examination: Only 0/4 critical evidence pieces found |

## Suspicious Patterns Detected

- ⚠️ ALL non-honeypot tests passed - could be overconfident!
- ⚠️ 3 tests have ≥95% confidence - check for overconfidence!

## Recommendations

Strengthen evidence in tests with weak validation:
  - tests/test_conversation_manager.py::test_impossible_routing: Add more conversation indicators
