#!/bin/bash
# Render start command - starts both services

# Start channel service on port 8001 in background
cd channel-service
python -m uvicorn main:app --host 0.0.0.0 --port 8001 &
CHANNEL_PID=$!

# Give channel service a moment to start
sleep 2

# Start CRM API on the main port (PORT env var from Render, default 8000)
cd ../backend
exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
