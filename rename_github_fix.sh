#!/bin/bash
# Rename GitHub repository with proper authentication

cd /home/graham/workspace/experiments/granger_hub

# Use keyring authentication
export GH_TOKEN=""

# Rename the repository with --yes flag
gh repo rename granger_hub --yes

# If rename succeeded, update the remote URL
if [ $? -eq 0 ]; then
    echo "Repository renamed successfully!"
    # Update local remote URL
    git remote set-url origin git@github.com:grahama1970/granger_hub.git
    echo "Updated remote URL to:"
    git remote -v
else
    echo "Failed to rename repository. You may need to:"
    echo "1. Login with: gh auth login"
    echo "2. Or rename manually on GitHub and then run:"
    echo "   git remote set-url origin git@github.com:grahama1970/granger_hub.git"
fi