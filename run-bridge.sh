#!/bin/bash
# WhatsApp Bridge Runner Script
# Production-ready runner with logging

set -e

# Change to bridge directory
cd whatsapp-bridge

# Create logs directory
mkdir -p logs

# Run with logging (stdout + file)
exec ./whatsapp-client "$@" 2>&1 | tee -a logs/whatsapp-bridge.log

