#!/bin/bash
# Start the local dev environment via Docker Compose.
# Usage: bash dev.sh
#
# First run: docker compose builds the images (~2min). Subsequent runs are fast.
# Backend:  http://localhost:8001  (uvicorn --reload, hot reloads on code changes)
# Frontend: http://localhost:3000  (vite dev, HMR)

# Clean SQLite lock files before starting
rm -f data/yourwriter.db-journal data/yourwriter.db-shm 2>/dev/null

docker compose up --build
