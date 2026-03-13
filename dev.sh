#!/bin/bash
# Kill any existing python processes on our ports, then start fresh.
# Usage: bash dev.sh

echo "Cleaning up old processes..."

# Kill anything on port 8001
PID=$(netstat -ano 2>/dev/null | grep ":8001.*LISTEN" | awk '{print $5}' | head -1)
if [ -n "$PID" ] && [ "$PID" != "0" ]; then
    taskkill //PID "$PID" //F //T 2>/dev/null
    echo "Killed process $PID on port 8001"
    sleep 1
fi

# Kill any remaining python.exe that are uvicorn
tasklist //FI "IMAGENAME eq python.exe" 2>/dev/null | grep -q python && {
    taskkill //F //FI "IMAGENAME eq python.exe" 2>/dev/null
    echo "Killed remaining python processes"
    sleep 1
}

# Clean SQLite lock files
rm -f data/yourwriter.db-journal data/yourwriter.db-shm 2>/dev/null

echo "Starting backend on port 8001..."
uvicorn backend.main:app --port 8001 --reload &
BACKEND_PID=$!

sleep 2
echo ""
echo "Backend: http://localhost:8001 (PID $BACKEND_PID)"
echo "Frontend: run 'cd frontend && npx vite --port 3000' in another terminal"
echo ""
echo "Press Ctrl+C to stop"
wait $BACKEND_PID
