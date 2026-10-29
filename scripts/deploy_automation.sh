#!/bin/bash
# AlphaMind - Deployment Automation Script
# This script automates the deployment process for the AlphaMind project
# It supports multiple deployment targets and includes rollback mechanisms

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

# Function to run a command and measure its execution time
run_timed() {
  local start_time
  start_time=$(date +%s)
  "$@"
  local status=$?
  local end_time
  end_time=$(date +%s)
  local duration=$((end_time - start_time))

  echo -e "${COLOR_CYAN}Command completed in ${duration}s${COLOR_RESET}"
  return $status
}

# Function to run a command remotely via SSH
run_remote() {
  if [[ -z "$REMOTE_HOST" ]]; then
    print_error "Remote host not configured"
    return 1
  fi

  local remote_target="${REMOTE_USER:-$(whoami)}@${REMOTE_HOST}"
  print_info "Running on $remote_target: $1"
  ssh $SSH_OPTIONS "$remote_target" "$1"
}

# Function to transfer files/dirs using scp
transfer_files() {
  if [[ -z "$REMOTE_HOST" ]]; then
    print_error "Remote host not configured"
    return 1
  fi

  local source="$1"
  local dest="$2"

  local remote_target="${REMOTE_USER:-$(whoami)}@${REMOTE_HOST}"
  print_info "Transferring $source to $remote_target:$dest"
  scp -P "$REMOTE_PORT" -r "$source" "$remote_target:$dest"
}

# --- Initialization ---

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# Define project root directory (assuming the script is in the project root)
PROJECT_ROOT="$(pwd)"

# Parse command line arguments
DEPLOY_ENV="development"
COMPONENT=""
VERBOSE=false
LOG_DIR="$PROJECT_ROOT/deploy-logs"
DRY_RUN=false
ROLLBACK=false
SKIP_BUILD=false
SKIP_TESTS=false
FORCE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --env)
      DEPLOY_ENV="$2"
      shift 2
      ;;
    --component)
      COMPONENT="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --log-dir)
      LOG_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --rollback)
      ROLLBACK=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --skip-tests)
      SKIP_TESTS=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --help)
      echo "Usage: ./deploy.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --env ENV              Deployment environment: development, staging, production (default: development)"
      echo "  --component COMPONENT  Specific component to deploy (e.g., backend, web-frontend)"
      echo "  --verbose              Enable verbose output"
      echo "  --log-dir DIR          Directory for deployment logs (default: ./deploy-logs)"
      echo "  --dry-run              Simulate deployment without making changes"
      echo "  --rollback             Rollback to previous deployment"
      echo "  --skip-build           Skip build step"
      echo "  --skip-tests           Skip tests before deployment"
      echo "  --force                Force deployment even if tests fail"
      echo "  --help                 Show this help message"
      exit 0
      ;;
    *)
      print_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# --- Environment Setup ---

print_header "Setting Up Deployment Environment"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy-$(date +%Y%m%d-%H%M%S).log"

# Start logging
exec > >(stdbuf -oL tee -a "$LOG_FILE") 2>&1
print_info "Logging to $LOG_FILE"

# Load deployment configuration
CONFIG_FILE="$PROJECT_ROOT/config/deploy/$DEPLOY_ENV.conf"
if [[ ! -f "$CONFIG_FILE" ]]; then
  print_warning "Deployment configuration file not found: $CONFIG_FILE"
  print_info "Creating default configuration..."

  # Create config directory if it doesn't exist
  mkdir -p "$PROJECT_ROOT/config/deploy"

  # Create default configuration based on environment
  case "$DEPLOY_ENV" in
    development)
      cat > "$CONFIG_FILE" << EOF
# AlphaMind Development Deployment Configuration

# Remote server configuration
REMOTE_HOST=localhost
REMOTE_USER=$(whoami)
REMOTE_PORT=22
REMOTE_DIR=/var/www/alphamind-dev

# Database configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=alphamind_dev
DB_USER=alphamind
DB_PASSWORD=alphamind_password

# Web server configuration
WEB_SERVER=nginx
WEB_SERVER_CONFIG=/etc/nginx/sites-available/alphamind-dev.conf
WEB_SERVER_ENABLED=/etc/nginx/sites-enabled/alphamind-dev.conf

# Application server configuration
APP_SERVER=gunicorn
APP_SERVER_CONFIG=/etc/systemd/system/alphamind-dev.service

# Docker configuration
USE_DOCKER=false
DOCKER_COMPOSE_FILE=docker-compose.dev.yml

# Deployment strategy
DEPLOYMENT_STRATEGY=direct
KEEP_RELEASES=3
EOF
      ;;
    staging)
      cat > "$CONFIG_FILE" << EOF
# AlphaMind Staging Deployment Configuration

# Remote server configuration
REMOTE_HOST=staging.alphamind.example.com
REMOTE_USER=deploy
REMOTE_PORT=22
REMOTE_DIR=/var/www/alphamind-staging

# Database configuration
DB_HOST=db.staging.alphamind.example.com
DB_PORT=5432
DB_NAME=alphamind_staging
DB_USER=alphamind
DB_PASSWORD=alphamind_staging_password

# Web server configuration
WEB_SERVER=nginx
WEB_SERVER_CONFIG=/etc/nginx/sites-available/alphamind-staging.conf
WEB_SERVER_ENABLED=/etc/nginx/sites-enabled/alphamind-staging.conf

# Application server configuration
APP_SERVER=gunicorn
APP_SERVER_CONFIG=/etc/systemd/system/alphamind-staging.service

# Docker configuration
USE_DOCKER=true
DOCKER_COMPOSE_FILE=docker-compose.staging.yml

# Deployment strategy
DEPLOYMENT_STRATEGY=blue-green
KEEP_RELEASES=5
EOF
      ;;
    production)
      cat > "$CONFIG_FILE" << EOF
# AlphaMind Production Deployment Configuration

# Remote server configuration
REMOTE_HOST=alphamind.example.com
REMOTE_USER=deploy
REMOTE_PORT=22
REMOTE_DIR=/var/www/alphamind-production

# Database configuration
DB_HOST=db.alphamind.example.com
DB_PORT=5432
DB_NAME=alphamind_production
DB_USER=alphamind
DB_PASSWORD=alphamind_production_password

# Web server configuration
WEB_SERVER=nginx
WEB_SERVER_CONFIG=/etc/nginx/sites-available/alphamind.conf
WEB_SERVER_ENABLED=/etc/nginx/sites-enabled/alphamind.conf

# Application server configuration
APP_SERVER=gunicorn
APP_SERVER_CONFIG=/etc/systemd/system/alphamind.service

# Docker configuration
USE_DOCKER=true
DOCKER_COMPOSE_FILE=docker-compose.prod.yml

# Deployment strategy
DEPLOYMENT_STRATEGY=blue-green
KEEP_RELEASES=10
EOF
      ;;
    *)
      print_error "Unknown environment: $DEPLOY_ENV"
      exit 1
      ;;
  esac

  print_success "Default configuration created: $CONFIG_FILE"
  print_warning "Please review and update the configuration before deploying"

  if [[ "$FORCE" != "true" ]]; then
    print_info "Exiting. Run with --force to continue with default configuration."
    exit 0
  fi
fi

# Set defaults before loading config (in case config is missing some vars)
REMOTE_HOST="${REMOTE_HOST:-localhost}"
REMOTE_PORT="${REMOTE_PORT:-22}"
REMOTE_DIR="${REMOTE_DIR:-/var/www/alphamind}"
USE_DOCKER="${USE_DOCKER:-false}"
DEPLOYMENT_STRATEGY="${DEPLOYMENT_STRATEGY:-direct}"
KEEP_RELEASES="${KEEP_RELEASES:-5}"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-docker-compose.yml}"

# Load configuration
# shellcheck source=/dev/null
source "$CONFIG_FILE"

# Set up SSH options
SSH_OPTIONS="-p $REMOTE_PORT"
if [[ "$VERBOSE" == "true" ]]; then
  SSH_OPTIONS="$SSH_OPTIONS -v"
else
  SSH_OPTIONS="$SSH_OPTIONS -q"
fi

# Set up component-specific paths
if [[ -n "$COMPONENT" ]]; then
  if [[ "$COMPONENT" == "backend" ]]; then
    COMPONENTS=("backend")
  elif [[ "$COMPONENT" == "web-frontend" ]]; then
    COMPONENTS=("web-frontend")
  elif [[ "$COMPONENT" == "mobile-frontend" ]]; then
    COMPONENTS=("mobile-frontend")
  elif [[ -d "$COMPONENT" ]]; then
    COMPONENTS=("$COMPONENT")
  else
    print_error "Component directory not found: $COMPONENT"
    exit 1
  fi
else
  COMPONENTS=("backend" "web-frontend")
fi

print_info "Deployment configuration:"
echo "  Environment: $DEPLOY_ENV"
echo "  Components: ${COMPONENTS[*]}"
echo "  Remote host: $REMOTE_HOST"
echo "  Remote directory: $REMOTE_DIR"
echo "  Deployment strategy: $DEPLOYMENT_STRATEGY"
echo "  Docker: $USE_DOCKER"
echo "  Dry run: $DRY_RUN"
echo "  Rollback: $ROLLBACK"

# --- Run Tests ---

if [[ "$SKIP_TESTS" == "false" && "$ROLLBACK" == "false" ]]; then
  print_header "Running Tests Before Deployment"

  if [[ -f "./run_tests.sh" ]]; then
    print_info "Running tests for $DEPLOY_ENV environment..."

    TEST_ARGS="--type all"
    if [[ -n "$COMPONENT" ]]; then
      TEST_ARGS="$TEST_ARGS --component $COMPONENT"
    fi

    if ! bash "$PROJECT_ROOT/run_tests.sh" $TEST_ARGS; then
      print_error "Tests failed!"
      if [[ "$FORCE" != "true" ]]; then
        print_info "Exiting. Run with --force to deploy anyway."
        exit 1
      else
        print_warning "Continuing deployment despite test failures (--force)"
      fi
    else
      print_success "Tests passed!"
    fi
  else
    print_warning "run_tests.sh not found, skipping tests"
  fi
fi

# --- Build Application ---

if [[ "$SKIP_BUILD" == "false" && "$ROLLBACK" == "false" ]]; then
  print_header "Building Application"

  if [[ -f "$PROJECT_ROOT/scripts/build.sh" ]]; then
    print_info "Building application for $DEPLOY_ENV environment..."

    BUILD_ARGS="--env $DEPLOY_ENV"
    if [[ -n "$COMPONENT" ]]; then
      BUILD_ARGS="$BUILD_ARGS --component $COMPONENT"
    fi

    if ! bash "$PROJECT_ROOT/build.sh" $BUILD_ARGS; then
      print_error "Build failed!"
      exit 1
    else
      print_success "Build completed successfully!"
    fi
  else
    print_warning "build.sh not found, using existing build artifacts"
  fi
fi

# --- Prepare Deployment ---

print_header "Preparing Deployment"

# Create timestamp for this deployment
TIMESTAMP=$(date +%Y%m%d%H%M%S)
RELEASE_DIR="$REMOTE_DIR/releases/$TIMESTAMP"

# Check if we're doing a rollback
if [[ "$ROLLBACK" == "true" ]]; then
  print_info "Preparing rollback..."

  # Get list of releases
  if [[ "$DRY_RUN" == "false" ]]; then
    RELEASES=$(run_remote "ls -1t $REMOTE_DIR/releases" | head -n 10)

    if [[ -z "$RELEASES" ]]; then
      print_error "No previous releases found for rollback"
      exit 1
    fi

    # Get current and previous release
    CURRENT_RELEASE=$(run_remote "readlink $REMOTE_DIR/current" | xargs basename)

    # Find the release before the current one
    PREVIOUS_RELEASE=""
    for release in $RELEASES; do
      if [[ "$release" != "$CURRENT_RELEASE" ]]; then
        PREVIOUS_RELEASE="$release"
        break
      fi
    done

    if [[ -z "$PREVIOUS_RELEASE" ]]; then
      print_error "No previous release found for rollback"
      exit 1
    fi

    print_info "Rolling back from $CURRENT_RELEASE to $PREVIOUS_RELEASE"
    RELEASE_DIR="$REMOTE_DIR/releases/$PREVIOUS_RELEASE"
  else
    print_info "Dry run: Would roll back to previous release"
    RELEASE_DIR="$REMOTE_DIR/releases/previous"
  fi
else
  print_info "Preparing new deployment..."

  # Create release directory structure
  if [[ "$DRY_RUN" == "false" ]]; then
    run_remote "mkdir -p $RELEASE_DIR"
    run_remote "mkdir -p $RELEASE_DIR/backend"
    run_remote "mkdir -p $RELEASE_DIR/web-frontend"
    run_remote "mkdir -p $RELEASE_DIR/config"
    run_remote "mkdir -p $RELEASE_DIR/logs"
  else
    print_info "Dry run: Would create release directory $RELEASE_DIR"
  fi
fi

# --- Deploy Components ---

deploy_backend() {
  print_header "Deploying Backend"

  if [[ ! -d "code/backend" ]]; then
    print_warning "Backend directory not found, skipping"
    return
  fi

  if [[ "$ROLLBACK" == "true" ]]; then
    print_info "Rollback: Using previous backend deployment"
    return
  fi

  # Determine backend build artifacts
  BACKEND_BUILD=""
  if [[ -d "code/backend/dist" ]]; then
    BACKEND_BUILD="code/backend/dist"
  elif [[ -d "code/backend/build" ]]; then
    BACKEND_BUILD="code/backend/build"
  else
    print_warning "No backend build artifacts found"
    BACKEND_BUILD="code/backend"
  fi

  # Transfer backend files
  if [[ "$DRY_RUN" == "false" ]]; then
    print_info "Transferring backend files..."
    transfer_files "$BACKEND_BUILD" "$RELEASE_DIR/backend"
    transfer_files "code/backend/requirements.txt" "$RELEASE_DIR/backend/"

    # Transfer configuration files
    if [[ -d "config" ]]; then
      transfer_files "config" "$RELEASE_DIR/"
    fi

    # Set up virtual environment on remote server
    print_info "Setting up Python virtual environment..."
    run_remote "cd $RELEASE_DIR && python3 -m venv venv"
    run_remote "cd $RELEASE_DIR && source venv/bin/activate && pip install -r backend/requirements.txt"

    # Run database migrations if needed (Alembic - backend is FastAPI)
    if [[ "$DEPLOY_ENV" != "development" ]]; then
      print_info "Running database migrations..."
      run_remote "cd $RELEASE_DIR && source venv/bin/activate && cd backend && alembic upgrade head"
    fi
  else
    print_info "Dry run: Would transfer backend files and set up environment"
  fi

  print_success "Backend deployment prepared"
}

deploy_web_frontend() {
  print_header "Deploying Web Frontend"

  if [[ ! -d "web-frontend" ]]; then
    print_warning "Web frontend directory not found, skipping"
    return
  fi

  if [[ "$ROLLBACK" == "true" ]]; then
    print_info "Rollback: Using previous web frontend deployment"
    return
  fi

  # Determine web frontend build artifacts
  WEB_BUILD=""
  if [[ -d "web-frontend/dist" ]]; then
    WEB_BUILD="web-frontend/dist"
  elif [[ -d "web-frontend/build" ]]; then
    WEB_BUILD="web-frontend/build"
  else
    print_warning "No web frontend build artifacts found"
    WEB_BUILD="web-frontend"
  fi

  # Transfer web frontend files
  if [[ "$DRY_RUN" == "false" ]]; then
    print_info "Transferring web frontend files..."
    transfer_files "$WEB_BUILD/" "$RELEASE_DIR/web-frontend/"
  else
    print_info "Dry run: Would transfer web frontend files"
  fi

  print_success "Web frontend deployment prepared"
}

# Deploy each component
for component in "${COMPONENTS[@]}"; do
  case "$component" in
    backend)
      deploy_backend
      ;;
    web-frontend)
      deploy_web_frontend
      ;;
    *)
      print_warning "Unknown component: $component, skipping"
      ;;
  esac
done

# --- Activate Deployment ---

print_header "Activating Deployment"

if [[ "$DRY_RUN" == "false" ]]; then
  # Create shared directories if they don't exist
  run_remote "mkdir -p $REMOTE_DIR/shared/logs"
  run_remote "mkdir -p $REMOTE_DIR/shared/uploads"
  run_remote "mkdir -p $REMOTE_DIR/shared/tmp"

  # Link shared directories
  run_remote "ln -sf $REMOTE_DIR/shared/logs $RELEASE_DIR/logs"
  run_remote "ln -sf $REMOTE_DIR/shared/uploads $RELEASE_DIR/uploads"
  run_remote "ln -sf $REMOTE_DIR/shared/tmp $RELEASE_DIR/tmp"

  # Deploy based on strategy
  if [[ "$DEPLOYMENT_STRATEGY" == "blue-green" ]]; then
    print_info "Using blue-green deployment strategy..."

    # Determine current color (blue or green)
    CURRENT_COLOR="blue"
    if run_remote "[ -L $REMOTE_DIR/current ] && [ \$(readlink $REMOTE_DIR/current | grep -c blue) -gt 0 ]"; then
      CURRENT_COLOR="blue"
      NEW_COLOR="green"
    else
      CURRENT_COLOR="green"
      NEW_COLOR="blue"
    fi

    print_info "Current deployment is $CURRENT_COLOR, new deployment will be $NEW_COLOR"

    # Create color-specific directory
    run_remote "mkdir -p $REMOTE_DIR/$NEW_COLOR"
    run_remote "rm -rf $REMOTE_DIR/$NEW_COLOR/*"
    run_remote "cp -R $RELEASE_DIR/* $REMOTE_DIR/$NEW_COLOR/"

    # Update configuration if needed
    if [[ "$USE_DOCKER" == "true" ]]; then
      print_info "Updating Docker configuration..."
      transfer_files "$DOCKER_COMPOSE_FILE" "$REMOTE_DIR/$NEW_COLOR/"
      run_remote "cd $REMOTE_DIR/$NEW_COLOR && docker-compose -f $(basename $DOCKER_COMPOSE_FILE) up -d"
    else
      # Update web server configuration
      if [[ -n "$WEB_SERVER_CONFIG" ]]; then
        print_info "Updating web server configuration..."
        run_remote "sudo cp $REMOTE_DIR/$NEW_COLOR/config/nginx/$DEPLOY_ENV.conf $WEB_SERVER_CONFIG"
        run_remote "sudo ln -sf $WEB_SERVER_CONFIG $WEB_SERVER_ENABLED"
      fi

      # Update application server configuration
      if [[ -n "$APP_SERVER_CONFIG" ]]; then
        print_info "Updating application server configuration..."
        run_remote "sudo cp $REMOTE_DIR/$NEW_COLOR/config/systemd/$DEPLOY_ENV.service $APP_SERVER_CONFIG"
        run_remote "sudo systemctl daemon-reload"
      fi
    fi

    # Switch to new deployment
    print_info "Switching to new deployment..."
    run_remote "ln -sfn $REMOTE_DIR/$NEW_COLOR $REMOTE_DIR/current"

    # Restart services
    if [[ "$USE_DOCKER" != "true" ]]; then
      print_info "Restarting services..."
      run_remote "sudo systemctl restart $(basename $APP_SERVER_CONFIG)"
      run_remote "sudo systemctl restart $WEB_SERVER"
    fi

    print_info "Waiting for health check..."
    sleep 5

    # Verify deployment
    if run_remote "curl -s -o /dev/null -w '%{http_code}' http://localhost/health" | grep -q "200"; then
      print_success "Deployment health check passed"
    else
      print_error "Deployment health check failed"

      if [[ "$ROLLBACK" != "true" ]]; then
        print_warning "Rolling back to previous deployment..."
        run_remote "ln -sfn $REMOTE_DIR/$CURRENT_COLOR $REMOTE_DIR/current"

        if [[ "$USE_DOCKER" != "true" ]]; then
          run_remote "sudo systemctl restart $(basename $APP_SERVER_CONFIG)"
          run_remote "sudo systemctl restart $WEB_SERVER"
        fi

        print_error "Deployment failed and rolled back to previous version"
        exit 1
      fi
    fi
  else
    # Simple direct deployment
    print_info "Using direct deployment strategy..."

    # Backup current deployment if it exists
    if run_remote "[ -L $REMOTE_DIR/current ]"; then
      print_info "Backing up current deployment..."
      run_remote "cp -R $(run_remote "readlink $REMOTE_DIR/current") $REMOTE_DIR/previous"
    fi

    # Update current symlink
    print_info "Updating current symlink..."
    run_remote "ln -sfn $RELEASE_DIR $REMOTE_DIR/current"

    # Update configuration if needed
    if [[ "$USE_DOCKER" == "true" ]]; then
      print_info "Updating Docker configuration..."
      transfer_files "$DOCKER_COMPOSE_FILE" "$REMOTE_DIR/current/"
      run_remote "cd $REMOTE_DIR/current && docker-compose -f $(basename $DOCKER_COMPOSE_FILE) up -d"
    else
      # Update web server configuration
      if [[ -n "$WEB_SERVER_CONFIG" ]]; then
        print_info "Updating web server configuration..."
        run_remote "sudo cp $REMOTE_DIR/current/config/nginx/$DEPLOY_ENV.conf $WEB_SERVER_CONFIG"
        run_remote "sudo ln -sf $WEB_SERVER_CONFIG $WEB_SERVER_ENABLED"
      fi

      # Update application server configuration
      if [[ -n "$APP_SERVER_CONFIG" ]]; then
        print_info "Updating application server configuration..."
        run_remote "sudo cp $REMOTE_DIR/current/config/systemd/$DEPLOY_ENV.service $APP_SERVER_CONFIG"
        run_remote "sudo systemctl daemon-reload"
      fi

      # Restart services
      print_info "Restarting services..."
      run_remote "sudo systemctl restart $(basename $APP_SERVER_CONFIG)"
      run_remote "sudo systemctl restart $WEB_SERVER"
    fi
  fi

  # Clean up old releases
  print_info "Cleaning up old releases..."
  run_remote "cd $REMOTE_DIR/releases && ls -1t | tail -n +$((KEEP_RELEASES + 1)) | xargs -I {} rm -rf {}"

  print_success "Deployment activated successfully!"
else
  print_info "Dry run: Would activate deployment and restart services"
fi

# --- Generate Deployment Report ---

print_header "Generating Deployment Report"

REPORT_FILE="$LOG_DIR/deploy-report-$TIMESTAMP.html"

# Create report HTML file
cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AlphaMind Deployment Report</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      line-height: 1.6;
      margin: 0;
      padding: 20px;
      color: #333;
    }
    h1, h2, h3 {
      color: #2c3e50;
    }
    .container {
      max-width: 1200px;
      margin: 0 auto;
    }
    .summary-box {
      background-color: #f8f9fa;
      border-radius: 5px;
      padding: 15px;
      margin-bottom: 20px;
      border-left: 5px solid #3498db;
    }
    .success {
      border-left-color: #2ecc71;
    }
    .warning {
      border-left-color: #f39c12;
    }
    .error {
      border-left-color: #e74c3c;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
    }
    th, td {
      padding: 12px 15px;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }
    th {
      background-color: #f2f2f2;
    }
    tr:hover {
      background-color: #f5f5f5;
    }
    .timestamp {
      color: #7f8c8d;
      font-size: 0.9em;
      margin-top: 5px;
    }
    pre {
      background-color: #f8f9fa;
      padding: 10px;
      border-radius: 5px;
      overflow-x: auto;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>AlphaMind Deployment Report</h1>
    <div class="timestamp">Generated on $(date)</div>

    <div class="summary-box success">
      <h2>Deployment Summary</h2>
      <p>
        <strong>Environment:</strong> ${DEPLOY_ENV}<br>
        <strong>Components:</strong> ${COMPONENTS[*]}<br>
        <strong>Timestamp:</strong> ${TIMESTAMP}<br>
        <strong>Remote host:</strong> ${REMOTE_HOST}<br>
        <strong>Remote directory:</strong> ${REMOTE_DIR}<br>
        <strong>Deployment strategy:</strong> ${DEPLOYMENT_STRATEGY}<br>
        <strong>Status:</strong> ${ROLLBACK:+Rollback}${ROLLBACK:-Success}
      </p>
    </div>

    <h2>Deployed Components</h2>

    <table>
      <tr>
        <th>Component</th>
        <th>Status</th>
        <th>Location</th>
      </tr>
EOF

# Add component details
for component in "${COMPONENTS[@]}"; do
  echo "      <tr>" >> "$REPORT_FILE"
  echo "        <td>$component</td>" >> "$REPORT_FILE"
  echo "        <td class=\"success\">Deployed</td>" >> "$REPORT_FILE"
  echo "        <td>$REMOTE_DIR/current/$component</td>" >> "$REPORT_FILE"
  echo "      </tr>" >> "$REPORT_FILE"
done

# Close HTML
cat >> "$REPORT_FILE" << EOF
    </table>

    <h2>Deployment Log</h2>
    <pre>
$(tail -n 50 "$LOG_FILE")
    </pre>

    <h2>Next Steps</h2>
    <p>
      The application has been successfully deployed to the ${DEPLOY_ENV} environment.
      You can access it at the following URL:
    </p>
    <p>
      <strong>URL:</strong> $(case "$DEPLOY_ENV" in production) echo "https://alphamind.example.com";; staging) echo "https://staging.alphamind.example.com";; *) echo "http://localhost:8000";; esac)
    </p>
    <p>
      If you need to roll back to the previous version, run:
      <pre>./deploy.sh --env ${DEPLOY_ENV} --rollback</pre>
    </p>
  </div>
</body>
</html>
EOF

print_success "Deployment report generated: $REPORT_FILE"

# Open the report in a browser if possible
if command_exists xdg-open; then
  xdg-open "$REPORT_FILE" &>/dev/null &
elif command_exists open; then
  open "$REPORT_FILE" &>/dev/null &
else
  print_info "To view the deployment report, open: $REPORT_FILE"
fi

print_header "Deployment Complete"
print_success "Deployment to $DEPLOY_ENV environment completed successfully!"
print_info "Deployment log: $LOG_FILE"
print_info "Deployment report: $REPORT_FILE"

exit 0
