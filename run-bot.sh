#!/bin/bash
# WhatsApp Bot Runner Script
# Production-ready runner with logging

set -e

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Create logs directory
mkdir -p bot/logs

# Run with logging (stdout + file)
exec python3 bot/main.py "$@" 2>&1 | tee -a bot/logs/whatsapp-bot.log
