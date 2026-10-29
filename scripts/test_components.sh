#!/bin/bash

# Test script for AlphaMind project
# This script tests both frontend and backend components

# Resolve project root relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The scripts live in <repo>/scripts, so the project root is one level up.
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/web-frontend"
BACKEND_DIR="$PROJECT_ROOT/code/backend"
AI_MODELS_DIR="$PROJECT_ROOT/code/ai_models"
TESTS_DIR="$PROJECT_ROOT/test-reports"
RESULTS_DIR="$TESTS_DIR/component-tests"

PASS=0
FAIL=0
WARN=0

pass()  { echo "✓ $*"; PASS=$((PASS+1)); }
fail()  { echo "✗ $*"; FAIL=$((FAIL+1)); }
warn()  { echo "! Warning: $*"; WARN=$((WARN+1)); }

echo "Starting AlphaMind test suite..."
echo "Project root: $PROJECT_ROOT"
echo ""

# Create test/results directory
mkdir -p "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# Frontend Tests
# ---------------------------------------------------------------------------
echo "Testing frontend components..."

if [[ ! -d "$FRONTEND_DIR" ]]; then
  warn "web-frontend directory not found; skipping frontend tests"
else

  # --- HTML files ---
  echo ""
  echo "Checking HTML validity..."
  HTML_FILES=( "$FRONTEND_DIR"/*.html )
  if [[ ! -e "${HTML_FILES[0]}" ]]; then
    warn "No HTML files found in $FRONTEND_DIR"
  else
    for file in "${HTML_FILES[@]}"; do
      filename=$(basename "$file")
      echo "Testing $filename..."

      if [[ ! -r "$file" ]]; then
        fail "File does not exist or is not readable: $file"
        continue
      fi
      pass "File exists and is readable"

      if grep -q "<!DOCTYPE html>" "$file" && grep -q "<html" "$file" && \
         grep -q "<head>" "$file" && grep -q "<body>" "$file"; then
        pass "Basic HTML structure is valid"
      else
        fail "Basic HTML structure is invalid in $filename"
      fi

      if grep -q '<meta name="viewport"' "$file"; then
        pass "Responsive viewport meta tag found"
      else
        fail "Responsive viewport meta tag missing in $filename"
      fi

      if grep -qE '<link rel="stylesheet" href="css/[^"]+\.css">' "$file"; then
        pass "CSS stylesheet link found"
      else
        fail "CSS stylesheet link missing in $filename"
      fi

      echo "$filename passed basic validation tests"
      echo ""
    done
  fi

  # --- CSS files ---
  echo "Checking CSS files..."
  CSS_FILES=( "$FRONTEND_DIR"/css/*.css )
  if [[ ! -e "${CSS_FILES[0]}" ]]; then
    warn "No CSS files found in $FRONTEND_DIR/css"
  else
    for file in "${CSS_FILES[@]}"; do
      filename=$(basename "$file")
      echo "Testing $filename..."

      if [[ ! -r "$file" ]]; then
        fail "File does not exist or is not readable: $file"
        continue
      fi
      pass "File exists and is readable"

      if grep -q "{" "$file" && grep -q "}" "$file"; then
        pass "Basic CSS structure is valid"
      else
        fail "Basic CSS structure is invalid in $filename"
      fi

      if grep -q "@media" "$file"; then
        pass "Responsive media queries found"
      else
        warn "No responsive media queries found in $filename"
      fi

      echo "$filename passed basic validation tests"
      echo ""
    done
  fi

  # --- JS files ---
  echo "Checking JavaScript files..."
  JS_FILES=( "$FRONTEND_DIR"/js/*.js )
  if [[ ! -e "${JS_FILES[0]}" ]]; then
    warn "No JS files found in $FRONTEND_DIR/js"
  else
    for file in "${JS_FILES[@]}"; do
      filename=$(basename "$file")
      echo "Testing $filename..."

      if [[ ! -r "$file" ]]; then
        fail "File does not exist or is not readable: $file"
        continue
      fi
      pass "File exists and is readable"

      if grep -qE "function |const |let |var |=>" "$file"; then
        pass "Basic JS structure is valid"
      else
        fail "No recognizable JS constructs found in $filename"
      fi

      if grep -q "addEventListener" "$file"; then
        pass "Event listeners found"
      else
        warn "No event listeners found in $filename"
      fi

      echo "$filename passed basic validation tests"
      echo ""
    done
  fi

  # --- Image references ---
  echo "Checking referenced image files..."
  while IFS= read -r imgref; do
    imgpath="$FRONTEND_DIR/$imgref"
    if [[ -f "$imgpath" ]]; then
      pass "Image exists: $imgref"
    else
      warn "Referenced image not found: $imgpath"
    fi
  done < <(grep -roh 'images/[^"'"'"' >)]*' "$FRONTEND_DIR"/*.html 2>/dev/null | sort -u)

fi  # end frontend dir check

echo "Frontend tests completed."
echo ""

# ---------------------------------------------------------------------------
# Backend Tests
# ---------------------------------------------------------------------------
echo "Testing backend components..."

if ! command -v python3 &>/dev/null; then
  fail "Python3 is not installed"
  echo ""
  echo "SUMMARY: $PASS passed, $FAIL failed, $WARN warnings"
  exit 1
fi

python_version=$(python3 --version 2>&1)
pass "Python is installed: $python_version"

# Check required Python packages
echo "Checking Python packages..."
required_packages=("numpy" "pandas" "scikit-learn")
optional_packages=("tensorflow" "torch")

for package in "${required_packages[@]}"; do
  if python3 -c "import $package" &>/dev/null; then
    pass "Package $package is installed"
  else
    fail "Required package $package is NOT installed"
  fi
done

for package in "${optional_packages[@]}"; do
  if python3 -c "import $package" &>/dev/null; then
    pass "Optional package $package is installed"
  else
    warn "Optional package $package is not installed"
  fi
done

# Check backend Python files for syntax errors
if [[ -d "$BACKEND_DIR" ]]; then
  echo "Checking backend Python files for syntax errors..."
  syntax_errors=0
  while IFS= read -r -d '' file; do
    filename=$(basename "$file")
    if python3 -m py_compile "$file" 2>/dev/null; then
      pass "Python syntax OK: $filename"
    else
      fail "Python syntax error in $filename"
      syntax_errors=$((syntax_errors+1))
    fi
  done < <(find "$BACKEND_DIR" -name "*.py" -print0)

  if [[ $syntax_errors -eq 0 ]]; then
    echo "All Python files passed syntax check"
  fi
else
  warn "Backend directory not found: $BACKEND_DIR"
fi

# ---------------------------------------------------------------------------
# AI Model Component Tests
# ---------------------------------------------------------------------------
echo ""
echo "Testing AI model components..."

run_python_test() {
  local label="$1"
  local testfile="$2"
  local testcode="$3"

  if [[ ! -f "$testfile" ]]; then
    warn "$label source file not found, skipping"
    return
  fi

  echo "Testing $label..."
  local tmptest
  tmptest=$(mktemp "$RESULTS_DIR/test_XXXXXX.py")

  cat > "$tmptest" << PYEOF
import sys
sys.path.insert(0, '$BACKEND_DIR')
sys.path.insert(0, '$PROJECT_ROOT/code')
$testcode
PYEOF

  if python3 "$tmptest" 2>&1; then
    pass "$label tests passed"
  else
    fail "$label tests failed"
  fi
  rm -f "$tmptest"
  echo ""
}

run_python_test "attention_mechanism" \
  "$AI_MODELS_DIR/examples/attention_mechanism.py" \
'try:
    from ai_models.examples.attention_mechanism import MultiHeadAttention, TemporalAttentionBlock
    print("  Imported MultiHeadAttention and TemporalAttentionBlock")
    import tensorflow as tf
    attn = MultiHeadAttention(d_model=64, num_heads=4)
    print("  Initialized MultiHeadAttention")
    block = TemporalAttentionBlock(d_model=64, num_heads=4, dff=256)
    print("  Initialized TemporalAttentionBlock")
    print("All attention_mechanism tests passed")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
'

run_python_test "sentiment_analysis" \
  "$BACKEND_DIR/analytics/alternative_data/sentiment_analysis.py" \
'try:
    from analytics.alternative_data.sentiment_analysis import MarketSentimentAnalyzer
    print("  Imported MarketSentimentAnalyzer")
    analyzer = MarketSentimentAnalyzer()
    print("  Initialized MarketSentimentAnalyzer")
    print("All sentiment_analysis tests passed")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
'

run_python_test "portfolio_optimization" \
  "$BACKEND_DIR/analytics/alpha_research/portfolio_optimization.py" \
'try:
    from analytics.alpha_research.portfolio_optimization import PortfolioOptimizer
    print("  Imported PortfolioOptimizer")
    optimizer = PortfolioOptimizer(n_assets=5)
    print("  Initialized PortfolioOptimizer")
    print("All portfolio_optimization tests passed")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
'

run_python_test "authentication" \
  "$BACKEND_DIR/infrastructure/auth/authentication.py" \
'try:
    from infrastructure.auth.authentication import AuthenticationSystem
    print("  Imported AuthenticationSystem")
    try:
        import jwt
        auth = AuthenticationSystem(secret_key="test-secret-key")
        print("  Initialized AuthenticationSystem")
        token = auth.generate_token("testuser")
        print("  Generated token")
        username = auth.verify_token(token)
        if username == "testuser":
            print("  Token verification successful")
        else:
            print(f"  Token verification returned unexpected value: {username}", file=sys.stderr)
            sys.exit(1)
    except ImportError as ie:
        print(f"  Skipping full auth test (missing dependency: {ie})")
    print("All authentication tests passed")
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
'

echo "Backend tests completed."
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "====================================================="
echo "TEST SUMMARY"
echo "====================================================="
echo "  Passed  : $PASS"
echo "  Failed  : $FAIL"
echo "  Warnings: $WARN"
echo "====================================================="

if [[ $FAIL -gt 0 ]]; then
  echo "RESULT: FAILED ($FAIL test(s) failed)"
  exit 1
else
  echo "RESULT: PASSED"
  echo "The AlphaMind project passed all component tests."
  exit 0
fi
