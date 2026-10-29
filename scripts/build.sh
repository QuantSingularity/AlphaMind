#!/bin/bash
# AlphaMind - Build Process Optimization
# This script provides an optimized build process for the AlphaMind project
# It supports incremental builds, different configurations, and asset optimization

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

# --- Initialization ---

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# Define project root directory (assuming the script is in the project root)
PROJECT_ROOT="$(pwd)"

# Parse command line arguments
BUILD_ENV="development"
CLEAN_BUILD=false
VERBOSE=false
REPORT_DIR="$PROJECT_ROOT/build-reports"
REPORT_FILE=""
COMPONENT=""
OPTIMIZE=true
CACHE=true
ANALYZE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --env)
      BUILD_ENV="$2"
      shift 2
      ;;
    --component)
      COMPONENT="$2"
      shift 2
      ;;
    --clean)
      CLEAN_BUILD=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --report-dir)
      REPORT_DIR="$2"
      shift 2
      ;;
    --no-optimize)
      OPTIMIZE=false
      shift
      ;;
    --no-cache)
      CACHE=false
      shift
      ;;
    --analyze)
      ANALYZE=true
      shift
      ;;
    --help)
      echo "Usage: ./build.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --env ENV              Build environment: development, staging, production (default: development)"
      echo "  --component COMPONENT  Specific component to build (e.g., backend, web-frontend)"
      echo "  --clean                Perform a clean build (remove previous build artifacts)"
      echo "  --verbose              Enable verbose output"
      echo "  --report-dir DIR       Directory for build reports (default: ./build-reports)"
      echo "  --no-optimize          Disable optimization steps"
      echo "  --no-cache             Disable build caching"
      echo "  --analyze              Generate build analysis reports"
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

print_header "Setting Up Build Environment"

# Create reports directory if it doesn't exist
mkdir -p "$REPORT_DIR"

# Check for Python virtual environment
if [[ -d "venv" ]]; then
  print_info "Activating Python virtual environment..."
  source venv/bin/activate
else
  print_warning "Python virtual environment not found. Running setup_environment.sh..."
  if [[ -f "./setup_environment.sh" ]]; then
    bash "$PROJECT_ROOT/setup_environment.sh" --type "$BUILD_ENV"
    source venv/bin/activate
  else
    print_error "setup_environment.sh not found. Please set up the environment first."
    exit 1
  fi
fi

# Set up build configuration
print_info "Setting up build configuration for $BUILD_ENV environment..."

# Create or update .env file based on environment
if [[ ! -f ".env.$BUILD_ENV" ]]; then
  print_warning ".env.$BUILD_ENV file not found, creating default configuration..."

  case "$BUILD_ENV" in
    development)
      cat > ".env.$BUILD_ENV" << EOF
# AlphaMind Development Environment Configuration
DEBUG=true
LOG_LEVEL=debug
API_URL=http://localhost:8000
DATABASE_URL=postgresql://alphamind:alphamind_password@localhost:5432/alphamind_dev
REDIS_URL=redis://localhost:6379/0
EOF
      ;;
    staging)
      cat > ".env.$BUILD_ENV" << EOF
# AlphaMind Staging Environment Configuration
DEBUG=false
LOG_LEVEL=info
API_URL=https://api-staging.alphamind.example.com
DATABASE_URL=postgresql://alphamind:alphamind_password@db.staging.alphamind.example.com:5432/alphamind_staging
REDIS_URL=redis://cache.staging.alphamind.example.com:6379/0
EOF
      ;;
    production)
      cat > ".env.$BUILD_ENV" << EOF
# AlphaMind Production Environment Configuration
DEBUG=false
LOG_LEVEL=warning
API_URL=https://api.alphamind.example.com
DATABASE_URL=postgresql://alphamind:alphamind_password@db.alphamind.example.com:5432/alphamind_prod
REDIS_URL=redis://cache.alphamind.example.com:6379/0
EOF
      ;;
    *)
      print_error "Unknown environment: $BUILD_ENV"
      exit 1
      ;;
  esac
fi

# Copy environment-specific .env file to .env
cp ".env.$BUILD_ENV" .env
print_success "Environment configuration set up for $BUILD_ENV"

# --- Build Configuration ---

print_header "Configuring Build"

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
  COMPONENTS=("backend" "web-frontend" "mobile-frontend")
fi

print_info "Build configuration:"
echo "  Environment: $BUILD_ENV"
echo "  Components: ${COMPONENTS[*]}"
echo "  Clean build: $CLEAN_BUILD"
echo "  Optimization: $OPTIMIZE"
echo "  Caching: $CACHE"
echo "  Build analysis: $ANALYZE"
echo "  Report directory: $REPORT_DIR"

# --- Build Backend ---

build_backend() {
  print_header "Building Backend"

  if [[ ! -d "code/backend" ]]; then
    print_warning "Backend directory not found, skipping"
    return
  fi

  cd code/backend || exit 1

  # Clean build if requested
  if [[ "$CLEAN_BUILD" == "true" ]]; then
    print_info "Cleaning previous build artifacts..."
    rm -rf build dist *.egg-info
    find . -name "__pycache__" -type d -print0 | xargs -0 rm -rf
  fi

  # Install backend dependencies
  print_info "Installing backend dependencies..."
  pip install -r requirements.txt

  # Build Python package
  print_info "Building Python package..."
  if [[ -f "setup.py" ]]; then
    python setup.py build

    if [[ "$BUILD_ENV" == "production" ]]; then
      print_info "Creating distribution packages..."
      python setup.py sdist bdist_wheel
    fi
  elif [[ -f "pyproject.toml" ]]; then
    pip install build
    python -m build
  else
    print_warning "No setup.py or pyproject.toml found, skipping package build"
  fi

  # Run type checking
  print_info "Running type checking..."
  if command_exists mypy; then
    mypy . --ignore-missing-imports || true
  else
    print_warning "mypy not found, skipping type checking"
  fi

  # Generate API documentation if in production mode
  if [[ "$BUILD_ENV" == "production" ]]; then
    print_info "Generating API documentation..."
    if command_exists sphinx-build && [[ -d "docs" ]]; then
      cd docs
      make html
      cd ..
    else
      print_warning "sphinx-build not found or docs directory missing, skipping documentation generation"
    fi
  fi

  print_success "Backend build completed"
  cd "$PROJECT_ROOT"
}

# --- Build Web Frontend ---

build_web_frontend() {
  print_header "Building Web Frontend"

  if [[ ! -d "web-frontend" ]]; then
    print_warning "Web frontend directory not found, skipping"
    return
  fi

  cd web-frontend

  # Clean build if requested
  if [[ "$CLEAN_BUILD" == "true" ]]; then
    print_info "Cleaning previous build artifacts..."
    rm -rf build dist .cache node_modules/.cache
  fi

  # Install dependencies
  print_info "Installing web frontend dependencies..."
  if [[ -f "yarn.lock" ]]; then
    yarn install --frozen-lockfile
  else
    npm ci
  fi

  # Set up environment variables for the build
  print_info "Setting up environment variables for $BUILD_ENV..."

  # Create or update .env file based on environment
  if [[ -f "../.env.$BUILD_ENV" ]]; then
    cp "../.env.$BUILD_ENV" .env
  fi

  # Add REACT_APP_ prefix to environment variables for React apps
  if [[ -f "package.json" ]] && grep -q "react-scripts" package.json; then
    print_info "Detected React app, preparing environment variables..."

    # Create .env.local file with REACT_APP_ prefixed variables
    if [[ -f ".env" ]]; then
      cat .env | sed 's/^/REACT_APP_/' > .env.local
    fi
  fi

  # Build command and options
  BUILD_CMD=""
  BUILD_OPTS=""

  if [[ -f "package.json" ]]; then
    # Determine build command based on package.json
    if grep -q "\"build:$BUILD_ENV\"" package.json; then
      BUILD_CMD="build:$BUILD_ENV"
    elif grep -q "\"build\"" package.json; then
      BUILD_CMD="build"
    fi

    # Add options based on configuration
    if [[ "$VERBOSE" == "true" ]]; then
      BUILD_OPTS="$BUILD_OPTS --verbose"
    fi

    if [[ "$CACHE" == "false" ]]; then
      BUILD_OPTS="$BUILD_OPTS --no-cache"
    fi

    if [[ "$ANALYZE" == "true" ]]; then
      # Check if webpack-bundle-analyzer is installed
      if ! grep -q "webpack-bundle-analyzer" package.json; then
        print_info "Installing webpack-bundle-analyzer..."
        if [[ -f "yarn.lock" ]]; then
          yarn add --dev webpack-bundle-analyzer
        else
          npm install --save-dev webpack-bundle-analyzer
        fi
      fi

      # Set environment variable for bundle analysis
      export ANALYZE=true
    fi

    # Run the build
    print_info "Building web frontend for $BUILD_ENV environment..."
    if [[ -n "$BUILD_CMD" ]]; then
      if [[ -f "yarn.lock" ]]; then
        run_timed yarn $BUILD_CMD $BUILD_OPTS
      else
        run_timed npm run $BUILD_CMD -- $BUILD_OPTS
      fi
    else
      print_error "No build script found in package.json"
      cd "$PROJECT_ROOT"
      return 1
    fi
  else
    print_error "No package.json found"
    cd "$PROJECT_ROOT"
    return 1
  fi

  # Optimize assets if enabled
  if [[ "$OPTIMIZE" == "true" && "$BUILD_ENV" == "production" ]]; then
    print_info "Optimizing assets..."

    # Check if build output directory exists
    BUILD_DIR=""
    if [[ -d "dist" ]]; then
      BUILD_DIR="dist"
    elif [[ -d "build" ]]; then
      BUILD_DIR="build"
    else
      print_warning "Build output directory not found, skipping optimization"
      cd "$PROJECT_ROOT"
      return
    fi

    # Optimize images
    if command_exists imagemin; then
      print_info "Optimizing images..."
      find "$BUILD_DIR" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" -o -name "*.gif" -o -name "*.svg" \) -exec imagemin {} -o {} \;
    else
      print_warning "imagemin not found, skipping image optimization"
    fi

    # Gzip assets for serving with compression
    print_info "Creating gzipped versions of assets..."
    find "$BUILD_DIR" -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" -o -name "*.json" -o -name "*.svg" \) | while read -r _gf; do gzip -9 -c "$_gf" > "${_gf}.gz"; done
  fi

  print_success "Web frontend build completed"
  cd "$PROJECT_ROOT"
}

# --- Build Mobile Frontend ---

build_mobile_frontend() {
  print_header "Building Mobile Frontend"

  if [[ ! -d "mobile-frontend" ]]; then
    print_warning "Mobile frontend directory not found, skipping"
    return
  fi

  cd mobile-frontend

  # Clean build if requested
  if [[ "$CLEAN_BUILD" == "true" ]]; then
    print_info "Cleaning previous build artifacts..."
    rm -rf build dist android/app/build ios/build

    # For React Native
    if [[ -d "android" && -d "ios" ]]; then
      print_info "Cleaning React Native build cache..."
      rm -rf $TMPDIR/react-* || true
      rm -rf $TMPDIR/metro-* || true
      rm -rf node_modules/.cache
    fi
  fi

  # Install dependencies
  print_info "Installing mobile frontend dependencies..."
  if [[ -f "yarn.lock" ]]; then
    yarn install --frozen-lockfile
  else
    npm ci
  fi

  # Set up environment variables for the build
  print_info "Setting up environment variables for $BUILD_ENV..."

  # Create or update .env file based on environment
  if [[ -f "../.env.$BUILD_ENV" ]]; then
    cp "../.env.$BUILD_ENV" .env
  fi

  # Build command and options
  BUILD_CMD=""
  BUILD_OPTS=""

  if [[ -f "package.json" ]]; then
    # Determine build command based on package.json and environment
    if grep -q "\"build:$BUILD_ENV\"" package.json; then
      BUILD_CMD="build:$BUILD_ENV"
    elif grep -q "\"build\"" package.json; then
      BUILD_CMD="build"
    fi

    # For React Native, use specific platform builds if available
    if [[ -d "android" && -d "ios" ]]; then
      if [[ "$BUILD_ENV" == "production" ]]; then
        if grep -q "\"build:android:release\"" package.json; then
          BUILD_CMD="build:android:release"
        elif grep -q "\"build:ios:release\"" package.json; then
          BUILD_CMD="build:ios:release"
        fi
      else
        if grep -q "\"build:android\"" package.json; then
          BUILD_CMD="build:android"
        elif grep -q "\"build:ios\"" package.json; then
          BUILD_CMD="build:ios"
        fi
      fi
    fi

    # Add options based on configuration
    if [[ "$VERBOSE" == "true" ]]; then
      BUILD_OPTS="$BUILD_OPTS --verbose"
    fi

    # Run the build
    print_info "Building mobile frontend for $BUILD_ENV environment..."
    if [[ -n "$BUILD_CMD" ]]; then
      if [[ -f "yarn.lock" ]]; then
        run_timed yarn $BUILD_CMD $BUILD_OPTS
      else
        run_timed npm run $BUILD_CMD -- $BUILD_OPTS
      fi
    else
      print_warning "No suitable build script found in package.json"

      # For React Native, try direct build commands if no script is found
      if [[ -d "android" ]]; then
        print_info "Attempting direct Android build..."
        cd android
        if [[ "$BUILD_ENV" == "production" ]]; then
          ./gradlew assembleRelease
        else
          ./gradlew assembleDebug
        fi
        cd ..
      fi
    fi
  else
    print_error "No package.json found"
    cd "$PROJECT_ROOT"
    return 1
  fi

  print_success "Mobile frontend build completed"
  cd "$PROJECT_ROOT"
}

# --- Generate Build Report ---

generate_build_report() {
  print_header "Generating Build Report"

  REPORT_FILE="$REPORT_DIR/build-report.html"

  # Create report directory if it doesn't exist
  mkdir -p "$REPORT_DIR"

  # Create report HTML file
  cat > "$REPORT_FILE" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AlphaMind Build Report</title>
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
  </style>
</head>
<body>
  <div class="container">
    <h1>AlphaMind Build Report</h1>
    <div class="timestamp">Generated on $(date)</div>

    <div class="summary-box">
      <h2>Build Summary</h2>
      <p>
        <strong>Environment:</strong> ${BUILD_ENV}<br>
        <strong>Components:</strong> ${COMPONENTS[*]}<br>
        <strong>Clean build:</strong> ${CLEAN_BUILD}<br>
        <strong>Optimization:</strong> ${OPTIMIZE}<br>
        <strong>Caching:</strong> ${CACHE}<br>
        <strong>Build analysis:</strong> ${ANALYZE}
      </p>
    </div>

    <h2>Build Results</h2>

    <table>
      <tr>
        <th>Component</th>
        <th>Status</th>
        <th>Output Location</th>
      </tr>
EOF

  # Add backend build results
  if [[ " ${COMPONENTS[*]} " =~ " backend " ]]; then
    echo "      <tr>" >> "$REPORT_FILE"
    echo "        <td>Backend</td>" >> "$REPORT_FILE"

    if [[ -d "code/backend/dist" ]]; then
      echo "        <td class=\"success\">Success</td>" >> "$REPORT_FILE"
      echo "        <td>backend/dist</td>" >> "$REPORT_FILE"
    elif [[ -d "code/backend/build" ]]; then
      echo "        <td class=\"success\">Success</td>" >> "$REPORT_FILE"
      echo "        <td>backend/build</td>" >> "$REPORT_FILE"
    else
      echo "        <td class=\"warning\">Unknown</td>" >> "$REPORT_FILE"
      echo "        <td>N/A</td>" >> "$REPORT_FILE"
    fi

    echo "      </tr>" >> "$REPORT_FILE"
  fi

  # Add web frontend build results
  if [[ " ${COMPONENTS[*]} " =~ " web-frontend " ]]; then
    echo "      <tr>" >> "$REPORT_FILE"
    echo "        <td>Web Frontend</td>" >> "$REPORT_FILE"

    if [[ -d "web-frontend/dist" ]]; then
      echo "        <td class=\"success\">Success</td>" >> "$REPORT_FILE"
      echo "        <td>web-frontend/dist</td>" >> "$REPORT_FILE"
    elif [[ -d "web-frontend/build" ]]; then
      echo "        <td class=\"success\">Success</td>" >> "$REPORT_FILE"
      echo "        <td>web-frontend/build</td>" >> "$REPORT_FILE"
    else
      echo "        <td class=\"warning\">Unknown</td>" >> "$REPORT_FILE"
      echo "        <td>N/A</td>" >> "$REPORT_FILE"
    fi

    echo "      </tr>" >> "$REPORT_FILE"
  fi

  # Add mobile frontend build results
  if [[ " ${COMPONENTS[*]} " =~ " mobile-frontend " ]]; then
    echo "      <tr>" >> "$REPORT_FILE"
    echo "        <td>Mobile Frontend</td>" >> "$REPORT_FILE"

    if [[ -d "mobile-frontend/android/app/build/outputs/apk" ]]; then
      echo "        <td class=\"success\">Success</td>" >> "$REPORT_FILE"
      echo "        <td>mobile-frontend/android/app/build/outputs/apk</td>" >> "$REPORT_FILE"
    elif [[ -d "mobile-frontend/ios/build" ]]; then
      echo "        <td class=\"success\">Success</td>" >> "$REPORT_FILE"
      echo "        <td>mobile-frontend/ios/build</td>" >> "$REPORT_FILE"
    elif [[ -d "mobile-frontend/dist" ]]; then
      echo "        <td class=\"success\">Success</td>" >> "$REPORT_FILE"
      echo "        <td>mobile-frontend/dist</td>" >> "$REPORT_FILE"
    elif [[ -d "mobile-frontend/build" ]]; then
      echo "        <td class=\"success\">Success</td>" >> "$REPORT_FILE"
      echo "        <td>mobile-frontend/build</td>" >> "$REPORT_FILE"
    else
      echo "        <td class=\"warning\">Unknown</td>" >> "$REPORT_FILE"
      echo "        <td>N/A</td>" >> "$REPORT_FILE"
    fi

    echo "      </tr>" >> "$REPORT_FILE"
  fi

  # Close HTML
  cat >> "$REPORT_FILE" << EOF
    </table>

    <h2>Build Artifacts</h2>

    <p>The following build artifacts were generated:</p>

    <ul>
EOF

  # List backend artifacts
  if [[ " ${COMPONENTS[*]} " =~ " backend " ]]; then
    if [[ -d "code/backend/dist" ]]; then
      echo "      <li><strong>Backend Packages:</strong>" >> "$REPORT_FILE"
      echo "        <ul>" >> "$REPORT_FILE"
      find "code/backend/dist" -type f \( -name "*.whl" -o -name "*.tar.gz" \) | while read -r file; do
        echo "          <li>$(basename "$file")</li>" >> "$REPORT_FILE"
      done
      echo "        </ul>" >> "$REPORT_FILE"
      echo "      </li>" >> "$REPORT_FILE"
    fi

    if [[ -d "code/backend/docs/build/html" ]]; then
      echo "      <li><strong>Backend Documentation:</strong> backend/docs/build/html</li>" >> "$REPORT_FILE"
    fi
  fi

  # List web frontend artifacts
  if [[ " ${COMPONENTS[*]} " =~ " web-frontend " ]]; then
    WEB_BUILD_DIR=""
    if [[ -d "web-frontend/dist" ]]; then
      WEB_BUILD_DIR="web-frontend/dist"
    elif [[ -d "web-frontend/build" ]]; then
      WEB_BUILD_DIR="web-frontend/build"
    fi

    if [[ -n "$WEB_BUILD_DIR" ]]; then
      echo "      <li><strong>Web Frontend Build:</strong> $WEB_BUILD_DIR</li>" >> "$REPORT_FILE"

      # List bundle size if available
      if [[ -f "$WEB_BUILD_DIR/asset-manifest.json" ]]; then
        echo "      <li><strong>Web Frontend Bundle:</strong>" >> "$REPORT_FILE"
        echo "        <ul>" >> "$REPORT_FILE"

        # Find JS and CSS files
        find "$WEB_BUILD_DIR" -type f -name "*.js" -not -path "*/node_modules/*" | sort | while read -r file; do
          size=$(du -h "$file" | cut -f1)
          echo "          <li>$(basename "$file") - $size</li>" >> "$REPORT_FILE"
        done

        find "$WEB_BUILD_DIR" -type f -name "*.css" -not -path "*/node_modules/*" | sort | while read -r file; do
          size=$(du -h "$file" | cut -f1)
          echo "          <li>$(basename "$file") - $size</li>" >> "$REPORT_FILE"
        done

        echo "        </ul>" >> "$REPORT_FILE"
        echo "      </li>" >> "$REPORT_FILE"
      fi
    fi
  fi

  # List mobile frontend artifacts
  if [[ " ${COMPONENTS[*]} " =~ " mobile-frontend " ]]; then
    if [[ -d "mobile-frontend/android/app/build/outputs/apk" ]]; then
      echo "      <li><strong>Android APK:</strong>" >> "$REPORT_FILE"
      echo "        <ul>" >> "$REPORT_FILE"
      find "mobile-frontend/android/app/build/outputs/apk" -type f -name "*.apk" | while read -r file; do
        size=$(du -h "$file" | cut -f1)
        echo "          <li>$(basename "$file") - $size</li>" >> "$REPORT_FILE"
      done
      echo "        </ul>" >> "$REPORT_FILE"
      echo "      </li>" >> "$REPORT_FILE"
    fi

    if [[ -d "mobile-frontend/ios/build" ]]; then
      echo "      <li><strong>iOS Build:</strong> mobile-frontend/ios/build</li>" >> "$REPORT_FILE"
    fi
  fi

  # Close HTML
  cat >> "$REPORT_FILE" << EOF
    </ul>

    <h2>Next Steps</h2>
    <p>
      The build artifacts are now ready for deployment. Use the deployment script to deploy to the ${BUILD_ENV} environment:
      <pre>./deploy.sh --env ${BUILD_ENV}</pre>
    </p>
  </div>
</body>
</html>
EOF

  print_success "Build report generated: $REPORT_FILE"

  # Open the report in a browser if possible
  if command_exists xdg-open; then
    xdg-open "$REPORT_FILE" &>/dev/null &
  elif command_exists open; then
    open "$REPORT_FILE" &>/dev/null &
  else
    print_info "To view the build report, open: $REPORT_FILE"
  fi
}

# --- Run Builds ---

# Run builds based on the specified components
for component in "${COMPONENTS[@]}"; do
  case "$component" in
    backend)
      build_backend
      ;;
    web-frontend)
      build_web_frontend
      ;;
    mobile-frontend)
      build_mobile_frontend
      ;;
    *)
      print_warning "Unknown component: $component, skipping"
      ;;
  esac
done

# Generate build report
generate_build_report

# --- Cleanup ---

# Deactivate virtual environment
deactivate

print_header "Build Complete"
print_success "All builds completed successfully!"
print_info "Build report is available at: $REPORT_FILE"

exit 0
