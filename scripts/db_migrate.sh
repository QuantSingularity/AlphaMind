#!/bin/bash
# AlphaMind - Database Migration Script

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

set -euo pipefail

PROJECT_ROOT="$(pwd)"

ACTION=""
MESSAGE=""
ENVIRONMENT="development"

while [[ $# -gt 0 ]]; do
  case $1 in
    --action)
      ACTION="$2"
      shift 2
      ;;
    --message)
      MESSAGE="$2"
      shift 2
      ;;
    --env)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --help)
      echo "Usage: ./db_migrate.sh --action [init|migrate|upgrade|downgrade|history|current] [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --action ACTION        Migration action: init, migrate, upgrade, downgrade, history, current"
      echo "  --message MESSAGE      Migration message (required for 'migrate')"
      echo "  --env ENVIRONMENT      Environment to run migration against (default: development)"
      echo "  --help                 Show this help message"
      exit 0
      ;;
    *)
      print_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$ACTION" ]]; then
  print_error "Migration action is required. Use --help for usage."
  exit 1
fi

# --- Environment Setup ---

print_header "Setting Up Database Migration Environment"

if [[ -d "venv" ]]; then
  print_info "Activating Python virtual environment..."
  source venv/bin/activate
else
  print_error "Python virtual environment not found. Please run setup_environment.sh first."
  exit 1
fi

# Load environment variables safely (skip blank lines and comments)
ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
if [[ -f "$ENV_FILE" ]]; then
  print_info "Loading environment variables from $ENV_FILE"
  while IFS='=' read -r key value; do
    # Skip blank lines and comment lines
    [[ -z "$key" || "$key" == \#* ]] && continue
    # Strip leading/trailing whitespace from key
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    [[ -z "$key" ]] && continue
    export "$key"="$value"
  done < "$ENV_FILE"
else
  print_warning "Environment file $ENV_FILE not found. Using default environment."
fi

if ! command_exists alembic; then
  print_error "Alembic not found. Please install it in your virtual environment (pip install alembic)."
  deactivate
  exit 1
fi

if [[ ! -d "code/backend" ]]; then
  print_error "Backend directory not found."
  deactivate
  exit 1
fi
cd code/backend

# --- Run Migration Action ---

print_header "Running Database Migration Action: $ACTION"

case "$ACTION" in
  init)
    print_info "Initializing Alembic environment..."
    alembic init migrations
    print_success "Alembic environment initialized. Review migrations/alembic.ini and migrations/env.py."
    ;;
  migrate)
    if [[ -z "$MESSAGE" ]]; then
      print_error "Migration message is required for 'migrate' action. Use --message."
      deactivate
      exit 1
    fi
    print_info "Creating new migration with message: $MESSAGE"
    alembic revision --autogenerate -m "$MESSAGE"
    print_success "New migration created."
    ;;
  upgrade)
    print_info "Upgrading database to latest revision..."
    alembic upgrade head
    print_success "Database upgrade complete."
    ;;
  downgrade)
    print_info "Downgrading database by one revision..."
    alembic downgrade -1
    print_success "Database downgrade complete."
    ;;
  history)
    print_info "Showing migration history..."
    alembic history --verbose
    ;;
  current)
    print_info "Showing current database revision..."
    alembic current
    ;;
  *)
    print_error "Invalid action: $ACTION. Supported actions: init, migrate, upgrade, downgrade, history, current."
    deactivate
    exit 1
    ;;
esac

cd "$PROJECT_ROOT"
deactivate

print_success "Database migration script finished."
