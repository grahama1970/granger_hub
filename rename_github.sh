#!/bin/bash
# Rename GitHub repository

cd /home/graham/workspace/experiments/granger_hub

# Check authentication
gh auth status

# Rename the repository
gh repo rename granger_hub

# Verify the rename
echo "Verifying remote URL..."
git remote -v

# Open in browser to confirm
gh repo view --web