#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "AlphaMind Infrastructure Validation"
echo "================================================"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

print_status() {
    if [ "$1" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

OVERALL_STATUS=0

# ============================================================================
# 1. Check Required Tools
# ============================================================================
echo "[1/6] Checking required tools..."

REQUIRED_TOOLS=("terraform" "kubectl" "ansible" "yamllint" "ansible-lint")
OPTIONAL_TOOLS=("kubeconform" "tflint" "trivy")

for tool in "${REQUIRED_TOOLS[@]}"; do
    if command_exists "$tool"; then
        # `|| true`: head closes the pipe early and newer ansible-core exits non-zero on SIGPIPE
        version=$($tool --version 2>&1 | head -n1 || true)
        print_status 0 "$tool: $version"
    else
        print_status 1 "$tool NOT installed"
        OVERALL_STATUS=1
    fi
done

if command_exists "docker" && docker compose version >/dev/null 2>&1; then
    print_status 0 "docker compose: $(docker compose version 2>&1 | head -n1)"
else
    print_warn "docker compose not available - skipping compose validation"
fi

for tool in "${OPTIONAL_TOOLS[@]}"; do
    if command_exists "$tool"; then
        print_status 0 "$tool available (optional)"
    else
        print_warn "$tool not installed (optional)"
    fi
done
echo ""

# ============================================================================
# 2. Validate Terraform
# ============================================================================
echo "[2/6] Validating Terraform..."

pushd terraform > /dev/null

if terraform fmt -check -recursive > /dev/null 2>&1; then
    print_status 0 "Terraform format check passed"
else
    print_status 1 "Terraform format check failed - run: terraform fmt -recursive"
    OVERALL_STATUS=1
fi

if terraform init -backend=false > /tmp/tf_init.log 2>&1; then
    print_status 0 "Terraform init successful"
else
    print_status 1 "Terraform init failed (see /tmp/tf_init.log)"
    OVERALL_STATUS=1
fi

if terraform validate > /tmp/tf_validate.log 2>&1; then
    print_status 0 "Terraform validate passed"
else
    print_status 1 "Terraform validate failed (see /tmp/tf_validate.log)"
    cat /tmp/tf_validate.log
    OVERALL_STATUS=1
fi

if command_exists "tflint"; then
    if tflint --init > /dev/null 2>&1 && tflint > /tmp/tflint.log 2>&1; then
        print_status 0 "tflint passed"
    else
        print_warn "tflint found issues (see /tmp/tflint.log)"
    fi
fi

popd > /dev/null
echo ""

# ============================================================================
# 3. Validate Kubernetes
# ============================================================================
echo "[3/6] Validating Kubernetes..."

pushd kubernetes > /dev/null

if yamllint base/ > /tmp/k8s_yamllint.log 2>&1; then
    print_status 0 "Kubernetes YAML lint passed"
else
    print_warn "YAML lint warnings (see /tmp/k8s_yamllint.log)"
fi

if kubectl kustomize base > /tmp/k8s_base.yaml 2> /tmp/k8s_kustomize.log; then
    print_status 0 "Kustomize build: base"
    # Offline schema validation (kubectl apply --dry-run needs a reachable API server).
    if command_exists "kubeconform"; then
        if kubeconform -strict -summary -ignore-missing-schemas -schema-location default \
            -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json' \
            /tmp/k8s_base.yaml > /tmp/k8s_kubeconform.log 2>&1; then
            print_status 0 "Kubernetes schema validation passed"
        else
            print_status 1 "Kubernetes schema validation failed (see /tmp/k8s_kubeconform.log)"
            OVERALL_STATUS=1
        fi
    else
        print_warn "kubeconform not installed - skipping schema validation"
    fi
else
    print_status 1 "Kustomize build failed: base (see /tmp/k8s_kustomize.log)"
    OVERALL_STATUS=1
fi

for env in environments/*/; do
    env_name=$(basename "$env")
    if kubectl kustomize "$env" > /dev/null 2>&1; then
        print_status 0 "Kustomize build: $env_name"
    else
        print_status 1 "Kustomize build failed: $env_name"
        OVERALL_STATUS=1
    fi
done

popd > /dev/null
echo ""

# ============================================================================
# 4. Validate Ansible
# ============================================================================
echo "[4/6] Validating Ansible..."

pushd ansible > /dev/null

if [ -f "requirements.yml" ]; then
    if ansible-galaxy collection install -r requirements.yml > /tmp/ansible_collections.log 2>&1; then
        print_status 0 "Ansible collections installed"
    else
        print_warn "Ansible collection install had warnings (see /tmp/ansible_collections.log)"
    fi
fi

if ansible-lint . > /tmp/ansible_lint.log 2>&1; then
    print_status 0 "ansible-lint passed"
else
    print_warn "ansible-lint found issues (see /tmp/ansible_lint.log)"
fi

if ansible-playbook --syntax-check playbooks/main.yml > /tmp/ansible_syntax.log 2>&1; then
    print_status 0 "Ansible syntax check passed"
else
    print_status 1 "Ansible syntax check failed (see /tmp/ansible_syntax.log)"
    OVERALL_STATUS=1
fi

popd > /dev/null
echo ""

# ============================================================================
# 5. Validate Docker Compose
# ============================================================================
echo "[5/6] Validating Docker Compose..."

if command_exists "docker" && docker compose version >/dev/null 2>&1; then
    # The compose file requires secrets via ${VAR:?}; fall back to the example values.
    COMPOSE_ENV_FILE=".env"
    if [ ! -f "$COMPOSE_ENV_FILE" ]; then
        COMPOSE_ENV_FILE=".env.example"
        print_warn ".env not found - validating Compose with .env.example"
    fi
    if docker compose --env-file "$COMPOSE_ENV_FILE" config --quiet > /tmp/compose_validate.log 2>&1; then
        print_status 0 "docker-compose.yml is valid"
    else
        print_status 1 "docker-compose.yml has errors (see /tmp/compose_validate.log)"
        OVERALL_STATUS=1
    fi

    if docker compose --env-file "$COMPOSE_ENV_FILE" -f docker-compose.yml -f docker-compose.override.yml config --quiet > /tmp/compose_override_validate.log 2>&1; then
        print_status 0 "docker-compose.override.yml is valid"
    else
        print_status 1 "docker-compose.override.yml has errors"
        OVERALL_STATUS=1
    fi
else
    print_warn "Skipping Docker Compose validation (docker compose not available)"
fi
echo ""

# ============================================================================
# 6. Secrets Scan
# ============================================================================
echo "[6/6] Scanning for committed secrets..."

if command_exists "trivy"; then
    if trivy config . --exit-code 0 --quiet > /tmp/trivy_secrets.log 2>&1; then
        print_status 0 "Trivy config scan passed"
    else
        print_warn "Trivy found issues (see /tmp/trivy_secrets.log)"
    fi
fi

SECRET_PATTERNS=(
    'password\s*=\s*"[^"]{8,}"'
    'secret\s*=\s*"[^"]{8,}"'
    'api[_-]key\s*=\s*"[^"]{8,}"'
    'BEGIN (RSA|EC|OPENSSH) PRIVATE KEY'
)

SECRETS_FOUND=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -rEi "$pattern" terraform/ kubernetes/ ansible/ 2>/dev/null \
        | grep -v ".example" \
        | grep -v "placeholder" \
        | grep -v "#"; then
        SECRETS_FOUND=1
    fi
done

if [ "$SECRETS_FOUND" -eq 0 ]; then
    print_status 0 "No hardcoded secrets detected"
else
    print_status 1 "Potential secrets found - review output above"
    OVERALL_STATUS=1
fi

echo ""
echo "================================================"
if [ "$OVERALL_STATUS" -eq 0 ]; then
    echo -e "${GREEN}All validations passed!${NC}"
else
    echo -e "${RED}Some validations failed. Review logs above.${NC}"
fi
echo "================================================"

exit "$OVERALL_STATUS"
