# Task Naming Convention

Task files should be named following this pattern:
- Place in the `docs/tasks` directory
- Follow the format: `00N_task_name.md` 
  - Where N is the task number (001, 002, etc.)
  - task_name should be brief and descriptive

Examples:
- `001_claude_simple_question.md`
- `002_anthropic_streaming.md`
- `003_max_text_embeddings.md` Task List Template Guide v2 - Example-Driven Approach

This guide provides a focused, example-driven template for creating task lists that prevent code executors from getting lost in excessive documentation and theory.

## Core Principle: Show, Don't Tell

**OLD WAY**: "Research best practices for X and implement Y"
**NEW WAY**: "Here's working code for X. Make test Y pass using this pattern."

## Essential Requirements

### 1. Front-Load Working Examples
Every task MUST start with a complete, working code example that can be copied and modified. No research required - provide the answer upfront.

### 2. One Test Case Per Task
Focus on making ONE specific test from test_prompts.json pass. Don't bundle multiple test cases together.

### 3. Exact Commands and Expected Output
Provide the EXACT command to run and the EXACT expected output structure. No ambiguity.

## Concise Task Template

```markdown
# Task [NUMBER]: Make test [TEST_ID] pass

**Test ID**: [exact test_case_id from test_prompts.json]
**Model**: [exact model name]
**Goal**: Make this specific test pass

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
[Insert complete, working code that handles this test case type]
```

## Test Details

**Input from test_prompts.json**:
```json
[Paste exact test case from test_prompts.json]
```

**Run Command**:
```bash
python test_v4_essential_async.py -k [test_id]
```

**Expected Output Structure**:
```json
{
  "content": "[example content]",
  "model": "[model name]", 
  "usage": {...}
}
```

## Common Issues & Solutions

### Issue 1: [Most common error]
```python
# Solution:
[Paste working fix]
```

### Issue 2: [Second most common error]
```python
# Solution:
[Paste working fix]
```

## Validation Requirements

```python
# This test passes when:
assert response.get("content"), "Has content"
assert len(response["content"]) > 10, "Content is substantial"
# [Add specific validation for this test]
```
```

## Example: Focused Task for max_text_001

```markdown
# Task 1: Make test max_text_001_simple_question pass

**Test ID**: max_text_001_simple_question
**Model**: max/text-general
**Goal**: Get a simple text response from Claude proxy

## Working Code Example

```python
# COPY THIS WORKING PATTERN:
import asyncio
from litellm import acompletion

async def test_simple_question():
    response = await acompletion(
        model="max/text-general",
        messages=[{"role": "user", "content": "What is the primary function of a CPU in a computer?"}],
        api_base="http://localhost:8080",
        timeout=30
    )
    return response

# Run it:
result = asyncio.run(test_simple_question())
print(result.choices[0].message.content)
```

## Test Details

**Input from test_prompts.json**:
```json
{
    "test_case_id": "max_text_001_simple_question",
    "description": "Simplest call to Claude proxy with a question string.",
    "llm_config": {
        "model": "max/text-general",
        "question": "What is the primary function of a CPU in a computer?"
    }
}
```

**Run Command**:
```bash
python test_v4_essential_async.py -k max_text_001
```

**Expected Output Structure**:
```json
{
  "choices": [{
    "message": {
      "content": "The primary function of a CPU (Central Processing Unit) is..."
    }
  }],
  "model": "max/text-general"
}
```

## Common Issues & Solutions

### Issue 1: Timeout (Claude proxy takes 7-15 seconds)
```python
# Solution: Already handled in example with timeout=30
# If still timing out, implement polling:
from async_polling_manager import AsyncPollingManager
manager = AsyncPollingManager()
task_id = await manager.submit_task(request)
result = await manager.wait_for_result(task_id)
```

### Issue 2: Format mismatch (question vs messages)
```python
# Solution: Convert question to messages format
if "question" in llm_config:
    messages = [{"role": "user", "content": llm_config["question"]}]
else:
    messages = llm_config["messages"]
```

## Validation Requirements

```python
# This test passes when:
assert response.choices[0].message.content, "Has content"
assert "cpu" in response.choices[0].message.content.lower(), "Mentions CPU"
assert len(response.choices[0].message.content) > 20, "Substantial response"
```
```

## Key Differences from v1

1. **No Research Section** - Provide working code immediately
2. **Single Test Focus** - One test case per task, not groups
3. **Exact Examples** - Real JSON from test_prompts.json
4. **Pre-Solved Problems** - Common issues already have solutions
5. **Minimal Text** - Code speaks louder than explanations
6. **Clear Success Criteria** - Exact assertions that must pass

## Anti-Patterns to Avoid

❌ "Research LiteLLM documentation for completion patterns"
❌ "Implement a flexible routing system for multiple models"
❌ "Create comprehensive error handling for all edge cases"
❌ Long explanations of why something works
❌ Multiple test cases in one task
❌ Vague success criteria

## Good Patterns to Follow

✅ "Copy this working code"
✅ "Make test X pass"
✅ "If you see error Y, use solution Z"
✅ Exact test data from test_prompts.json
✅ One specific test case
✅ Clear pass/fail assertions

## Creating Effective Tasks

1. **Start with the test case** - Pick one from test_prompts.json
2. **Find or write working code** - Test it yourself first
3. **Document the exact command** - No ambiguity
4. **List common errors with fixes** - Pre-solve problems
5. **Keep it under 100 lines** - Focus is key

Remember: The code executor performs best when given concrete examples and clear targets, not abstract concepts and research tasks.

## Test Validation Tasks with Allure Reporting

### Critical Test Validation Template

For tasks requiring comprehensive test validation with zero tolerance for failures, use this template:

```markdown
# Task [NUMBER]: Critical Test Validation with Iteration

**Command**: sparta-cli test-iterate
**Requirement**: 100% test pass rate - NO EXCEPTIONS
**Reports**: Allure dashboard + JSON analysis

## Execution Command

```bash
# Run with maximum critical analysis
sparta-cli test-iterate --critical --attempts 3 --allure --project sparta
```

## Success Criteria (ALL MUST PASS)

- [ ] 100% test pass rate (no failures allowed)
- [ ] 0 skipped tests (or documented valid reasons)
- [ ] 0 mocked core functionality (per CLAUDE.md)
- [ ] Allure report shows all green status
- [ ] No critical issues in iteration summary

## Expected Output Structure

```json
{
  "project": "sparta",
  "final_status": {
    "all_passed": true,
    "requires_action": false,
    "failure_count": 0,
    "skipped_count": 0,
    "passed_count": 25,
    "success_rate": 100.0
  },
  "total_iterations": 1
}
```

## Common Issues & Auto-Fixes

### Issue 1: Import Errors
**Auto-Fix**: Command runs `uv sync` automatically
**Manual Check**: Verify pyproject.toml dependencies

### Issue 2: Missing Directories
**Auto-Fix**: Creates docs/reports/, allure-results/ automatically
**Manual Check**: Verify file permissions

### Issue 3: Skipped Tests
**Investigation Required**: 
```bash
# Find skipped tests
pytest -v | grep SKIPPED

# Check skip conditions in test files
grep -r "@pytest.mark.skip" tests/
```

## Validation Process

1. **Initial Run**: Execute test-iterate command
2. **Analyze Failures**: Review actionable items from JSON report
3. **Apply Fixes**: Let auto-fix handle common issues
4. **Re-iterate**: Command automatically retries up to 3 times
5. **Final Verification**: Check Allure dashboard

## Report Locations

- **Allure HTML**: ./allure-report/index.html
- **JSON Summary**: docs/reports/test_iterate_summary_*.json
- **Test Results**: test-results-*.json
- **Multi-Project**: Run `sparta-cli allure-dashboard`
```

### Example: Complete Test Validation Task

```markdown
# Task 5: Achieve 100% Test Pass Rate for SPARTA

**Command**: sparta-cli test-iterate
**Model**: N/A (test validation task)
**Goal**: Fix all failing tests and achieve 100% pass rate

## Initial Test Run

```bash
# First, check current status
sparta-cli test-iterate --critical --attempts 1 --project sparta
```

## Expected Iterations

### Iteration 1: Identify Failures
- Import errors → auto-fixed with `uv sync`
- Missing directories → auto-created
- Review remaining failures in JSON report

### Iteration 2: Fix Remaining Issues
- Check error patterns in actionable items
- Apply suggested fixes from AgentReportAdapter
- Re-run automatically

### Iteration 3: Final Validation
- All tests should pass
- No skipped tests without documentation
- Success rate: 100%

## Verification Commands

```bash
# View Allure report
allure open allure-report

# Check iteration summary
cat docs/reports/test_iterate_summary_*.json | jq '.final_status'

# Launch multi-project dashboard
python scripts/allure_dashboard.py
```

## Success Output

```
🔍 Starting critical test analysis and iteration...
Project: sparta
Critical mode: ON

━━━ Iteration 1 of 3 ━━━

Test Results:
  • Total tests: 25
  • Passed: 25
  • Failed: 0
  • Skipped: 0
  • Success rate: 100.0%

✅ All tests passed with no skips!

📊 Generating final reports...
  • Iteration summary: docs/reports/test_iterate_summary_20250527_120000.json
  • Allure report: ./allure-report/index.html

✅ SUCCESS: All tests passing!
```
```

## Integration with CI/CD

For automated validation in pipelines:

```yaml
# Example GitHub Actions
- name: Run Critical Test Validation
  run: |
    sparta-cli test-iterate --critical --attempts 5 --allure
    
- name: Upload Allure Report
  uses: actions/upload-artifact@v3
  with:
    name: allure-report
    path: allure-report/
    
- name: Check Test Status
  run: |
    # Fail pipeline if tests don't pass
    status=$(cat docs/reports/test_iterate_summary_*.json | jq -r '.final_status.all_passed')
    if [ "$status" != "true" ]; then
      echo "Tests failed!"
      exit 1
    fi
```

## Best Practices for Test Tasks

1. **Always Use Critical Mode**: Default behavior should be zero tolerance
2. **Document Skip Reasons**: If tests must be skipped, document why in the test file
3. **Review Auto-Fixes**: Verify that automated fixes are appropriate
4. **Check Flaky Tests**: Use Allure history to identify intermittent failures
5. **Multi-Project Validation**: Use dashboard for cross-project health checks

## Anti-Patterns to Avoid

❌ Accepting any test failures as "expected"
❌ Skipping tests without documentation
❌ Mocking core functionality
❌ Ignoring iteration summaries
❌ Manual fixes without documenting

## Good Patterns to Follow

✅ 100% pass rate as non-negotiable
✅ Automated iteration with fixes
✅ Clear documentation of any exceptions
✅ Using Allure for visual verification
✅ Saving iteration summaries for history
