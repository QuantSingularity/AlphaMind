#!/bin/bash

# Run script for AlphaMind project
# This script starts both the backend and frontend components

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting AlphaMind application...${NC}"

# Resolve the project root relative to this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The scripts live in <repo>/scripts, so the project root is one level up.
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Create Python virtual environment if it doesn't exist
if [ ! -d "$PROJECT_ROOT/venv" ]; then
  echo -e "${BLUE}Creating Python virtual environment...${NC}"
  python3 -m venv "$PROJECT_ROOT/venv"
fi

# Start backend server
if [ ! -d "$PROJECT_ROOT/code/backend" ]; then
  echo -e "${RED}Backend directory not found. Exiting.${NC}"
  exit 1
fi

echo -e "${BLUE}Starting backend server...${NC}"
cd "$PROJECT_ROOT/code/backend" || exit 1
source "$PROJECT_ROOT/venv/bin/activate"
pip install -r requirements.txt > /dev/null 2>&1
python main.py &
BACKEND_PID=$!
cd "$PROJECT_ROOT" || exit 1

# Wait for backend to initialize
echo -e "${BLUE}Waiting for backend to initialize...${NC}"
sleep 5

# Verify backend started successfully
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo -e "${RED}Backend failed to start. Exiting.${NC}"
  exit 1
fi

# Start frontend
if [ ! -d "$PROJECT_ROOT/web-frontend" ]; then
  echo -e "${RED}Frontend directory not found. Stopping backend.${NC}"
  kill "$BACKEND_PID" 2>/dev/null
  exit 1
fi

echo -e "${BLUE}Starting frontend...${NC}"
cd "$PROJECT_ROOT/web-frontend" || exit 1
npm install > /dev/null 2>&1
npm start &
FRONTEND_PID=$!
cd "$PROJECT_ROOT" || exit 1

echo -e "${GREEN}AlphaMind application is running!${NC}"
echo -e "${GREEN}Backend running with PID: ${BACKEND_PID}${NC}"
echo -e "${GREEN}Frontend running with PID: ${FRONTEND_PID}${NC}"
echo -e "${GREEN}Access the application at: http://localhost:3000${NC}"
echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"

# Handle graceful shutdown
cleanup() {
  echo -e "${BLUE}Stopping services...${NC}"
  if kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID"
  fi
  if kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID"
  fi
  deactivate 2>/dev/null || true
  echo -e "${GREEN}All services stopped${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script running
wait
