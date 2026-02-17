#!/bin/bash

# Start FastAPI Backend Server
# Usage: ./start-backend.sh

echo "Starting Startup Ideas Collector Backend..."
echo "=========================================="

cd "$(dirname "$0")/backend" || exit

# Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Error: Virtual environment not found!"
    echo "Please run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if database exists
if [ ! -f "data/startup_ideas.db" ]; then
    echo "Database not found. Initializing..."
    PYTHONPATH=. python db/database.py
fi

# Start FastAPI server
echo "Starting FastAPI server on http://localhost:8000"
echo "API docs available at: http://localhost:8000/docs"
echo "=========================================="

PYTHONPATH=. uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
