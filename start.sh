#!/bin/bash

# Start script for PDB Notes Reporting
# Run from the project root directory

set -e

echo "Starting PDB Notes Reporting..."

# Build frontend
echo "Building frontend..."
cd frontend
npm run build
cd ..
echo "Frontend built successfully"

# Start backend (serves both API and frontend)
echo "Starting backend..."
cd backend
./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/pdb-backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/pdb-backend.pid
cd ..

# Wait for backend to be ready
sleep 2

# Check if backend started successfully
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "Backend started successfully (PID: $BACKEND_PID)"
else
    echo "Warning: Backend may not have started correctly. Check /tmp/pdb-backend.log"
fi

echo ""
echo "==========================================="
echo "PDB Notes Reporting is running!"
echo "==========================================="
echo ""
echo "  URL:   http://localhost:8000"
echo "  Logs:  /tmp/pdb-backend.log"
echo ""
echo "To stop: ./stop.sh"
echo ""
