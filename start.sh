#!/bin/bash

# LLM Council - Start script

echo "Starting LLM Council..."
echo "  Backend:  http://localhost:8001"
echo "  Frontend: http://localhost:5173"
echo ""

# Use npx concurrently to run both processes
# -k: kill others if one dies
# -n: names for the logs
# -c: colors for the logs
# PYTHONUNBUFFERED=1 ensures Python output is not hidden/buffered
npx concurrently -k \
    -n "BACKEND,FRONTEND" \
    -c "cyan,magenta" \
    "PYTHONUNBUFFERED=1 uv run python -m backend.main" \
    "sleep 2 && cd frontend && npm run dev"
