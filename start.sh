#!/bin/bash

# Symposia - Start script

echo "Starting Symposia..."
echo "  Backend:  http://localhost:8001"
echo "  Frontend: http://localhost:5173"
echo ""
echo "  DEV_AUTH is enabled - use 'Dev Login' button for easy testing"
echo ""

# Use npx concurrently to run both processes
# -k: kill others if one dies
# -n: names for the logs
# -c: colors for the logs
# PYTHONUNBUFFERED=1 ensures Python output is not hidden/buffered
# DEV_AUTH=true enables dev authentication bypass
npx concurrently -k \
    -n "BACKEND,FRONTEND" \
    -c "cyan,magenta" \
    "PYTHONUNBUFFERED=1 DEV_AUTH=true uv run python -m backend.main" \
    "sleep 2 && cd frontend && npm run dev"
