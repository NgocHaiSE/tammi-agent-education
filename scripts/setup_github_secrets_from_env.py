#!/usr/bin/env python3
"""
GitHub Secrets Setup from Environment Configuration
==================================================

This script helps you set up GitHub Secrets from environment configuration files.

Usage:
    # From YAML config
    python scripts/setup_github_secrets_from_env.py --yaml-config
    
    # Interactive mode
    python scripts/setup_github_secrets_from_env.py --interactive
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Set, Optional
import subprocess
import json
import yaml


class GitHubSecretsSetup:
    """Setup GitHub Secrets from environment configuration files."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        
    def load_yaml_config(self) -> Dict[str, str]:
        """Load secrets from env-config.secret.yaml."""
        secrets = {}
        secret_file = self.project_root / "env-config.secret.yaml"
        
        if not secret_file.exists():
            print(f"[WARNING] File not found: {secret_file}")
            print("   Create env-config.secret.yaml with your secret values.")
            return secrets
            
        try:
            with open(secret_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            if config and 'secrets' in config:
                secrets.update(config['secrets'])
                print(f"[SUCCESS] Loaded {len(secrets)} secrets from {secret_file}")
            else:
                print(f"[WARNING] No 'secrets' section found in {secret_file}")
                
        except yaml.YAMLError as e:
            print(f"[ERROR] Error parsing YAML file {secret_file}: {e}")
        except Exception as e:
            print(f"[ERROR] Error reading file {secret_file}: {e}")
            
        return secrets
    
    def get_secret_variables(self) -> Set[str]:
        """Get list of secret variables from env-config.yaml."""
        try:
            config_file = self.project_root / "env-config.yaml"
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            secret_vars = set()
            if 'variables' in config:
                for var_name, var_config in config['variables'].items():
                    if var_config.get('secret', False):
                        secret_vars.add(var_name)
            
            return secret_vars
        except Exception as e:
            print(f"[ERROR] Error loading secret variables: {e}")
            return set()
    
    def check_github_cli(self) -> bool:
        """Check if GitHub CLI is installed and authenticated."""
        try:
            result = subprocess.run(['gh', 'auth', 'status'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Extract username from output
                output_text = result.stdout + result.stderr
                for line in output_text.split('\n'):
                    if 'Logged in to github.com account' in line:
                        username = line.split('account ')[1].split(' ')[0]
                        print(f"[SUCCESS] GitHub CLI is authenticated as: {username}")
                        return True
                    elif 'Logged in to github.com as' in line:
                        username = line.split('as ')[1].split(' ')[0]
                        print(f"[SUCCESS] GitHub CLI is authenticated as: {username}")
                        return True
            return False
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"[ERROR] GitHub CLI authentication failed: {e}")
            return False
    
    def get_repo_info(self) -> Optional[str]:
        """Get GitHub repository information."""
        try:
            result = subprocess.run(['gh', 'repo', 'view', '--json', 'nameWithOwner'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                repo_info = json.loads(result.stdout)
                return repo_info.get('nameWithOwner')
        except Exception as e:
            print(f"[ERROR] Failed to get repository info: {e}")
        return None
    
    def set_github_secret(self, name: str, value: str) -> bool:
        """Set a GitHub secret using GitHub CLI."""
        try:
            result = subprocess.run(['gh', 'secret', 'set', name], 
                                  input=value, text=True, capture_output=True)
            if result.returncode == 0:
                print(f"   [SUCCESS] Secret '{name}' set successfully")
                return True
            else:
                print(f"   [ERROR] Failed to set secret '{name}': {result.stderr}")
                return False
        except Exception as e:
            print(f"   [ERROR] Failed to set secret '{name}': {e}")
            return False
    
    def setup_from_yaml_config(self):
        """Setup GitHub Secrets from YAML configuration."""
        print("Setting up GitHub Secrets from YAML Configuration")
        print("=" * 60)
        
        # Check GitHub CLI
        if not self.check_github_cli():
            print("[ERROR] GitHub CLI not found or not authenticated.")
            print("   Please install GitHub CLI and run: gh auth login")
            return False
        
        repo = self.get_repo_info()
        if repo:
            print(f"Repository: {repo}")
        else:
            print("[WARNING] Could not detect repository. Make sure you're in a Git repository.")
        
        print()
        
        # Load secrets from YAML config
        secrets = self.load_yaml_config()
        
        if not secrets:
            print("[ERROR] No secrets found in env-config.secret.yaml")
            print("   Please create env-config.secret.yaml with your secret values.")
            return False
        
        print(f"Found {len(secrets)} secrets to set up:")
        for name in secrets.keys():
            print(f"   • {name}")
        print()
        
        # Ask user how to proceed
        print("How would you like to set up these secrets?")
        print("1. Set all secrets automatically")
        print("2. Set secrets interactively (review each one)")
        print("3. Show manual setup instructions")
        print("4. Cancel")
        
        while True:
            choice = input("\nEnter your choice (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                break
            print("Please enter 1, 2, 3, or 4")
        
        if choice == '1':
            return self._set_all_secrets(secrets)
        elif choice == '2':
            return self._set_secrets_interactive(secrets)
        elif choice == '3':
            return self._show_manual_instructions(secrets)
        else:
            print("[INFO] Setup cancelled by user")
            return False

    def interactive_setup(self):
        """Interactive setup of GitHub Secrets."""
        print("GitHub Secrets Interactive Setup")
        print("=" * 50)
        
        # Check GitHub CLI
        if not self.check_github_cli():
            print("[ERROR] GitHub CLI not found or not authenticated.")
            print("   Please install GitHub CLI and run: gh auth login")
            return False
        
        repo = self.get_repo_info()
        if repo:
            print(f"Repository: {repo}")
        else:
            print("[WARNING] Could not detect repository. Make sure you're in a Git repository.")
        
        print()
        
        # Check for YAML config
        yaml_config_exists = (self.project_root / "env-config.secret.yaml").exists()
        
        print("Detected configuration sources:")
        if yaml_config_exists:
            print("   [SUCCESS] env-config.secret.yaml (YAML configuration)")
        else:
            print("   [ERROR] env-config.secret.yaml not found")
            print("   Please create env-config.secret.yaml with your secrets.")
            return False
        
        print()
        return self.setup_from_yaml_config()
    
    def _set_all_secrets(self, secrets: Dict[str, str]) -> bool:
        """Set all secrets automatically."""
        print(f"\nSetting {len(secrets)} secrets...")
        
        success_count = 0
        for name, value in secrets.items():
            if not value or value == "":
                print(f"   [WARNING] Skipping '{name}' (empty value)")
                continue
            
            print(f"   Setting {name}...", end=" ")
            if self.set_github_secret(name, value):
                success_count += 1
        
        if success_count > 0:
            print(f"\n[SUCCESS] Successfully set {success_count} secrets in GitHub repository!")
        else:
            print(f"\n[WARNING] No secrets were set. Check if secrets have values in env-config.secret.yaml")
        return success_count > 0
    
    def _set_secrets_interactive(self, secrets: Dict[str, str]) -> bool:
        """Set secrets one by one with confirmation."""
        print(f"\nInteractive secret setup...")
        
        success_count = 0
        for name, value in secrets.items():
            if not value or value == "":
                print(f"\n[WARNING] Secret: {name} has empty value, skipping...")
                continue
            
            print(f"\nSecret: {name}")
            print(f"   Value: {value[:20]}{'...' if len(value) > 20 else ''}")
            
            choice = input("   Set this secret? (y/n/s=skip all): ").strip().lower()
            
            if choice == 's':
                print("Skipping remaining secrets...")
                break
            elif choice == 'y':
                print(f"   Setting {name}...")
                if self.set_github_secret(name, value):
                    success_count += 1
            else:
                print("   Skipped")
        
        print(f"\n[SUCCESS] Successfully set {success_count} secrets.")
        return True
    
    def _show_manual_instructions(self, secrets: Dict[str, str]) -> bool:
        """Show manual setup instructions."""
        repo = self.get_repo_info()
        
        print("\nManual GitHub Secrets Setup Instructions")
        print("=" * 50)
        
        if repo:
            print(f"1. Go to: https://github.com/{repo}/settings/secrets/actions")
        else:
            print("1. Go to your GitHub repository")
            print("2. Navigate to: Settings → Secrets and variables → Actions")
        
        print("3. Click 'New repository secret' for each of the following:")
        print()
        
        for name, value in secrets.items():
            if not value or value == "":
                print(f"   [WARNING] Secret Name: {name}")
                print(f"   [WARNING] Secret Value: <EMPTY - NEEDS TO BE SET>")
            else:
                print(f"   Secret Name: {name}")
                value_preview = value[:30] + "..." if len(value) > 30 else value
                print(f"   Secret Value: {value_preview}")
            print("   " + "-" * 40)
        
        print("\nTips:")
        print("   - Copy the exact secret names (case-sensitive)")
        print("   - Make sure there are no extra spaces")
        print("   - Verify all secrets are set before running CI/CD")
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup GitHub Secrets from environment configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From YAML configuration (recommended)
  python scripts/setup_github_secrets_from_env.py --yaml-config
  
  # Interactive mode (auto-detect)
  python scripts/setup_github_secrets_from_env.py --interactive
        """
    )
    
    parser.add_argument('--yaml-config', action='store_true',
                       help='Use YAML configuration (env-config.secret.yaml)')
    parser.add_argument('--interactive', action='store_true',
                       help='Interactive mode')
    
    args = parser.parse_args()
    
    setup = GitHubSecretsSetup()
    
    try:
        if args.interactive or args.yaml_config:
            if args.interactive:
                success = setup.interactive_setup()
            else:
                success = setup.setup_from_yaml_config()
        else:
            parser.print_help()
            return 1
        
        return 0 if success else 1
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
