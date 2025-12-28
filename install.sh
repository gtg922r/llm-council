#!/bin/bash

# LLM Council - Install/Setup script

set -e  # Exit on error

echo "Setting up LLM Council..."
echo "========================="

echo "[1/2] Installing Backend dependencies (uv)..."
uv sync

echo ""
echo "[2/2] Installing Frontend dependencies (npm)..."
cd frontend
npm install
cd ..

echo ""
echo "Setup complete! You can now run the app with ./start.sh"
