#!/bin/bash
# Verify the rename was successful

set -e  # Exit on error

cd /home/graham/workspace/experiments/granger_hub

echo "=== Verification Script for granger_hub ==="
echo

# 1. Activate virtual environment
echo "1. Activating virtual environment..."
source .venv/bin/activate

# 2. Test Python import
echo "2. Testing Python import..."
python -c "import granger_hub; print('✅ granger_hub imported successfully!')" || echo "❌ Import failed"

# 3. Check CLI command
echo "3. Checking CLI command..."
which granger-cli && echo "✅ CLI command installed" || echo "❌ CLI command not found"

# 4. Run quick tests
echo "4. Running quick tests..."
pytest tests/test_schema_negotiation.py -v || echo "⚠️  Some tests failed (this might be expected)"

# 5. Check git status
echo "5. Checking git status..."
git status --short

# 6. Verify remote URL
echo "6. Verifying git remote..."
git remote -v

echo
echo "=== Verification Complete ==="
echo "If all checks passed, the rename was successful!"
echo "Note: You may still need to manually rename the GitHub repository."