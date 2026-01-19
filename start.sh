#!/bin/bash
export PYTHONPATH=$PYTHONPATH:/home/sebas024/.local/lib/python3.12/site-packages
export PATH=$PATH:/home/sebas024/.local/bin
cd /home/sebas024/htdocs/srv1274145.hstgr.cloud

# Kill existing
pkill -f uvicorn || true

# Remove old log to avoid confusion
rm -f app.log

# Start new
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8090 > app.log 2>&1 &

echo "Started uvicorn in background on port 8090. Checking logs..."
sleep 2
cat app.log
