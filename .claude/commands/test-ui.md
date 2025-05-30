# Test website UI with Claude's intelligence

Let Claude intelligently test a website by opening a browser, interacting with elements, taking screenshots, and providing detailed analysis.

## Usage

```bash
cmc-cli test-browser <URL> [OPTIONS]
```

## Options

- `--instruction/-i`: Test instruction for Claude (default: "Test this website thoroughly")
- `--scenario/-s`: Path to test scenario file (JSON)
- `--output/-o`: Output directory for results (default: ./test_results)
- `--headless/--headed`: Run browser in headless mode (default: headless)
- `--focus/-f`: Focus areas for testing (can be used multiple times)
- `--quick/-q`: Run quick test (page structure and accessibility only)

## Examples

```bash
# Basic test
/project:test-ui https://example.com

# Test with specific instruction
/project:test-ui https://example.com --instruction "Test the login flow and verify all form validations"

# Test with focus areas
/project:test-ui https://example.com --focus "navigation" --focus "forms" --focus "accessibility"

# Quick test
/project:test-ui https://example.com --quick

# Test with scenario file
/project:test-ui https://example.com --scenario ./test_scenarios/login_test.json

# Run in headed mode to see the browser
/project:test-ui https://example.com --headed
```

## What Claude Tests

1. **Page Structure**: Analyzes headings, forms, links, images, and buttons
2. **Interactive Elements**: Clicks buttons and links to verify they work
3. **Accessibility**: Checks for alt text, form labels, and other a11y concerns
4. **Responsive Design**: Tests how the page looks on mobile, tablet, and desktop
5. **User Experience**: Provides recommendations for improvements

## Output

Claude generates a comprehensive HTML report with:
- Screenshots of each test step
- AI-powered analysis of what happened
- Pass/fail status for each test
- Overall recommendations
- Detailed test results with before/after screenshots

---
*Claude's intelligent browser testing*
