#!/bin/bash
# AlphaMind - Development Server Startup Script

# Define colors for output
COLOR_RESET="\e[0m"
COLOR_GREEN="\e[32m"
COLOR_RED="\e[31m"
COLOR_YELLOW="\e[33m"
COLOR_BLUE="\e[34m"
COLOR_CYAN="\e[36m"

# --- Helper Functions ---

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

print_header() {
  echo -e "\n${COLOR_BLUE}===========================================================${COLOR_RESET}"
  echo -e "${COLOR_BLUE} $1 ${COLOR_RESET}"
  echo -e "${COLOR_BLUE}===========================================================${COLOR_RESET}"
}

print_success() {
  echo -e "${COLOR_GREEN}[SUCCESS] $1${COLOR_RESET}"
}

print_error() {
  echo -e "${COLOR_RED}[ERROR] $1${COLOR_RESET}" >&2
}

print_warning() {
  echo -e "${COLOR_YELLOW}[WARNING] $1${COLOR_RESET}"
}

print_info() {
  echo -e "${COLOR_CYAN}[INFO] $1${COLOR_RESET}"
}

# --- Initialization ---

# Note: set -e is intentionally NOT set globally here because we need to manage
# background process failures manually for a clean shutdown experience.
set -uo pipefail

PROJECT_ROOT="$(pwd)"
BACKEND_PID=""

# --- Graceful Shutdown ---

cleanup() {
  echo ""
  print_info "Shutting down development environment..."
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    print_info "Stopping backend server (PID: $BACKEND_PID)..."
    kill "$BACKEND_PID"
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  deactivate 2>/dev/null || true
  print_success "Development environment stopped."
  exit 0
}

trap cleanup SIGINT SIGTERM

# --- Environment Setup ---

print_header "Setting Up Development Environment"

if [[ -d "venv" ]]; then
  print_info "Activating Python virtual environment..."
  source venv/bin/activate
else
  print_error "Python virtual environment not found. Please run setup_environment.sh first."
  exit 1
fi

# Load .env file if present
if [[ -f ".env" ]]; then
  print_info "Loading .env configuration..."
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# --- Start Backend Server ---

start_backend() {
  print_header "Starting Backend Development Server"

  if [[ ! -d "code/backend" ]]; then
    print_error "Backend directory not found."
    return 1
  fi

  cd code/backend || return 1

  if command_exists uvicorn; then
    print_info "Starting Uvicorn server on http://0.0.0.0:8000 ..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
  elif command_exists gunicorn; then
    print_info "Starting Gunicorn server on http://0.0.0.0:8000 ..."
    gunicorn app.main:app --bind 0.0.0.0:8000 --reload --workers 1 &
    BACKEND_PID=$!
  elif python -c "import flask" 2>/dev/null; then
    print_info "Starting Flask development server on http://0.0.0.0:8000 ..."
    export FLASK_APP=app.main
    export FLASK_ENV=development
    flask run --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
  else
    print_error "No suitable backend server (uvicorn, gunicorn, flask) found. Please install one."
    cd "$PROJECT_ROOT" || exit 1
    return 1
  fi

  cd "$PROJECT_ROOT" || exit 1

  # Brief wait to detect immediate crashes
  sleep 2
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    print_error "Backend server failed to start."
    BACKEND_PID=""
    return 1
  fi

  print_success "Backend server started (PID: $BACKEND_PID)"
  return 0
}

# --- Start Web Frontend Server ---

start_web_frontend() {
  print_header "Starting Web Frontend Development Server"

  if [[ ! -d "web-frontend" ]]; then
    print_error "Web frontend directory not found."
    return 1
  fi

  cd web-frontend || return 1

  if [[ ! -f "package.json" ]]; then
    print_error "No package.json found in web-frontend directory."
    cd "$PROJECT_ROOT" || exit 1
    return 1
  fi

  if ! grep -q '"start"' package.json; then
    print_error "No 'start' script found in web-frontend/package.json."
    cd "$PROJECT_ROOT" || exit 1
    return 1
  fi

  print_info "Starting web frontend development server..."
  if [[ -f "yarn.lock" ]]; then
    yarn start
  else
    npm start
  fi

  cd "$PROJECT_ROOT" || exit 1
}

# --- Main Execution ---

print_header "Starting AlphaMind Development Environment"

# Start backend in background
if ! start_backend; then
  print_error "Failed to start backend. Aborting."
  cleanup
fi

print_info "Backend server started with PID: $BACKEND_PID"

# Start web frontend in the foreground (blocking)
start_web_frontend

# Frontend exited (normal stop) - clean up backend
cleanup
