#!/bin/bash

# =============================================================================
# Tammi QA Agent - Deployment Script (Linux/Unix)
# =============================================================================
# 
# This script provides comprehensive deployment automation for the Tammi QA Agent
# including environment configuration, GitHub Actions setup, and Kubernetes deployment.
#
# Usage:
#   ./scripts/deploy.sh [command] [options]
#
# Commands:
#   env-setup       Setup environment configuration
#   github-setup    Setup GitHub Actions and Secrets
#   k8s-deploy      Deploy to Kubernetes
#   full-deploy     Complete deployment pipeline
#   help           Show this help message
#
# Examples:
#   ./scripts/deploy.sh env-setup --from-env
#   ./scripts/deploy.sh github-setup --interactive
#   ./scripts/deploy.sh k8s-deploy --namespace production
#   ./scripts/deploy.sh full-deploy --environment production
#
# =============================================================================

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/deploy.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/env-config.yaml" ]]; then
        error "env-config.yaml not found. Please run from project root directory"
        exit 1
    fi
    
    # Check if env_deploy.py exists
    if [[ ! -f "$PROJECT_ROOT/scripts/env_deploy.py" ]]; then
        error "scripts/env_deploy.py not found"
        exit 1
    fi
    
    log "Prerequisites check passed"
    
}

# Environment setup
setup_environment() {
    local from_env=false
    local interactive=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --from-env)
                from_env=true
                shift
                ;;
            --interactive)
                interactive=true
                shift
                ;;
            *)
                warn "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    log "Setting up environment configuration..."
    
    cd "$PROJECT_ROOT"
    
    if [[ "$from_env" == true ]]; then
        info "Migrating from .env files..."
        if [[ -f ".env" ]]; then
            python3 scripts/env_deploy.py migrate-from-env --env-file .env --env-local-file .env.local
        else
            error ".env file not found for migration"
            exit 1
        fi
    elif [[ "$interactive" == true ]]; then
        info "Running interactive environment setup..."
        python3 scripts/env_deploy.py audit
        echo
        info "Please review the audit results and update env-config.secret.yaml as needed"
        read -p "Press Enter to continue after updating env-config.secret.yaml..."
    else
        info "Validating current environment configuration..."
        python3 scripts/env_deploy.py audit
    fi
    
    log "Environment setup completed"
}

# GitHub setup
setup_github() {
    local interactive=false
    local use_yaml=true
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interactive)
                interactive=true
                shift
                ;;
            --use-env)
                use_yaml=false
                shift
                ;;
            *)
                warn "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    log "Setting up GitHub Actions and Secrets..."
    
    cd "$PROJECT_ROOT"
    
    # Check GitHub CLI
    if ! command -v gh &> /dev/null; then
        warn "GitHub CLI not found. Installing GitHub CLI is recommended for automatic secret setup"
        info "You can install it from: https://cli.github.com/"
        info "Manual setup instructions will be provided instead"
    fi
    
    # Update GitHub Actions workflow
    info "Updating GitHub Actions workflow..."
    python3 scripts/env_deploy.py sync-github
    
    # Setup GitHub Secrets
    info "Setting up GitHub Secrets..."
    if [[ "$use_yaml" == true ]]; then
        if [[ "$interactive" == true ]]; then
            python3 scripts/setup_github_secrets_from_env.py --yaml-config
        else
            python3 scripts/setup_github_secrets_from_env.py --yaml-config
        fi
    else
        if [[ "$interactive" == true ]]; then
            python3 scripts/setup_github_secrets_from_env.py --interactive
        else
            python3 scripts/setup_github_secrets_from_env.py --env-file .env
        fi
    fi
    
    log "GitHub setup completed"
}

# Kubernetes deployment
deploy_kubernetes() {
    local namespace="default"
    local dry_run=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --namespace)
                namespace="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            *)
                warn "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    log "Deploying to Kubernetes (namespace: $namespace)..."
    
    cd "$PROJECT_ROOT"
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is required but not installed"
        exit 1
    fi
    
    # Generate Kubernetes ConfigMap
    info "Generating Kubernetes ConfigMap..."
    python3 scripts/env_deploy.py sync-k8s
    
    if [[ ! -f "deploy/configmap-full.yaml" ]]; then
        error "ConfigMap generation failed"
        exit 1
    fi
    
    # Apply to cluster
    if [[ "$dry_run" == true ]]; then
        info "Dry run mode - showing what would be applied:"
        kubectl apply -f deploy/configmap-full.yaml --namespace="$namespace" --dry-run=client -o yaml
    else
        info "Applying ConfigMap to cluster..."
        kubectl apply -f deploy/configmap-full.yaml --namespace="$namespace"
        
        # Verify deployment
        info "Verifying ConfigMap deployment..."
        kubectl get configmap tammi-config --namespace="$namespace" -o yaml
    fi
    
    log "Kubernetes deployment completed"
}

# Full deployment pipeline
full_deploy() {
    local environment="development"
    local skip_github=false
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                environment="$2"
                shift 2
                ;;
            --skip-github)
                skip_github=true
                shift
                ;;
            *)
                warn "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    log "Starting full deployment pipeline for environment: $environment"
    
    # Step 1: Environment setup
    info "Step 1/4: Environment Configuration"
    setup_environment --interactive
    
    # Step 2: GitHub setup (optional)
    if [[ "$skip_github" != true ]]; then
        info "Step 2/4: GitHub Actions Setup"
        setup_github --interactive
    else
        info "Step 2/4: Skipping GitHub setup"
    fi
    
    # Step 3: Build and test
    info "Step 3/4: Build and Test"
    if [[ -f "requirements.txt" ]]; then
        python3 -m pip install -r requirements.txt
    fi
    
    # Run tests if available
    if [[ -d "tests" ]]; then
        info "Running tests..."
        python3 -m pytest tests/ -v || warn "Some tests failed"
    fi
    
    # Step 4: Kubernetes deployment
    info "Step 4/4: Kubernetes Deployment"
    if [[ "$environment" == "production" ]]; then
        deploy_kubernetes --namespace production
    else
        deploy_kubernetes --namespace "$environment"
    fi
    
    log "Full deployment pipeline completed successfully!"
}

# Backup function
create_backup() {
    local backup_dir="$PROJECT_ROOT/backups/deploy_$(date +%Y%m%d_%H%M%S)"
    
    info "Creating backup in $backup_dir..."
    mkdir -p "$backup_dir"
    
    # Backup important files
    [[ -f "env-config.yaml" ]] && cp "env-config.yaml" "$backup_dir/"
    [[ -f "env-config.secret.yaml" ]] && cp "env-config.secret.yaml" "$backup_dir/"
    [[ -f ".github/workflows/ci-cd-pipeline.yml" ]] && cp ".github/workflows/ci-cd-pipeline.yml" "$backup_dir/"
    [[ -f "deploy/configmap-full.yaml" ]] && cp "deploy/configmap-full.yaml" "$backup_dir/"
    
    info "Backup created successfully"
}

# Help function
show_help() {
    cat << EOF
Tammi QA Agent - Deployment Script

USAGE:
    ./scripts/deploy.sh [COMMAND] [OPTIONS]

COMMANDS:
    env-setup       Setup environment configuration
    github-setup    Setup GitHub Actions and Secrets  
    k8s-deploy      Deploy to Kubernetes
    full-deploy     Complete deployment pipeline
    backup          Create backup of configuration files
    help            Show this help message

ENV-SETUP OPTIONS:
    --from-env      Migrate from existing .env files
    --interactive   Interactive setup with audit

GITHUB-SETUP OPTIONS:
    --interactive   Interactive GitHub setup
    --use-env       Use .env files instead of YAML config

K8S-DEPLOY OPTIONS:
    --namespace     Kubernetes namespace (default: default)
    --dry-run       Show what would be applied without applying

FULL-DEPLOY OPTIONS:
    --environment   Target environment (default: development)
    --skip-github   Skip GitHub Actions setup

EXAMPLES:
    # Setup environment from .env files
    ./scripts/deploy.sh env-setup --from-env

    # Interactive GitHub setup
    ./scripts/deploy.sh github-setup --interactive

    # Deploy to production namespace
    ./scripts/deploy.sh k8s-deploy --namespace production

    # Full deployment to production
    ./scripts/deploy.sh full-deploy --environment production

    # Create backup
    ./scripts/deploy.sh backup

For more information, see docs/environment-deployment-guide.md
EOF
}

# Main function
main() {
    # Initialize log file
    echo "=== Deployment Script Started at $(date) ===" >> "$LOG_FILE"
    
    # Check prerequisites
    check_prerequisites
    
    # Parse command
    case "${1:-help}" in
        env-setup)
            shift
            setup_environment "$@"
            ;;
        github-setup)
            shift
            setup_github "$@"
            ;;
        k8s-deploy)
            shift
            deploy_kubernetes "$@"
            ;;
        full-deploy)
            shift
            full_deploy "$@"
            ;;
        backup)
            create_backup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown command: $1"
            echo
            show_help
            exit 1
            ;;
    esac
    
    echo "=== Deployment Script Completed at $(date) ===" >> "$LOG_FILE"
}

# Run main function with all arguments
main "$@"