#!/bin/bash

# Stop script for PDB Notes Reporting

echo "Stopping PDB Notes Reporting..."

# Stop backend
if [ -f /tmp/pdb-backend.pid ]; then
    BACKEND_PID=$(cat /tmp/pdb-backend.pid)
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo "Backend stopped (PID: $BACKEND_PID)"
    else
        echo "Backend process not running"
    fi
    rm -f /tmp/pdb-backend.pid
else
    # Fallback: kill by process name
    pkill -f "uvicorn.*app.main:app" 2>/dev/null && echo "Backend stopped" || echo "Backend not running"
fi

# Stop frontend (if running)
if [ -f /tmp/pdb-frontend.pid ]; then
    FRONTEND_PID=$(cat /tmp/pdb-frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo "Frontend stopped (PID: $FRONTEND_PID)"
    else
        echo "Frontend process not running"
    fi
    rm -f /tmp/pdb-frontend.pid
fi

echo "All services stopped"
