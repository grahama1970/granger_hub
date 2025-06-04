#!/bin/bash
# Setup cron jobs for self-improvement system

echo "Setting up Claude Module Communicator Self-Improvement Cron Jobs"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Python executable path (adjust if needed)
PYTHON_PATH="/usr/bin/python3"

# Create cron entries
CRON_ENTRIES="
# Claude Module Communicator Self-Improvement System

# Daily discovery run at 2 AM - find new patterns
0 2 * * * cd $PROJECT_ROOT && $PYTHON_PATH scripts/run_discovery.py >> logs/discovery.log 2>&1

# Daily improvement proposals at 3 AM - generate tasks
0 3 * * * cd $PROJECT_ROOT && $PYTHON_PATH scripts/generate_improvements.py >> logs/improvements.log 2>&1

# Quick optimization check every 6 hours
0 */6 * * * cd $PROJECT_ROOT && $PYTHON_PATH scripts/run_discovery.py --categories optimization --max-scenarios 3 >> logs/discovery_quick.log 2>&1

# Weekly performance analysis on Sundays at 2 AM
0 2 * * 0 cd $PROJECT_ROOT && $PYTHON_PATH scripts/generate_improvements.py --mode performance >> logs/performance.log 2>&1

# Monthly deep analysis on 1st of month at 1 AM
0 1 1 * * cd $PROJECT_ROOT && $PYTHON_PATH scripts/run_discovery.py --force-refresh --max-scenarios 20 >> logs/discovery_deep.log 2>&1
"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

# Function to add cron jobs
add_cron_jobs() {
    # Save current crontab
    crontab -l > /tmp/current_cron 2>/dev/null || echo "" > /tmp/current_cron
    
    # Check if our jobs are already installed
    if grep -q "Claude Module Communicator Self-Improvement System" /tmp/current_cron; then
        echo "❌ Cron jobs already installed. Remove them first with --remove flag."
        return 1
    fi
    
    # Add new entries
    echo "$CRON_ENTRIES" >> /tmp/current_cron
    
    # Install new crontab
    crontab /tmp/current_cron
    
    # Clean up
    rm /tmp/current_cron
    
    echo "✅ Cron jobs installed successfully!"
    echo ""
    echo "Scheduled jobs:"
    echo "- Daily discovery: 2 AM"
    echo "- Daily improvements: 3 AM" 
    echo "- Quick optimization: Every 6 hours"
    echo "- Weekly performance: Sundays 2 AM"
    echo "- Monthly deep analysis: 1st of month 1 AM"
    echo ""
    echo "Logs will be saved to: $PROJECT_ROOT/logs/"
}

# Function to remove cron jobs
remove_cron_jobs() {
    # Save current crontab
    crontab -l > /tmp/current_cron 2>/dev/null || echo "" > /tmp/current_cron
    
    # Remove our section
    sed -i '/# Claude Module Communicator Self-Improvement System/,/^$/d' /tmp/current_cron
    
    # Install modified crontab
    crontab /tmp/current_cron
    
    # Clean up
    rm /tmp/current_cron
    
    echo "✅ Cron jobs removed successfully!"
}

# Function to show status
show_status() {
    echo "Current Claude Module Communicator cron jobs:"
    echo ""
    crontab -l 2>/dev/null | grep -A 20 "Claude Module Communicator Self-Improvement System" || echo "No jobs installed."
}

# Parse command line arguments
case "$1" in
    --remove)
        remove_cron_jobs
        ;;
    --status)
        show_status
        ;;
    --help)
        echo "Usage: $0 [--remove|--status|--help]"
        echo ""
        echo "Options:"
        echo "  (no args)  Install cron jobs"
        echo "  --remove   Remove installed cron jobs"
        echo "  --status   Show current cron jobs"
        echo "  --help     Show this help message"
        ;;
    *)
        add_cron_jobs
        ;;
esac