#!/bin/bash
# Kill any existing uvicorn process to ensure clean restart
pkill -f uvicorn || true

# Start the application in background
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8090 > app.log 2>&1 &
