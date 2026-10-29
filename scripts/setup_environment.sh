#!/bin/bash
# AlphaMind - Unified Environment Setup Script
# This script automates the setup of development environments for the AlphaMind project
# It detects the OS, installs dependencies, and configures development tools

# Define colors for output
COLOR_RESET="\e[0m"
COLOR_GREEN="\e[32m"
COLOR_RED="\e[31m"
COLOR_YELLOW="\e[33m"
COLOR_BLUE="\e[34m"
COLOR_CYAN="\e[36m"

# --- Helper Functions ---

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to print section headers
print_header() {
  echo -e "\n${COLOR_BLUE}===========================================================${COLOR_RESET}"
  echo -e "${COLOR_BLUE} $1 ${COLOR_RESET}"
  echo -e "${COLOR_BLUE}===========================================================${COLOR_RESET}"
}

# Function to print success messages
print_success() {
  echo -e "${COLOR_GREEN}[SUCCESS] $1${COLOR_RESET}"
}

# Function to print error messages
print_error() {
  echo -e "${COLOR_RED}[ERROR] $1${COLOR_RESET}" >&2
}

# Function to print warning messages
print_warning() {
  echo -e "${COLOR_YELLOW}[WARNING] $1${COLOR_RESET}"
}

# Function to print info messages
print_info() {
  echo -e "${COLOR_CYAN}[INFO] $1${COLOR_RESET}"
}

# --- Initialization ---

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# Define project root directory (assuming the script is in the project root)
PROJECT_ROOT="$(pwd)"

# Parse command line arguments
SETUP_TYPE="development"
VERBOSE=false
SKIP_PYTHON=false
SKIP_NODE=false
SKIP_DOCKER=false
FORCE_REINSTALL=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --type)
      SETUP_TYPE="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --skip-python)
      SKIP_PYTHON=true
      shift
      ;;
    --skip-node)
      SKIP_NODE=true
      shift
      ;;
    --skip-docker)
      SKIP_DOCKER=true
      shift
      ;;
    --force-reinstall)
      FORCE_REINSTALL=true
      shift
      ;;
    --help)
      echo "Usage: ./setup_environment.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --type TYPE            Setup type: development, testing, or production (default: development)"
      echo "  --verbose              Enable verbose output"
      echo "  --skip-python          Skip Python environment setup"
      echo "  --skip-node            Skip Node.js environment setup"
      echo "  --skip-docker          Skip Docker setup"
      echo "  --force-reinstall      Force reinstallation of components"
      echo "  --help                 Show this help message"
      exit 0
      ;;
    *)
      print_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Enable shell tracing when verbose output is requested.
if [[ "$VERBOSE" == "true" ]]; then
  set -x
fi

# --- OS Detection ---

print_header "OS Detection"

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="linux"
  if command_exists apt-get; then
    PACKAGE_MANAGER="apt"
  elif command_exists dnf; then
    PACKAGE_MANAGER="dnf"
  elif command_exists yum; then
    PACKAGE_MANAGER="yum"
  else
    print_error "Unsupported Linux distribution. Please install dependencies manually."
    exit 1
  fi
  print_success "Detected Linux OS with $PACKAGE_MANAGER package manager"
elif [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macos"
  if command_exists brew; then
    PACKAGE_MANAGER="brew"
    print_success "Detected macOS with Homebrew package manager"
  else
    print_error "Homebrew not found. Please install Homebrew first: https://brew.sh/"
    exit 1
  fi
else
  print_error "Unsupported operating system: $OSTYPE"
  print_info "This script supports Linux and macOS. For Windows, please use WSL or Docker."
  exit 1
fi

# --- System Dependencies ---

print_header "Installing System Dependencies"

install_system_dependencies() {
  if [[ "$OS" == "linux" ]]; then
    if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
      print_info "Updating package lists..."
      sudo apt-get update

      print_info "Installing essential build tools and libraries..."
      sudo apt-get install -y build-essential curl wget git unzip zip \
        libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
        libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev
    elif [[ "$PACKAGE_MANAGER" == "dnf" || "$PACKAGE_MANAGER" == "yum" ]]; then
      print_info "Updating package lists..."
      sudo $PACKAGE_MANAGER update -y

      print_info "Installing essential build tools and libraries..."
      sudo $PACKAGE_MANAGER install -y gcc gcc-c++ make curl wget git unzip zip \
        openssl-devel zlib-devel bzip2-devel readline-devel sqlite-devel \
        ncurses-devel tk-devel libffi-devel xz-devel
    fi
  elif [[ "$OS" == "macos" ]]; then
    print_info "Updating Homebrew..."
    brew update

    print_info "Installing essential build tools and libraries..."
    brew install curl wget git unzip zip openssl readline sqlite3 xz
  fi

  print_success "System dependencies installed successfully"
}

install_system_dependencies

# --- Python Environment Setup ---

if [[ "$SKIP_PYTHON" == "false" ]]; then
  print_header "Setting up Python Environment"

  # Check for Python 3.10+
  if command_exists python3.12; then
    PYTHON_CMD="python3.12"
  elif command_exists python3.11; then
    PYTHON_CMD="python3.11"
  elif command_exists python3.10; then
    PYTHON_CMD="python3.10"
  elif command_exists python3; then
    PY_VERSION=$(python3 --version | cut -d' ' -f2)
    if [[ $(echo "$PY_VERSION" | cut -d. -f1,2 | sed 's/\.//') -ge 310 ]]; then
      PYTHON_CMD="python3"
    else
      print_warning "Python 3.10+ is required but found $PY_VERSION"

      if [[ "$OS" == "linux" ]]; then
        if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
          print_info "Installing Python 3.10..."
          sudo add-apt-repository -y ppa:deadsnakes/ppa
          sudo apt-get update
          sudo apt-get install -y python3.10 python3.10-venv python3.10-dev
          PYTHON_CMD="python3.10"
        elif [[ "$PACKAGE_MANAGER" == "dnf" ]]; then
          print_info "Installing Python 3.10..."
          sudo dnf install -y python3.10 python3.10-devel
          PYTHON_CMD="python3.10"
        else
          print_error "Please install Python 3.10+ manually"
          exit 1
        fi
      elif [[ "$OS" == "macos" ]]; then
        print_info "Installing Python 3.10 via Homebrew..."
        brew install python@3.10
        PYTHON_CMD="python3.10"
      fi
    fi
  else
    print_error "Python 3 not found"
    exit 1
  fi

  print_success "Using Python: $($PYTHON_CMD --version)"

  # Set up virtual environment
  print_info "Setting up Python virtual environment..."

  if [[ -d "venv" && "$FORCE_REINSTALL" == "true" ]]; then
    print_info "Removing existing virtual environment..."
    rm -rf venv
  fi

  if [[ ! -d "venv" ]]; then
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
  else
    print_info "Using existing virtual environment"
  fi

  # Activate virtual environment
  source venv/bin/activate

  # Upgrade pip
  print_info "Upgrading pip..."
  pip install --upgrade pip

  # Install dependencies based on setup type
  print_info "Installing Python dependencies for $SETUP_TYPE environment..."

  if [[ "$SETUP_TYPE" == "development" ]]; then
    pip install -r code/backend/requirements.txt
    pip install pytest pytest-cov black flake8 mypy sphinx sphinx-rtd-theme
  elif [[ "$SETUP_TYPE" == "testing" ]]; then
    pip install -r code/backend/requirements.txt
    pip install pytest pytest-cov pytest-benchmark pytest-mock
  elif [[ "$SETUP_TYPE" == "production" ]]; then
    pip install -r code/backend/requirements.txt
  fi

  print_success "Python environment setup complete"

  # Deactivate virtual environment
  deactivate
fi

# --- Node.js Environment Setup ---

if [[ "$SKIP_NODE" == "false" ]]; then
  print_header "Setting up Node.js Environment"

  # Check for Node.js
  if command_exists node; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    if [[ $(echo "$NODE_VERSION" | cut -d. -f1) -ge 18 ]]; then
      print_success "Using Node.js $NODE_VERSION"
    else
      print_warning "Node.js 18+ is required but found $NODE_VERSION"

      if [[ "$OS" == "linux" ]]; then
        print_info "Installing Node.js 18 via NodeSource..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
      elif [[ "$OS" == "macos" ]]; then
        print_info "Installing Node.js 18 via Homebrew..."
        brew install node@18
        brew link --force node@18
      fi

      print_success "Node.js $(node --version) installed"
    fi
  else
    print_info "Node.js not found, installing..."

    if [[ "$OS" == "linux" ]]; then
      curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
      sudo apt-get install -y nodejs
    elif [[ "$OS" == "macos" ]]; then
      brew install node@18
      brew link --force node@18
    fi

    print_success "Node.js $(node --version) installed"
  fi

  # Check for npm
  if ! command_exists npm; then
    print_error "npm not found. Please install npm manually."
    exit 1
  fi

  print_success "Using npm $(npm --version)"

  # Install global npm packages based on setup type
  print_info "Installing global npm packages for $SETUP_TYPE environment..."

  if [[ "$SETUP_TYPE" == "development" ]]; then
    npm install -g yarn pnpm typescript eslint prettier
  elif [[ "$SETUP_TYPE" == "testing" ]]; then
    npm install -g yarn pnpm
  elif [[ "$SETUP_TYPE" == "production" ]]; then
    npm install -g yarn pnpm
  fi

  # Install frontend dependencies
  if [[ -d "web-frontend" ]]; then
    print_info "Installing web frontend dependencies..."
    cd web-frontend

    if [[ -f "yarn.lock" ]]; then
      yarn install
    elif [[ -f "package-lock.json" ]]; then
      npm ci
    else
      npm install
    fi

    cd "$PROJECT_ROOT"
    print_success "Web frontend dependencies installed"
  fi

  # Install mobile frontend dependencies
  if [[ -d "mobile-frontend" ]]; then
    print_info "Installing mobile frontend dependencies..."
    cd mobile-frontend

    if [[ -f "yarn.lock" ]]; then
      yarn install
    elif [[ -f "package-lock.json" ]]; then
      npm ci
    else
      npm install
    fi

    cd "$PROJECT_ROOT"
    print_success "Mobile frontend dependencies installed"
  fi

  print_success "Node.js environment setup complete"
fi

# --- Docker Setup ---

if [[ "$SKIP_DOCKER" == "false" ]]; then
  print_header "Setting up Docker"

  # Check for Docker
  if command_exists docker; then
    print_success "Docker is already installed: $(docker --version)"
  else
    print_info "Docker not found, installing..."

    if [[ "$OS" == "linux" ]]; then
      curl -fsSL https://get.docker.com -o get-docker.sh
      sudo sh get-docker.sh
      sudo usermod -aG docker $USER
      print_warning "You may need to log out and log back in for Docker group changes to take effect"
    elif [[ "$OS" == "macos" ]]; then
      print_info "Please install Docker Desktop for Mac manually: https://docs.docker.com/desktop/mac/install/"
      print_info "After installation, run this script again with --skip-docker"
    fi

    if command_exists docker; then
      print_success "Docker installed: $(docker --version)"
    else
      print_warning "Docker installation may require manual steps"
    fi
  fi

  # Check for Docker Compose
  if command_exists docker-compose; then
    print_success "Docker Compose is already installed: $(docker-compose --version)"
  elif docker compose version &>/dev/null; then
    print_success "Docker Compose V2 is already installed"
  else
    print_info "Docker Compose not found, installing..."

    if [[ "$OS" == "linux" ]]; then
      COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
      sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
      sudo chmod +x /usr/local/bin/docker-compose
    elif [[ "$OS" == "macos" ]]; then
      brew install docker-compose
    fi

    if command_exists docker-compose; then
      print_success "Docker Compose installed: $(docker-compose --version)"
    else
      print_warning "Docker Compose installation may require manual steps"
    fi
  fi

  print_success "Docker setup complete"
fi

# --- Environment Validation ---

print_header "Environment Validation"

VALIDATION_PASSED=true

# Validate Python environment
if [[ "$SKIP_PYTHON" == "false" ]]; then
  print_info "Validating Python environment..."

  if [[ ! -d "venv" ]]; then
    print_error "Python virtual environment not found"
    VALIDATION_PASSED=false
  else
    source venv/bin/activate

    if ! pip list | grep -q "pytest"; then
      print_warning "pytest not found in virtual environment"
    fi

    if [[ "$SETUP_TYPE" == "development" ]] && ! pip list | grep -q "black"; then
      print_warning "black not found in virtual environment"
    fi

    deactivate
  fi
fi

# Validate Node.js environment
if [[ "$SKIP_NODE" == "false" ]]; then
  print_info "Validating Node.js environment..."

  if ! command_exists node; then
    print_error "Node.js not found"
    VALIDATION_PASSED=false
  fi

  if ! command_exists npm; then
    print_error "npm not found"
    VALIDATION_PASSED=false
  fi

  if [[ -d "web-frontend" ]]; then
    if [[ ! -d "web-frontend/node_modules" ]]; then
      print_warning "Web frontend dependencies not installed"
    fi
  fi

  if [[ -d "mobile-frontend" ]]; then
    if [[ ! -d "mobile-frontend/node_modules" ]]; then
      print_warning "Mobile frontend dependencies not installed"
    fi
  fi
fi

# Validate Docker environment
if [[ "$SKIP_DOCKER" == "false" ]]; then
  print_info "Validating Docker environment..."

  if ! command_exists docker; then
    print_error "Docker not found"
    VALIDATION_PASSED=false
  else
    if ! docker info &>/dev/null; then
      print_warning "Docker daemon is not running or current user doesn't have permission"
    fi
  fi

  if ! command_exists docker-compose && ! (docker compose version &>/dev/null); then
    print_warning "Docker Compose not found"
  fi
fi

# Final validation result
if [[ "$VALIDATION_PASSED" == "true" ]]; then
  print_success "Environment validation passed"
else
  print_warning "Environment validation completed with warnings or errors"
fi

# --- Create Environment Configuration ---

print_header "Creating Environment Configuration"

# Create .env file if it doesn't exist
if [[ ! -f ".env" || "$FORCE_REINSTALL" == "true" ]]; then
  print_info "Creating .env file..."

  cat > .env << EOF
# AlphaMind Environment Configuration
# Generated by setup_environment.sh on $(date)

# Environment type
ALPHAMIND_ENV=${SETUP_TYPE}

# Paths
PROJECT_ROOT=${PROJECT_ROOT}
PYTHON_VENV=${PROJECT_ROOT}/venv
PYTHON_BIN=${PROJECT_ROOT}/venv/bin/python

# Database configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=alphamind
DB_USER=alphamind
DB_PASSWORD=alphamind_password

# API configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# Web frontend configuration
WEB_PORT=3000

# Mobile frontend configuration
MOBILE_PORT=8081

# Docker configuration
DOCKER_COMPOSE_FILE=docker-compose.yml
EOF

  print_success ".env file created"
else
  print_info "Using existing .env file"
fi

# --- Summary ---

print_header "Setup Summary"

echo -e "Setup type: ${COLOR_CYAN}${SETUP_TYPE}${COLOR_RESET}"
echo -e "Project root: ${COLOR_CYAN}${PROJECT_ROOT}${COLOR_RESET}"

if [[ "$SKIP_PYTHON" == "false" ]]; then
  echo -e "Python: ${COLOR_CYAN}$($PYTHON_CMD --version)${COLOR_RESET}"
  echo -e "Virtual environment: ${COLOR_CYAN}${PROJECT_ROOT}/venv${COLOR_RESET}"
fi

if [[ "$SKIP_NODE" == "false" ]]; then
  echo -e "Node.js: ${COLOR_CYAN}$(node --version)${COLOR_RESET}"
  echo -e "npm: ${COLOR_CYAN}$(npm --version)${COLOR_RESET}"
fi

if [[ "$SKIP_DOCKER" == "false" ]] && command_exists docker; then
  echo -e "Docker: ${COLOR_CYAN}$(docker --version)${COLOR_RESET}"
  if command_exists docker-compose; then
    echo -e "Docker Compose: ${COLOR_CYAN}$(docker-compose --version)${COLOR_RESET}"
  elif docker compose version &>/dev/null; then
    echo -e "Docker Compose: ${COLOR_CYAN}Docker Compose V2${COLOR_RESET}"
  fi
fi

echo ""
print_success "Environment setup completed successfully!"
echo ""
print_info "To activate the Python virtual environment, run:"
echo -e "  ${COLOR_CYAN}source venv/bin/activate${COLOR_RESET}"
echo ""
print_info "To start the development servers:"
echo -e "  ${COLOR_CYAN}./run_alphamind.sh${COLOR_RESET}"
echo ""
print_info "For more information, see the documentation in the docs/ directory."
