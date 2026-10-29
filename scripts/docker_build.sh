#!/bin/bash
# AlphaMind - Docker Image Build Script

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

IMAGE_NAME="alphamind"
TAG="latest"
BUILD_ARGS=""
NO_CACHE=false
PUSH=false
COMPONENT="all"
REGISTRY=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --name)
      IMAGE_NAME="$2"
      shift 2
      ;;
    --tag)
      TAG="$2"
      shift 2
      ;;
    --build-arg)
      BUILD_ARGS="$BUILD_ARGS --build-arg $2"
      shift 2
      ;;
    --no-cache)
      NO_CACHE=true
      shift
      ;;
    --push)
      PUSH=true
      shift
      ;;
    --registry)
      REGISTRY="$2"
      shift 2
      ;;
    --component)
      COMPONENT="$2"
      shift 2
      ;;
    --help)
      echo "Usage: ./docker_build.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --name NAME            Base image name (default: alphamind)"
      echo "  --tag TAG              Image tag (default: latest)"
      echo "  --build-arg ARG        Pass a build-arg to Docker (can be used multiple times)"
      echo "  --no-cache             Do not use cache when building the image"
      echo "  --push                 Push the image to the registry after building"
      echo "  --registry REGISTRY    Registry prefix for the image (e.g., myregistry.io/myorg)"
      echo "  --component COMPONENT  Component to build: backend, web-frontend, or all (default: all)"
      echo "  --help                 Show this help message"
      exit 0
      ;;
    *)
      print_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate component value
if [[ "$COMPONENT" != "all" && "$COMPONENT" != "backend" && "$COMPONENT" != "web-frontend" ]]; then
  print_error "Invalid component: $COMPONENT. Supported: all, backend, web-frontend."
  exit 1
fi

# --- Prerequisite Check ---

print_header "Checking Prerequisites"

if ! command_exists docker; then
  print_error "Docker command not found. Please install Docker."
  exit 1
fi

# Verify Docker daemon is running
if ! docker info >/dev/null 2>&1; then
  print_error "Docker daemon is not running. Please start Docker."
  exit 1
fi

# --- Build Component Images ---

build_backend_image() {
  print_header "Building Backend Docker Image"

  if [[ ! -f "code/backend/Dockerfile" ]]; then
    print_warning "code/backend/Dockerfile not found, skipping backend image build."
    return 0
  fi

  local image_base="${IMAGE_NAME}-backend"
  if [[ -n "$REGISTRY" ]]; then
    image_base="${REGISTRY}/${image_base}"
  fi
  local full_tag="${image_base}:${TAG}"

  local cache_option=""
  if [[ "$NO_CACHE" == "true" ]]; then
    cache_option="--no-cache"
  fi

  print_info "Building image: $full_tag"
  # Build context is the backend dir (its Dockerfile uses context-relative COPY).
  # shellcheck disable=SC2086
  docker build -f code/backend/Dockerfile -t "$full_tag" $cache_option $BUILD_ARGS "$PROJECT_ROOT/code/backend"

  if [[ "$PUSH" == "true" ]]; then
    print_info "Pushing image: $full_tag"
    docker push "$full_tag"
    print_success "Backend image pushed: $full_tag"
  fi

  print_success "Backend image built: $full_tag"
}

build_web_frontend_image() {
  print_header "Building Web Frontend Docker Image"

  if [[ ! -f "web-frontend/Dockerfile" ]]; then
    print_warning "web-frontend/Dockerfile not found, skipping web frontend image build."
    return 0
  fi

  local image_base="${IMAGE_NAME}-web"
  if [[ -n "$REGISTRY" ]]; then
    image_base="${REGISTRY}/${image_base}"
  fi
  local full_tag="${image_base}:${TAG}"

  local cache_option=""
  if [[ "$NO_CACHE" == "true" ]]; then
    cache_option="--no-cache"
  fi

  print_info "Building image: $full_tag"
  # Build context is the web-frontend dir (context-relative COPY in its Dockerfile).
  # shellcheck disable=SC2086
  docker build -f web-frontend/Dockerfile -t "$full_tag" $cache_option $BUILD_ARGS "$PROJECT_ROOT/web-frontend"

  if [[ "$PUSH" == "true" ]]; then
    print_info "Pushing image: $full_tag"
    docker push "$full_tag"
    print_success "Web frontend image pushed: $full_tag"
  fi

  print_success "Web frontend image built: $full_tag"
}

# --- Main Execution ---

print_header "Starting Docker Build Process"

if [[ "$COMPONENT" == "all" || "$COMPONENT" == "backend" ]]; then
  build_backend_image
fi

if [[ "$COMPONENT" == "all" || "$COMPONENT" == "web-frontend" ]]; then
  build_web_frontend_image
fi

print_success "Docker build process complete."
