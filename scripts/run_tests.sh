#!/bin/bash
# AlphaMind - Automated Testing Pipeline
# This script provides a comprehensive testing framework for the AlphaMind project
# It runs unit tests, integration tests, and end-to-end tests with detailed reporting

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

# Ensure venv is deactivated on exit
_venv_cleanup() { deactivate 2>/dev/null || true; }
trap _venv_cleanup EXIT

# Define project root directory (assuming the script is in the project root)
PROJECT_ROOT="$(pwd)"

# Parse command line arguments
TEST_TYPE="all"
VERBOSE=false
COVERAGE=true
REPORT_DIR="$PROJECT_ROOT/test-reports"
PARALLEL=false
FAIL_FAST=false
COMPONENT=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --type)
      TEST_TYPE="$2"
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
    --no-coverage)
      COVERAGE=false
      shift
      ;;
    --report-dir)
      REPORT_DIR="$2"
      shift 2
      ;;
    --parallel)
      PARALLEL=true
      shift
      ;;
    --fail-fast)
      FAIL_FAST=true
      shift
      ;;
    --help)
      echo "Usage: ./run_tests.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --type TYPE            Test type: unit, integration, e2e, or all (default: all)"
      echo "  --component COMPONENT  Specific component to test (e.g., ai_models, risk_system)"
      echo "  --verbose              Enable verbose output"
      echo "  --no-coverage          Disable coverage reporting"
      echo "  --report-dir DIR       Directory for test reports (default: ./test-reports)"
      echo "  --parallel             Run tests in parallel"
      echo "  --fail-fast            Stop on first failure"
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

print_header "Setting Up Test Environment"

# Create reports directory if it doesn't exist
mkdir -p "$REPORT_DIR"
mkdir -p "$REPORT_DIR/unit"
mkdir -p "$REPORT_DIR/integration"
mkdir -p "$REPORT_DIR/e2e"
mkdir -p "$REPORT_DIR/coverage"

# Check for Python virtual environment
if [[ -d "venv" ]]; then
  print_info "Activating Python virtual environment..."
  source venv/bin/activate
else
  print_warning "Python virtual environment not found. Running setup_environment.sh..."
  if [[ -f "./setup_environment.sh" ]]; then
    bash "$PROJECT_ROOT/setup_environment.sh" --type testing
    source venv/bin/activate
  else
    print_error "setup_environment.sh not found. Please set up the environment first."
    exit 1
  fi
fi

# Check for required testing tools
print_info "Checking for required testing tools..."

# Python testing tools
if ! command_exists pytest; then
  print_info "Installing pytest and related packages..."
  pip install pytest pytest-cov pytest-html pytest-xdist pytest-benchmark
fi

# JavaScript testing tools
if [[ -d "web-frontend" || -d "mobile-frontend" ]]; then
  if ! command_exists node; then
    print_error "Node.js not found. Please install Node.js first."
    exit 1
  fi

  if [[ -d "web-frontend" ]]; then
    cd web-frontend
    if [[ ! -d "node_modules" ]]; then
      print_info "Installing web frontend dependencies..."
      if [[ -f "yarn.lock" ]]; then
        yarn install
      else
        npm install
      fi
    fi
    cd "$PROJECT_ROOT"
  fi

  if [[ -d "mobile-frontend" ]]; then
    cd mobile-frontend
    if [[ ! -d "node_modules" ]]; then
      print_info "Installing mobile frontend dependencies..."
      if [[ -f "yarn.lock" ]]; then
        yarn install
      else
        npm install
      fi
    fi
    cd "$PROJECT_ROOT"
  fi
fi

print_success "Test environment setup complete"

# --- Test Configuration ---

print_header "Configuring Tests"

# Set up pytest arguments
PYTEST_ARGS="--tb=short"

if [[ "$VERBOSE" == "true" ]]; then
  PYTEST_ARGS="$PYTEST_ARGS -v"
fi

if [[ "$COVERAGE" == "true" ]]; then
  PYTEST_ARGS="$PYTEST_ARGS --cov --cov-report=html:$REPORT_DIR/coverage/html --cov-report=xml:$REPORT_DIR/coverage/coverage.xml"
fi

if [[ "$PARALLEL" == "true" ]]; then
  PYTEST_ARGS="$PYTEST_ARGS -n auto"
fi

if [[ "$FAIL_FAST" == "true" ]]; then
  PYTEST_ARGS="$PYTEST_ARGS -x"
fi

# Set up component-specific test paths
if [[ -n "$COMPONENT" ]]; then
  if [[ -d "code/backend/$COMPONENT" ]]; then
    BACKEND_TEST_PATH="code/backend/$COMPONENT"
  elif [[ -d "$COMPONENT" ]]; then
    BACKEND_TEST_PATH="$COMPONENT"
  else
    print_error "Component directory not found: $COMPONENT"
    exit 1
  fi
else
  BACKEND_TEST_PATH="code/backend"
fi

print_info "Test configuration:"
echo "  Test type: $TEST_TYPE"
if [[ -n "$COMPONENT" ]]; then
  echo "  Component: $COMPONENT"
fi
echo "  Coverage reporting: $COVERAGE"
echo "  Report directory: $REPORT_DIR"
echo "  Parallel execution: $PARALLEL"
echo "  Fail fast: $FAIL_FAST"

# --- Run Unit Tests ---

run_unit_tests() {
  print_header "Running Unit Tests"

  # Backend unit tests
  if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "unit" ]]; then
    print_info "Running backend unit tests..."

    UNIT_TEST_ARGS="$PYTEST_ARGS --html=$REPORT_DIR/unit/backend-report.html --self-contained-html"

    if [[ -n "$COMPONENT" ]]; then
      print_info "Testing component: $COMPONENT"
      if [[ -d "$BACKEND_TEST_PATH/tests/unit" ]]; then
        python -m pytest $UNIT_TEST_ARGS "$BACKEND_TEST_PATH/tests/unit"
      elif [[ -d "$BACKEND_TEST_PATH/tests" ]]; then
        python -m pytest $UNIT_TEST_ARGS "$BACKEND_TEST_PATH/tests"
      else
        print_warning "No backend unit tests found for component"
      fi
    elif [[ -d "code/backend/tests/unit" ]]; then
      python -m pytest $UNIT_TEST_ARGS code/backend/tests/unit
    elif [[ -d "code/backend/tests" ]]; then
      python -m pytest $UNIT_TEST_ARGS code/backend/tests
    else
      print_warning "No backend unit tests found"
    fi

    print_success "Backend unit tests completed"
  fi

  # Web frontend unit tests
  if [[ ("$TEST_TYPE" == "all" || "$TEST_TYPE" == "unit") && -d "web-frontend" && (-z "$COMPONENT" || "$COMPONENT" == "web-frontend") ]]; then
    print_info "Running web frontend unit tests..."

    cd web-frontend
    if [[ -f "package.json" ]]; then
      if grep -q "\"test\"" package.json; then
        if [[ -f "yarn.lock" ]]; then
          CI=true yarn test --coverage --reporters=default --reporters=jest-junit
        else
          CI=true npm test -- --coverage --reporters=default --reporters=jest-junit
        fi

        # Copy test reports
        if [[ -d "coverage" ]]; then
          mkdir -p "$REPORT_DIR/coverage/web-frontend"
          cp -r coverage/* "$REPORT_DIR/coverage/web-frontend/"
        fi
        if [[ -f "junit.xml" ]]; then
          cp junit.xml "$REPORT_DIR/unit/web-frontend-junit.xml"
        fi

        print_success "Web frontend unit tests completed"
      else
        print_warning "No test script found in web-frontend/package.json"
      fi
    else
      print_warning "No package.json found in web-frontend directory"
    fi
    cd "$PROJECT_ROOT"
  fi

  # Mobile frontend unit tests
  if [[ ("$TEST_TYPE" == "all" || "$TEST_TYPE" == "unit") && -d "mobile-frontend" && (-z "$COMPONENT" || "$COMPONENT" == "mobile-frontend") ]]; then
    print_info "Running mobile frontend unit tests..."

    cd mobile-frontend
    if [[ -f "package.json" ]]; then
      if grep -q "\"test\"" package.json; then
        if [[ -f "yarn.lock" ]]; then
          CI=true yarn test --coverage --reporters=default --reporters=jest-junit
        else
          CI=true npm test -- --coverage --reporters=default --reporters=jest-junit
        fi

        # Copy test reports
        if [[ -d "coverage" ]]; then
          mkdir -p "$REPORT_DIR/coverage/mobile-frontend"
          cp -r coverage/* "$REPORT_DIR/coverage/mobile-frontend/"
        fi
        if [[ -f "junit.xml" ]]; then
          cp junit.xml "$REPORT_DIR/unit/mobile-frontend-junit.xml"
        fi

        print_success "Mobile frontend unit tests completed"
      else
        print_warning "No test script found in mobile-frontend/package.json"
      fi
    else
      print_warning "No package.json found in mobile-frontend directory"
    fi
    cd "$PROJECT_ROOT"
  fi
}

# --- Run Integration Tests ---

run_integration_tests() {
  print_header "Running Integration Tests"

  # Backend integration tests
  if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration" ]]; then
    print_info "Running backend integration tests..."

    INTEGRATION_TEST_ARGS="$PYTEST_ARGS --html=$REPORT_DIR/integration/backend-report.html --self-contained-html"

    if [[ -n "$COMPONENT" ]]; then
      print_info "Testing component: $COMPONENT"
      if [[ -d "$BACKEND_TEST_PATH/tests/integration" ]]; then
        python -m pytest $INTEGRATION_TEST_ARGS "$BACKEND_TEST_PATH/tests/integration"
      else
        print_warning "No backend integration tests found for component"
      fi
    elif [[ -d "code/backend/tests/integration" ]]; then
      python -m pytest $INTEGRATION_TEST_ARGS code/backend/tests/integration
    else
      print_warning "No backend integration tests found"
    fi

    print_success "Backend integration tests completed"
  fi

  # Web frontend integration tests
  if [[ ("$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration") && -d "web-frontend" && (-z "$COMPONENT" || "$COMPONENT" == "web-frontend") ]]; then
    print_info "Running web frontend integration tests..."

    cd web-frontend
    if [[ -f "package.json" ]]; then
      if grep -q "\"test:integration\"" package.json; then
        if [[ -f "yarn.lock" ]]; then
          yarn test:integration
        else
          npm run test:integration
        fi

        # Copy test reports if they exist
        if [[ -f "integration-results.xml" ]]; then
          cp integration-results.xml "$REPORT_DIR/integration/web-frontend-results.xml"
        fi

        print_success "Web frontend integration tests completed"
      else
        print_warning "No integration test script found in web-frontend/package.json"
      fi
    else
      print_warning "No package.json found in web-frontend directory"
    fi
    cd "$PROJECT_ROOT"
  fi

  # Mobile frontend integration tests
  if [[ ("$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration") && -d "mobile-frontend" && (-z "$COMPONENT" || "$COMPONENT" == "mobile-frontend") ]]; then
    print_info "Running mobile frontend integration tests..."

    cd mobile-frontend
    if [[ -f "package.json" ]]; then
      if grep -q "\"test:integration\"" package.json; then
        if [[ -f "yarn.lock" ]]; then
          yarn test:integration
        else
          npm run test:integration
        fi

        # Copy test reports if they exist
        if [[ -f "integration-results.xml" ]]; then
          cp integration-results.xml "$REPORT_DIR/integration/mobile-frontend-results.xml"
        fi

        print_success "Mobile frontend integration tests completed"
      else
        print_warning "No integration test script found in mobile-frontend/package.json"
      fi
    else
      print_warning "No package.json found in mobile-frontend directory"
    fi
    cd "$PROJECT_ROOT"
  fi
}

# --- Run End-to-End Tests ---

run_e2e_tests() {
  print_header "Running End-to-End Tests"

  # Check if we should run E2E tests
  if [[ "$TEST_TYPE" != "all" && "$TEST_TYPE" != "e2e" ]]; then
    return
  fi

  # Check if component filtering allows E2E tests
  if [[ -n "$COMPONENT" && "$COMPONENT" != "e2e" && "$COMPONENT" != "web-frontend" && "$COMPONENT" != "mobile-frontend" ]]; then
    print_info "Skipping E2E tests for component: $COMPONENT"
    return
  fi

  # Backend E2E tests
  print_info "Running backend E2E tests..."

  E2E_TEST_ARGS="$PYTEST_ARGS --html=$REPORT_DIR/e2e/backend-report.html --self-contained-html"

  if [[ -d "code/backend/tests/e2e" ]]; then
    python -m pytest $E2E_TEST_ARGS code/backend/tests/e2e
    print_success "Backend E2E tests completed"
  else
    print_warning "No backend E2E tests found"
  fi

  # Web frontend E2E tests
  if [[ -d "web-frontend" && (-z "$COMPONENT" || "$COMPONENT" == "web-frontend" || "$COMPONENT" == "e2e") ]]; then
    print_info "Running web frontend E2E tests..."

    cd web-frontend
    if [[ -f "package.json" ]]; then
      if grep -q "\"test:e2e\"" package.json; then
        if [[ -f "yarn.lock" ]]; then
          yarn test:e2e
        else
          npm run test:e2e
        fi

        # Copy test reports if they exist
        if [[ -d "cypress/reports" ]]; then
          mkdir -p "$REPORT_DIR/e2e/web-frontend"
          cp -r cypress/reports/* "$REPORT_DIR/e2e/web-frontend/"
        fi

        print_success "Web frontend E2E tests completed"
      else
        print_warning "No E2E test script found in web-frontend/package.json"
      fi
    else
      print_warning "No package.json found in web-frontend directory"
    fi
    cd "$PROJECT_ROOT"
  fi

  # Mobile frontend E2E tests
  if [[ -d "mobile-frontend" && (-z "$COMPONENT" || "$COMPONENT" == "mobile-frontend" || "$COMPONENT" == "e2e") ]]; then
    print_info "Running mobile frontend E2E tests..."

    cd mobile-frontend
    if [[ -f "package.json" ]]; then
      if grep -q "\"test:e2e\"" package.json; then
        if [[ -f "yarn.lock" ]]; then
          yarn test:e2e
        else
          npm run test:e2e
        fi

        # Copy test reports if they exist
        if [[ -d "e2e/reports" ]]; then
          mkdir -p "$REPORT_DIR/e2e/mobile-frontend"
          cp -r e2e/reports/* "$REPORT_DIR/e2e/mobile-frontend/"
        fi

        print_success "Mobile frontend E2E tests completed"
      else
        print_warning "No E2E test script found in mobile-frontend/package.json"
      fi
    else
      print_warning "No package.json found in mobile-frontend directory"
    fi
    cd "$PROJECT_ROOT"
  fi
}

# --- Generate Test Report Summary ---

generate_test_summary() {
  print_header "Generating Test Summary"

  SUMMARY_FILE="$REPORT_DIR/test-summary.html"

  # Create summary HTML file
  cat > "$SUMMARY_FILE" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AlphaMind Test Summary</title>
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
    .report-link {
      color: #3498db;
      text-decoration: none;
    }
    .report-link:hover {
      text-decoration: underline;
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
    <h1>AlphaMind Test Summary</h1>
    <div class="timestamp">Generated on $(date)</div>

    <div class="summary-box">
      <h2>Test Run Summary</h2>
      <p>
        <strong>Test Type:</strong> ${TEST_TYPE}<br>
        <strong>Component:</strong> ${COMPONENT:-"All components"}<br>
        <strong>Coverage Reporting:</strong> ${COVERAGE}<br>
        <strong>Report Directory:</strong> ${REPORT_DIR}
      </p>
    </div>

    <h2>Test Reports</h2>

    <h3>Unit Tests</h3>
    <table>
      <tr>
        <th>Component</th>
        <th>Status</th>
        <th>Report</th>
      </tr>
EOF

  # Add unit test reports
  if [[ -f "$REPORT_DIR/unit/backend-report.html" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Backend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"unit/backend-report.html\" class=\"report-link\">View Report</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  if [[ -f "$REPORT_DIR/unit/web-frontend-junit.xml" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Web Frontend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"unit/web-frontend-junit.xml\" class=\"report-link\">View Report</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  if [[ -f "$REPORT_DIR/unit/mobile-frontend-junit.xml" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Mobile Frontend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"unit/mobile-frontend-junit.xml\" class=\"report-link\">View Report</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  # Continue with integration tests
  cat >> "$SUMMARY_FILE" << EOF
    </table>

    <h3>Integration Tests</h3>
    <table>
      <tr>
        <th>Component</th>
        <th>Status</th>
        <th>Report</th>
      </tr>
EOF

  # Add integration test reports
  if [[ -f "$REPORT_DIR/integration/backend-report.html" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Backend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"integration/backend-report.html\" class=\"report-link\">View Report</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  if [[ -f "$REPORT_DIR/integration/web-frontend-results.xml" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Web Frontend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"integration/web-frontend-results.xml\" class=\"report-link\">View Report</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  if [[ -f "$REPORT_DIR/integration/mobile-frontend-results.xml" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Mobile Frontend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"integration/mobile-frontend-results.xml\" class=\"report-link\">View Report</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  # Continue with E2E tests
  cat >> "$SUMMARY_FILE" << EOF
    </table>

    <h3>End-to-End Tests</h3>
    <table>
      <tr>
        <th>Component</th>
        <th>Status</th>
        <th>Report</th>
      </tr>
EOF

  # Add E2E test reports
  if [[ -f "$REPORT_DIR/e2e/backend-report.html" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Backend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"e2e/backend-report.html\" class=\"report-link\">View Report</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  if [[ -d "$REPORT_DIR/e2e/web-frontend" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Web Frontend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"e2e/web-frontend/\" class=\"report-link\">View Reports</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  if [[ -d "$REPORT_DIR/e2e/mobile-frontend" ]]; then
    echo "      <tr>" >> "$SUMMARY_FILE"
    echo "        <td>Mobile Frontend</td>" >> "$SUMMARY_FILE"
    echo "        <td>Completed</td>" >> "$SUMMARY_FILE"
    echo "        <td><a href=\"e2e/mobile-frontend/\" class=\"report-link\">View Reports</a></td>" >> "$SUMMARY_FILE"
    echo "      </tr>" >> "$SUMMARY_FILE"
  fi

  # Add coverage section
  cat >> "$SUMMARY_FILE" << EOF
    </table>

    <h3>Coverage Reports</h3>
EOF

  if [[ "$COVERAGE" == "true" ]]; then
    echo "    <p>Coverage reports are available <a href=\"coverage/html/index.html\" class=\"report-link\">here</a>.</p>" >> "$SUMMARY_FILE"
  else
    echo "    <p>Coverage reporting was disabled for this test run.</p>" >> "$SUMMARY_FILE"
  fi

  # Close HTML
  cat >> "$SUMMARY_FILE" << EOF
  </div>
</body>
</html>
EOF

  print_success "Test summary generated: $SUMMARY_FILE"

  # Open the summary in a browser if possible
  if command_exists xdg-open; then
    xdg-open "$SUMMARY_FILE" &>/dev/null &
  elif command_exists open; then
    open "$SUMMARY_FILE" &>/dev/null &
  else
    print_info "To view the test summary, open: $SUMMARY_FILE"
  fi
}

# --- Run Tests ---

# Run tests based on the specified type
if [[ "$TEST_TYPE" == "unit" || "$TEST_TYPE" == "all" ]]; then
  run_unit_tests
fi

if [[ "$TEST_TYPE" == "integration" || "$TEST_TYPE" == "all" ]]; then
  run_integration_tests
fi

if [[ "$TEST_TYPE" == "e2e" || "$TEST_TYPE" == "all" ]]; then
  run_e2e_tests
fi

# Generate test summary
generate_test_summary

# --- Cleanup ---

# Deactivate virtual environment
deactivate

print_header "Test Run Complete"
print_success "All tests completed successfully!"
print_info "Test reports are available in: $REPORT_DIR"
print_info "Test summary: $REPORT_DIR/test-summary.html"
