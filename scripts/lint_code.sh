#!/bin/bash
# AlphaMind - Code Quality and Linting Automation
# This script provides comprehensive linting and code quality checks for the AlphaMind project
# It supports Python, JavaScript, TypeScript, and other languages used in the project

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

# Initialize path arrays early to avoid unbound variable errors
PYTHON_PATHS=()
JS_PATHS=()

_venv_cleanup() { deactivate 2>/dev/null || true; }
trap _venv_cleanup EXIT

# Define project root directory (assuming the script is in the project root)
PROJECT_ROOT="$(pwd)"

# Parse command line arguments
LINT_TYPE="all"
FIX=false
VERBOSE=false
REPORT_DIR="$PROJECT_ROOT/lint-reports"
COMPONENT=""
STRICT=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --type)
      LINT_TYPE="$2"
      shift 2
      ;;
    --component)
      COMPONENT="$2"
      shift 2
      ;;
    --fix)
      FIX=true
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
    --strict)
      STRICT=true
      shift
      ;;
    --help)
      echo "Usage: ./lint_code.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --type TYPE            Lint type: python, js, all (default: all)"
      echo "  --component COMPONENT  Specific component to lint (e.g., backend, web-frontend)"
      echo "  --fix                  Automatically fix issues where possible"
      echo "  --verbose              Enable verbose output"
      echo "  --report-dir DIR       Directory for lint reports (default: ./lint-reports)"
      echo "  --strict               Fail on any lint error (strict mode)"
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

# --- Environment Setup ---

print_header "Setting Up Lint Environment"

# Create reports directory if it doesn't exist
mkdir -p "$REPORT_DIR"
mkdir -p "$REPORT_DIR/python"
mkdir -p "$REPORT_DIR/js"
mkdir -p "$REPORT_DIR/css"

# Check for Python virtual environment
if [[ -d "venv" ]]; then
  print_info "Activating Python virtual environment..."
  source venv/bin/activate
else
  print_warning "Python virtual environment not found. Running setup_environment.sh..."
  if [[ -f "./setup_environment.sh" ]]; then
    bash "$PROJECT_ROOT/setup_environment.sh" --type development
    source venv/bin/activate
  else
    print_error "setup_environment.sh not found. Please set up the environment first."
    exit 1
  fi
fi

# Check for required linting tools
print_info "Checking for required linting tools..."

# Python linting tools
if [[ "$LINT_TYPE" == "all" || "$LINT_TYPE" == "python" ]]; then
  for tool in black flake8 mypy isort pylint; do
    if ! command_exists $tool; then
      print_info "Installing $tool..."
      pip install $tool
    fi
  done
fi

# JavaScript/TypeScript linting tools
if [[ "$LINT_TYPE" == "all" || "$LINT_TYPE" == "js" ]]; then
  if ! command_exists node; then
    print_error "Node.js not found. Please install Node.js first."
    exit 1
  fi

  if ! command_exists eslint; then
    print_info "Installing ESLint globally..."
    npm install -g eslint
  fi

  if ! command_exists prettier; then
    print_info "Installing Prettier globally..."
    npm install -g prettier
  fi

  if ! command_exists stylelint; then
    print_info "Installing Stylelint globally..."
    npm install -g stylelint
  fi
fi

print_success "Lint environment setup complete"

# --- Lint Configuration ---

print_header "Configuring Linters"

# Set up component-specific paths
if [[ -n "$COMPONENT" ]]; then
  if [[ "$COMPONENT" == "backend" ]]; then
    PYTHON_PATHS=("code/backend" "code/ai_models")
    JS_PATHS=()
  elif [[ "$COMPONENT" == "web-frontend" ]]; then
    PYTHON_PATHS=()
    JS_PATHS=("web-frontend")
  elif [[ "$COMPONENT" == "mobile-frontend" ]]; then
    PYTHON_PATHS=()
    JS_PATHS=("mobile-frontend")
  elif [[ -d "$COMPONENT" ]]; then
    PYTHON_PATHS=("$COMPONENT")
    JS_PATHS=("$COMPONENT")
  else
    print_error "Component directory not found: $COMPONENT"
    exit 1
  fi
else
  PYTHON_PATHS=("code/backend" "code/ai_models")
  JS_PATHS=("web-frontend" "mobile-frontend")
fi

print_info "Lint configuration:"
echo "  Lint type: $LINT_TYPE"
if [[ -n "$COMPONENT" ]]; then
  echo "  Component: $COMPONENT"
fi
echo "  Auto-fix: $FIX"
echo "  Report directory: $REPORT_DIR"
echo "  Strict mode: $STRICT"

# --- Run Python Linters ---

run_python_linters() {
  print_header "Running Python Linters"

  if [[ "$LINT_TYPE" != "all" && "$LINT_TYPE" != "python" ]]; then
    return
  fi

  if [[ ${#PYTHON_PATHS[@]} -eq 0 ]]; then
    print_info "No Python paths to lint"
    return
  fi

  PYTHON_FILES=()
  for path in "${PYTHON_PATHS[@]}"; do
    if [[ -d "$path" ]]; then
      while IFS= read -r -d '' file; do
        PYTHON_FILES+=("$file")
      done < <(find "$path" -name "*.py" -type f -print0)
    elif [[ -f "$path" && "$path" == *.py ]]; then
      PYTHON_FILES+=("$path")
    fi
  done

  if [[ ${#PYTHON_FILES[@]} -eq 0 ]]; then
    print_info "No Python files found to lint"
    return
  fi

  print_info "Found ${#PYTHON_FILES[@]} Python files to lint"

  # Run Black (code formatter)
  print_info "Running Black code formatter..."
  if [[ "$FIX" == "true" ]]; then
    black "${PYTHON_FILES[@]}" 2>&1 | tee "$REPORT_DIR/python/black.log"
    print_success "Black formatting completed"
  else
    black --check "${PYTHON_FILES[@]}" 2>&1 | tee "$REPORT_DIR/python/black.log" || true
    print_info "Black check completed (use --fix to apply formatting)"
  fi

  # Run isort (import sorter)
  print_info "Running isort import sorter..."
  if [[ "$FIX" == "true" ]]; then
    isort "${PYTHON_FILES[@]}" 2>&1 | tee "$REPORT_DIR/python/isort.log"
    print_success "isort completed"
  else
    isort --check-only "${PYTHON_FILES[@]}" 2>&1 | tee "$REPORT_DIR/python/isort.log" || true
    print_info "isort check completed (use --fix to apply sorting)"
  fi

  # Run Flake8 (linter)
  print_info "Running Flake8 linter..."
  flake8 "${PYTHON_FILES[@]}" --output-file="$REPORT_DIR/python/flake8.log" || true
  print_info "Flake8 completed, report saved to $REPORT_DIR/python/flake8.log"

  # Run MyPy (type checker)
  print_info "Running MyPy type checker..."
  mypy "${PYTHON_FILES[@]}" 2>&1 | tee "$REPORT_DIR/python/mypy.log" || true
  print_info "MyPy completed, report saved to $REPORT_DIR/python/mypy.log"

  # Run Pylint (comprehensive linter)
  print_info "Running Pylint..."
  pylint "${PYTHON_FILES[@]}" 2>&1 | tee "$REPORT_DIR/python/pylint.log" || true
  print_info "Pylint completed, report saved to $REPORT_DIR/python/pylint.log"

  print_success "Python linting completed"
}

# --- Run JavaScript/TypeScript Linters ---

run_js_linters() {
  print_header "Running JavaScript/TypeScript Linters"

  if [[ "$LINT_TYPE" != "all" && "$LINT_TYPE" != "js" ]]; then
    return
  fi

  if [[ ${#JS_PATHS[@]} -eq 0 ]]; then
    print_info "No JavaScript/TypeScript paths to lint"
    return
  fi

  for path in "${JS_PATHS[@]}"; do
    if [[ ! -d "$path" ]]; then
      print_warning "Directory not found: $path"
      continue
    fi

    print_info "Linting $path..."

    cd "$path" || { print_warning "Cannot cd into $path, skipping"; continue; }

    # Check if package.json exists
    if [[ ! -f "package.json" ]]; then
      print_warning "No package.json found in $path"
      cd "$PROJECT_ROOT"
      continue
    fi

    # Install dependencies if node_modules doesn't exist
    if [[ ! -d "node_modules" ]]; then
      print_info "Installing dependencies..."
      if [[ -f "yarn.lock" ]]; then
        yarn install
      else
        npm install
      fi
    fi

    # Run ESLint
    print_info "Running ESLint..."
    if [[ -f ".eslintrc.js" || -f ".eslintrc.json" || -f ".eslintrc.yml" || -f ".eslintrc" ]]; then
      if [[ "$FIX" == "true" ]]; then
        npx eslint --fix . 2>&1 | tee "$REPORT_DIR/js/eslint-$path.log" || true
        print_success "ESLint fix completed"
      else
        npx eslint . 2>&1 | tee "$REPORT_DIR/js/eslint-$path.log" || true
        print_info "ESLint check completed (use --fix to apply fixes)"
      fi
    else
      print_warning "No ESLint configuration found in $path"
    fi

    # Run Prettier
    print_info "Running Prettier..."
    if [[ -f ".prettierrc.js" || -f ".prettierrc.json" || -f ".prettierrc.yml" || -f ".prettierrc" ]]; then
      if [[ "$FIX" == "true" ]]; then
        npx prettier --write . 2>&1 | tee "$REPORT_DIR/js/prettier-$path.log" || true
        print_success "Prettier formatting completed"
      else
        npx prettier --check . 2>&1 | tee "$REPORT_DIR/js/prettier-$path.log" || true
        print_info "Prettier check completed (use --fix to apply formatting)"
      fi
    else
      print_warning "No Prettier configuration found in $path"
    fi

    # Run Stylelint for CSS files
    print_info "Running Stylelint for CSS..."
    if [[ -f ".stylelintrc.js" || -f ".stylelintrc.json" || -f ".stylelintrc.yml" || -f ".stylelintrc" ]]; then
      if [[ "$FIX" == "true" ]]; then
        npx stylelint "**/*.css" "**/*.scss" "**/*.less" --fix 2>&1 | tee "$REPORT_DIR/css/stylelint-$path.log" || true
        print_success "Stylelint fix completed"
      else
        npx stylelint "**/*.css" "**/*.scss" "**/*.less" 2>&1 | tee "$REPORT_DIR/css/stylelint-$path.log" || true
        print_info "Stylelint check completed (use --fix to apply fixes)"
      fi
    else
      print_warning "No Stylelint configuration found in $path"
    fi

    # Run TypeScript compiler check if tsconfig.json exists
    if [[ -f "tsconfig.json" ]]; then
      print_info "Running TypeScript compiler check..."
      npx tsc --noEmit 2>&1 | tee "$REPORT_DIR/js/tsc-$path.log" || true
      print_info "TypeScript check completed"
    fi

    # Run project-specific lint script if it exists
    if grep -q "\"lint\"" package.json; then
      print_info "Running project-specific lint script..."
      if [[ -f "yarn.lock" ]]; then
        yarn lint 2>&1 | tee "$REPORT_DIR/js/project-lint-$path.log" || true
      else
        npm run lint 2>&1 | tee "$REPORT_DIR/js/project-lint-$path.log" || true
      fi
      print_info "Project-specific lint completed"
    fi

    cd "$PROJECT_ROOT"
  done

  print_success "JavaScript/TypeScript linting completed"
}

# --- Generate Lint Report Summary ---

generate_lint_summary() {
  print_header "Generating Lint Summary"

  SUMMARY_FILE="$REPORT_DIR/lint-summary.html"

  # Create summary HTML file
  cat > "$SUMMARY_FILE" << EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AlphaMind Lint Summary</title>
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
    <h1>AlphaMind Lint Summary</h1>
    <div class="timestamp">Generated on $(date)</div>

    <div class="summary-box">
      <h2>Lint Run Summary</h2>
      <p>
        <strong>Lint Type:</strong> ${LINT_TYPE}<br>
        <strong>Component:</strong> ${COMPONENT:-"All components"}<br>
        <strong>Auto-fix:</strong> ${FIX}<br>
        <strong>Report Directory:</strong> ${REPORT_DIR}
      </p>
    </div>
EOF

  # Add Python lint reports
  if [[ "$LINT_TYPE" == "all" || "$LINT_TYPE" == "python" ]]; then
    cat >> "$SUMMARY_FILE" << EOF

    <h2>Python Linting Results</h2>

    <h3>Black (Code Formatter)</h3>
EOF

    if [[ -f "$REPORT_DIR/python/black.log" ]]; then
      echo "    <pre>" >> "$SUMMARY_FILE"
      cat "$REPORT_DIR/python/black.log" | head -n 20 >> "$SUMMARY_FILE"
      if [[ $(wc -l < "$REPORT_DIR/python/black.log") -gt 20 ]]; then
        echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
      fi
      echo "    </pre>" >> "$SUMMARY_FILE"
      echo "    <p><a href=\"python/black.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
    else
      echo "    <p>No Black log found</p>" >> "$SUMMARY_FILE"
    fi

    cat >> "$SUMMARY_FILE" << EOF

    <h3>isort (Import Sorter)</h3>
EOF

    if [[ -f "$REPORT_DIR/python/isort.log" ]]; then
      echo "    <pre>" >> "$SUMMARY_FILE"
      cat "$REPORT_DIR/python/isort.log" | head -n 20 >> "$SUMMARY_FILE"
      if [[ $(wc -l < "$REPORT_DIR/python/isort.log") -gt 20 ]]; then
        echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
      fi
      echo "    </pre>" >> "$SUMMARY_FILE"
      echo "    <p><a href=\"python/isort.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
    else
      echo "    <p>No isort log found</p>" >> "$SUMMARY_FILE"
    fi

    cat >> "$SUMMARY_FILE" << EOF

    <h3>Flake8 (Linter)</h3>
EOF

    if [[ -f "$REPORT_DIR/python/flake8.log" ]]; then
      echo "    <pre>" >> "$SUMMARY_FILE"
      cat "$REPORT_DIR/python/flake8.log" | head -n 20 >> "$SUMMARY_FILE"
      if [[ $(wc -l < "$REPORT_DIR/python/flake8.log") -gt 20 ]]; then
        echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
      fi
      echo "    </pre>" >> "$SUMMARY_FILE"
      echo "    <p><a href=\"python/flake8.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
    else
      echo "    <p>No Flake8 log found</p>" >> "$SUMMARY_FILE"
    fi

    cat >> "$SUMMARY_FILE" << EOF

    <h3>MyPy (Type Checker)</h3>
EOF

    if [[ -f "$REPORT_DIR/python/mypy.log" ]]; then
      echo "    <pre>" >> "$SUMMARY_FILE"
      cat "$REPORT_DIR/python/mypy.log" | head -n 20 >> "$SUMMARY_FILE"
      if [[ $(wc -l < "$REPORT_DIR/python/mypy.log") -gt 20 ]]; then
        echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
      fi
      echo "    </pre>" >> "$SUMMARY_FILE"
      echo "    <p><a href=\"python/mypy.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
    else
      echo "    <p>No MyPy log found</p>" >> "$SUMMARY_FILE"
    fi

    cat >> "$SUMMARY_FILE" << EOF

    <h3>Pylint (Comprehensive Linter)</h3>
EOF

    if [[ -f "$REPORT_DIR/python/pylint.log" ]]; then
      echo "    <pre>" >> "$SUMMARY_FILE"
      cat "$REPORT_DIR/python/pylint.log" | head -n 20 >> "$SUMMARY_FILE"
      if [[ $(wc -l < "$REPORT_DIR/python/pylint.log") -gt 20 ]]; then
        echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
      fi
      echo "    </pre>" >> "$SUMMARY_FILE"
      echo "    <p><a href=\"python/pylint.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
    else
      echo "    <p>No Pylint log found</p>" >> "$SUMMARY_FILE"
    fi
  fi

  # Add JavaScript/TypeScript lint reports
  if [[ "$LINT_TYPE" == "all" || "$LINT_TYPE" == "js" ]]; then
    cat >> "$SUMMARY_FILE" << EOF

    <h2>JavaScript/TypeScript Linting Results</h2>
EOF

    # List all JS paths
    for path in "${JS_PATHS[@]}"; do
      if [[ -d "$path" ]]; then
        cat >> "$SUMMARY_FILE" << EOF

    <h3>${path}</h3>

    <h4>ESLint</h4>
EOF

        if [[ -f "$REPORT_DIR/js/eslint-$path.log" ]]; then
          echo "    <pre>" >> "$SUMMARY_FILE"
          cat "$REPORT_DIR/js/eslint-$path.log" | head -n 20 >> "$SUMMARY_FILE"
          if [[ $(wc -l < "$REPORT_DIR/js/eslint-$path.log") -gt 20 ]]; then
            echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
          fi
          echo "    </pre>" >> "$SUMMARY_FILE"
          echo "    <p><a href=\"js/eslint-$path.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
        else
          echo "    <p>No ESLint log found for $path</p>" >> "$SUMMARY_FILE"
        fi

        cat >> "$SUMMARY_FILE" << EOF

    <h4>Prettier</h4>
EOF

        if [[ -f "$REPORT_DIR/js/prettier-$path.log" ]]; then
          echo "    <pre>" >> "$SUMMARY_FILE"
          cat "$REPORT_DIR/js/prettier-$path.log" | head -n 20 >> "$SUMMARY_FILE"
          if [[ $(wc -l < "$REPORT_DIR/js/prettier-$path.log") -gt 20 ]]; then
            echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
          fi
          echo "    </pre>" >> "$SUMMARY_FILE"
          echo "    <p><a href=\"js/prettier-$path.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
        else
          echo "    <p>No Prettier log found for $path</p>" >> "$SUMMARY_FILE"
        fi

        cat >> "$SUMMARY_FILE" << EOF

    <h4>TypeScript Compiler</h4>
EOF

        if [[ -f "$REPORT_DIR/js/tsc-$path.log" ]]; then
          echo "    <pre>" >> "$SUMMARY_FILE"
          cat "$REPORT_DIR/js/tsc-$path.log" | head -n 20 >> "$SUMMARY_FILE"
          if [[ $(wc -l < "$REPORT_DIR/js/tsc-$path.log") -gt 20 ]]; then
            echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
          fi
          echo "    </pre>" >> "$SUMMARY_FILE"
          echo "    <p><a href=\"js/tsc-$path.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
        else
          echo "    <p>No TypeScript compiler log found for $path</p>" >> "$SUMMARY_FILE"
        fi

        cat >> "$SUMMARY_FILE" << EOF

    <h4>CSS Linting (Stylelint)</h4>
EOF

        if [[ -f "$REPORT_DIR/css/stylelint-$path.log" ]]; then
          echo "    <pre>" >> "$SUMMARY_FILE"
          cat "$REPORT_DIR/css/stylelint-$path.log" | head -n 20 >> "$SUMMARY_FILE"
          if [[ $(wc -l < "$REPORT_DIR/css/stylelint-$path.log") -gt 20 ]]; then
            echo "    ... (see full log for more details)" >> "$SUMMARY_FILE"
          fi
          echo "    </pre>" >> "$SUMMARY_FILE"
          echo "    <p><a href=\"css/stylelint-$path.log\" class=\"report-link\">View Full Log</a></p>" >> "$SUMMARY_FILE"
        else
          echo "    <p>No Stylelint log found for $path</p>" >> "$SUMMARY_FILE"
        fi
      fi
    done
  fi

  # Close HTML
  cat >> "$SUMMARY_FILE" << EOF

    <h2>Next Steps</h2>
    <p>
      To fix linting issues automatically, run the script with the <code>--fix</code> flag:
      <pre>./lint_code.sh --fix</pre>
    </p>
    <p>
      For more detailed information about specific linting rules and how to fix common issues, refer to:
      <ul>
        <li><a href="https://black.readthedocs.io/en/stable/" target="_blank">Black documentation</a></li>
        <li><a href="https://flake8.pycqa.org/en/latest/" target="_blank">Flake8 documentation</a></li>
        <li><a href="https://mypy.readthedocs.io/en/stable/" target="_blank">MyPy documentation</a></li>
        <li><a href="https://eslint.org/docs/user-guide/getting-started" target="_blank">ESLint documentation</a></li>
        <li><a href="https://prettier.io/docs/en/index.html" target="_blank">Prettier documentation</a></li>
      </ul>
    </p>
  </div>
</body>
</html>
EOF

  print_success "Lint summary generated: $SUMMARY_FILE"

  # Open the summary in a browser if possible
  if command_exists xdg-open; then
    xdg-open "$SUMMARY_FILE" &>/dev/null &
  elif command_exists open; then
    open "$SUMMARY_FILE" &>/dev/null &
  else
    print_info "To view the lint summary, open: $SUMMARY_FILE"
  fi
}

# --- Run Linters ---

# Run linters based on the specified type
if [[ "$LINT_TYPE" == "python" || "$LINT_TYPE" == "all" ]]; then
  run_python_linters
fi

if [[ "$LINT_TYPE" == "js" || "$LINT_TYPE" == "all" ]]; then
  run_js_linters
fi

# Generate lint summary
generate_lint_summary

# --- Cleanup ---

# Deactivate virtual environment
deactivate

print_header "Lint Run Complete"
print_success "All linting completed successfully!"
print_info "Lint reports are available in: $REPORT_DIR"
print_info "Lint summary: $REPORT_DIR/lint-summary.html"

# Check if we should fail in strict mode
if [[ "$STRICT" == "true" ]]; then
  ERRORS_FOUND=false

  # Check Python lint logs for errors
  if [[ -f "$REPORT_DIR/python/flake8.log" && -s "$REPORT_DIR/python/flake8.log" ]]; then
    ERRORS_FOUND=true
  fi

  if [[ -f "$REPORT_DIR/python/mypy.log" && -s "$REPORT_DIR/python/mypy.log" ]]; then
    ERRORS_FOUND=true
  fi

  # Check JS lint logs for errors
  for path in "${JS_PATHS[@]}"; do
    if [[ -f "$REPORT_DIR/js/eslint-$path.log" && -s "$REPORT_DIR/js/eslint-$path.log" ]]; then
      ERRORS_FOUND=true
    fi
  done

  if [[ "$ERRORS_FOUND" == "true" ]]; then
    print_error "Lint errors found and strict mode is enabled. Exiting with error."
    exit 1
  fi
fi

exit 0
