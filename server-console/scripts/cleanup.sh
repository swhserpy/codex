#!/usr/bin/env bash
# Whitelisted cleanup script
set -e
echo "🧹 Cleaning temporary files..."
find /tmp -name "*.log" -mtime +3 -delete 2>/dev/null && echo "  Cleaned old logs in /tmp"
find "${HOME}" -name "*.pyc" -delete 2>/dev/null && echo "  Cleaned .pyc files"
echo "✅ Cleanup complete"
