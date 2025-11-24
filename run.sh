#!/bin/bash
# WhatsApp Bot Runner Script
# Production-ready runner with logging

set -e

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found. Run ./setup.sh first"
    exit 1
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Create logs directory
mkdir -p logs

# Run with logging (stdout + file)
exec python3 main.py "$@" 2>&1 | tee -a logs/whatsapp-bot.log
