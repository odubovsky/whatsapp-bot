# Python Bot Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY bot/requirements.txt /app/bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt

# Copy bot code
COPY bot/ /app/bot/
COPY app.json /app/app.json
COPY app.json.example /app/app.json.example
COPY prompts/ /app/prompts/

# Create directories for store
RUN mkdir -p /app/bot/store /shared/store

# Set PYTHONPATH
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the bot
CMD ["python", "-m", "bot.main"]

