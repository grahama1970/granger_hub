#!/bin/bash
# Reinstall granger_hub with UV

cd /home/graham/workspace/experiments/granger_hub

# Clear UV cache
uv cache clean

# Create new virtual environment
uv venv

# Activate it
source .venv/bin/activate

# Install in editable mode
uv pip install -e .

# Test the import
python -c "import granger_hub; print('✅ granger_hub imported successfully!')"