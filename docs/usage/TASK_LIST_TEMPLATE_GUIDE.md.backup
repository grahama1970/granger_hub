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
