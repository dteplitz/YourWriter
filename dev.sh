#!/bin/bash
# Start the local dev environment via Docker Compose.
# Usage: bash dev.sh
#
# First run: docker compose builds the images (~2min). Subsequent runs are fast.
# Backend:  http://localhost:8001  (uvicorn --reload, hot reloads on code changes)
# Frontend: http://localhost:3000  (vite dev, HMR)
# Postgres: internal to the compose network on port 5432
#           (data persists in the pg_data volume across `docker compose down`)

docker compose up --build
