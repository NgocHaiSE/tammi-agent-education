# =============================================================================
# Tammi QA Agent - Deployment Script (Windows PowerShell)
# =============================================================================
# 
# This script provides comprehensive deployment automation for the Tammi QA Agent
# including environment configuration, GitHub Actions setup, and Kubernetes deployment.
#
# Usage:
#   .\scripts\deploy.ps1 [command] [options]
#
# Commands:
#   env-setup       Setup environment configuration
#   github-setup    Setup GitHub Actions and Secrets
#   k8s-deploy      Deploy to Kubernetes
#   full-deploy     Complete deployment pipeline
#   help           Show this help message
#
# Examples:
#   .\scripts\deploy.ps1 env-setup -FromEnv
#   .\scripts\deploy.ps1 github-setup -Interactive
#   .\scripts\deploy.ps1 k8s-deploy -Namespace production
#   .\scripts\deploy.ps1 full-deploy -Environment production
#
# =============================================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("env-setup", "github-setup", "k8s-deploy", "full-deploy", "backup", "help")]
    [string]$Command = "help",
    
    # Environment setup options
    [switch]$FromEnv,
    [switch]$Interactive,
    
    # GitHub setup options
    [switch]$UseEnv,
    
    # Kubernetes options
    [string]$Namespace = "default",
    [switch]$DryRun,
    
    # Full deploy options
    [string]$Environment = "development",
    [switch]$SkipGitHub
)

# Script configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$LogFile = Join-Path $ProjectRoot "deploy.log"

# Logging functions
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] ${Level}: ${Message}"
    
    switch ($Level) {
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        "WARN"  { Write-Host $logMessage -ForegroundColor Yellow }
        "INFO"  { Write-Host $logMessage -ForegroundColor Blue }
        default { Write-Host $logMessage -ForegroundColor Green }
    }
    
    Add-Content -Path $LogFile -Value $logMessage
}

function Write-Success {
    param([string]$Message)
    Write-Log $Message "SUCCESS"
}

function Write-Error {
    param([string]$Message)
    Write-Log $Message "ERROR"
}

function Write-Warning {
    param([string]$Message)
    Write-Log $Message "WARN"
}

function Write-Info {
    param([string]$Message)
    Write-Log $Message "INFO"
}

# Check prerequisites
function Test-Prerequisites {
    Write-Log "Checking prerequisites..."
    
    # Check Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python is required but not installed"
        exit 1
    }
    
    # Check if we're in the right directory
    $envConfigPath = Join-Path $ProjectRoot "env-config.yaml"
    if (-not (Test-Path $envConfigPath)) {
        Write-Error "env-config.yaml not found. Please run from project root directory"
        exit 1
    }
    
    # Check if env_deploy.py exists
    $envDeployPath = Join-Path $ProjectRoot "scripts\env_deploy.py"
    if (-not (Test-Path $envDeployPath)) {
        Write-Error "scripts\env_deploy.py not found"
        exit 1
    }
    
    Write-Log "Prerequisites check passed"
}

# Environment setup functions
function Invoke-EnvSetup {
    Write-Log "Setting up environment configuration..."
    
    if ($FromEnv) {
        Write-Log "Migrating from .env files to env-config.yaml..."
        $result = python (Join-Path $ProjectRoot "scripts\env_deploy.py") migrate
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to migrate from .env files"
            exit 1
        }
        Write-Success "Migration completed successfully"
    }
    
    if ($Interactive) {
        Write-Log "Starting interactive environment setup..."
        $result = python (Join-Path $ProjectRoot "scripts\env_deploy.py") interactive
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Interactive setup failed"
            exit 1
        }
        Write-Success "Interactive setup completed"
    }
    
    Write-Success "Environment setup completed"
}

# GitHub setup functions
function Invoke-GitHubSetup {
    Write-Log "Setting up GitHub Actions and Secrets..."
    
    # Generate GitHub Actions workflow
    Write-Log "Generating GitHub Actions workflow..."
    $result = python (Join-Path $ProjectRoot "scripts\env_deploy.py") sync-github
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate GitHub Actions workflow"
        exit 1
    }
    
    # Setup GitHub Secrets
    if ($UseEnv) {
        Write-Log "Setting up GitHub Secrets from .env files..."
        $result = python (Join-Path $ProjectRoot "scripts\setup_github_secrets_from_env.py") --interactive
    } else {
        Write-Log "Setting up GitHub Secrets from env-config.secret.yaml..."
        $result = python (Join-Path $ProjectRoot "scripts\setup_github_secrets_from_env.py") --yaml-config
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to setup GitHub Secrets"
        exit 1
    }
    
    Write-Success "GitHub setup completed"
}

# Kubernetes deployment functions
function Invoke-K8sDeploy {
    Write-Log "Deploying to Kubernetes..."
    
    # Check kubectl availability
    if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
        Write-Error "kubectl is required but not installed"
        exit 1
    }
    
    # Generate Kubernetes ConfigMap
    Write-Log "Generating Kubernetes ConfigMap..."
    $args = @(
        (Join-Path $ProjectRoot "scripts\env_deploy.py"),
        "sync-k8s-configmap",
        "--namespace", $Namespace
    )
    
    if ($DryRun) {
        $args += "--dry-run"
    }
    
    $result = python @args
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to generate/apply Kubernetes ConfigMap"
        exit 1
    }
    
    Write-Success "Kubernetes deployment completed"
}

# Full deployment pipeline
function Invoke-FullDeploy {
    Write-Log "Starting full deployment pipeline for environment: $Environment"
    
    # Step 1: Environment setup
    Write-Log "Step 1: Environment setup"
    Invoke-EnvSetup
    
    # Step 2: GitHub setup (unless skipped)
    if (-not $SkipGitHub) {
        Write-Log "Step 2: GitHub Actions setup"
        Invoke-GitHubSetup
    } else {
        Write-Log "Step 2: Skipping GitHub setup as requested"
    }
    
    # Step 3: Kubernetes deployment
    Write-Log "Step 3: Kubernetes deployment"
    $script:Namespace = $Environment
    Invoke-K8sDeploy
    
    Write-Success "Full deployment pipeline completed successfully"
}

# Backup function
function Invoke-Backup {
    Write-Log "Creating backup of current configuration..."
    
    $backupDir = Join-Path $ProjectRoot "backups\$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    # Backup configuration files
    $filesToBackup = @(
        "env-config.yaml",
        "env-config.secret.yaml"
    )
    
    foreach ($file in $filesToBackup) {
        $sourcePath = Join-Path $ProjectRoot $file
        if (Test-Path $sourcePath) {
            Copy-Item $sourcePath $backupDir
            Write-Log "Backed up: $file"
        }
    }
    
    # Backup generated files
    $generatedDir = Join-Path $ProjectRoot "deploy\generated"
    if (Test-Path $generatedDir) {
        Copy-Item $generatedDir (Join-Path $backupDir "generated") -Recurse
        Write-Log "Backed up generated deployment files"
    }
    
    Write-Success "Backup created at: $backupDir"
}

# Help function
function Show-Help {
    Write-Host @"
=============================================================================
Tammi QA Agent - Deployment Script (Windows PowerShell)
=============================================================================

USAGE:
    .\scripts\deploy.ps1 [command] [options]

COMMANDS:
    env-setup       Setup environment configuration
    github-setup    Setup GitHub Actions and Secrets  
    k8s-deploy      Deploy to Kubernetes
    full-deploy     Complete deployment pipeline
    backup          Backup current configuration
    help           Show this help message

ENVIRONMENT SETUP OPTIONS:
    -FromEnv        Migrate from existing .env files
    -Interactive    Interactive environment configuration

GITHUB SETUP OPTIONS:
    -UseEnv         Use .env files instead of env-config.secret.yaml

KUBERNETES OPTIONS:
    -Namespace      Kubernetes namespace (default: default)
    -DryRun         Perform dry run without applying changes

FULL DEPLOY OPTIONS:
    -Environment    Target environment (default: development)
    -SkipGitHub     Skip GitHub Actions setup

EXAMPLES:
    # Setup environment from .env files
    .\scripts\deploy.ps1 env-setup -FromEnv

    # Interactive environment setup
    .\scripts\deploy.ps1 env-setup -Interactive

    # Setup GitHub Actions and Secrets
    .\scripts\deploy.ps1 github-setup

    # Deploy to Kubernetes production namespace
    .\scripts\deploy.ps1 k8s-deploy -Namespace production

    # Full deployment pipeline
    .\scripts\deploy.ps1 full-deploy -Environment production

    # Create backup
    .\scripts\deploy.ps1 backup

=============================================================================
"@ -ForegroundColor Cyan
}

# Main execution
function Main {
    Write-Log "Starting Tammi QA Agent deployment script"
    Write-Log "Command: $Command"
    
    # Check prerequisites for all commands except help
    if ($Command -ne "help") {
        Test-Prerequisites
    }
    
    switch ($Command) {
        "env-setup" {
            Invoke-EnvSetup
        }
        "github-setup" {
            Invoke-GitHubSetup
        }
        "k8s-deploy" {
            Invoke-K8sDeploy
        }
        "full-deploy" {
            Invoke-FullDeploy
        }
        "backup" {
            Invoke-Backup
        }
        "help" {
            Show-Help
        }
        default {
            Write-Error "Unknown command: $Command"
            Show-Help
            exit 1
        }
    }
    
    Write-Log "Deployment script completed successfully"
}

# Execute main function
Main