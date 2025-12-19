#!/usr/bin/env python3
"""
Environment Deployment Manager - Tammi medical Agent
======================================================

This script manages environment variable deployment across different platforms:
- GitHub Actions (ci-cd-pipeline.yml)
- Kubernetes ConfigMaps (configmap-full.yaml)

It reads from:
- env-config.yaml (public schema and defaults)
- env-config.secret.yaml (private secret values)
- OS environment variables (highest precedence)

Usage:
    python scripts/env_deploy.py sync-all
    python scripts/env_deploy.py sync-github --interactive
    python scripts/env_deploy.py sync-k8s
    python scripts/env_deploy.py list-secrets
    python scripts/env_deploy.py validate
"""

import os
import sys
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import re
from datetime import datetime

def convert_values_to_strings(data):
    if isinstance(data, dict):
        # Duyệt qua các mục, gọi đệ quy cho giá trị, giữ nguyên khóa
        return {k: convert_values_to_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        # Duyệt qua danh sách, gọi đệ quy cho từng phần tử
        return [convert_values_to_strings(i) for i in data]
    else:
        # Đây là giá trị cuối cùng: chuyển nó thành chuỗi
        # Bao gồm int, float, bool, None, v.v.
        return '"' + str(data) + '"'


class EnvDeployManager:
    """Manages environment variable deployment across platforms."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the deployment manager."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.config_file = self.project_root / "env-config.yaml"
        self.secret_file = self.project_root / "env-config.secret.yaml"
        
        # Load configurations
        self.config = self._load_yaml_file(self.config_file)
        self.secrets = self._load_yaml_file(self.secret_file, required=False)
        
        # Merged environment variables with precedence
        self.env_vars = self._merge_environment_variables()
    
    def _load_yaml_file(self, file_path: Path, required: bool = True) -> Dict[str, Any]:
        """Load YAML file with error handling."""
        try:
            if not file_path.exists():
                if required:
                    raise FileNotFoundError(f"Required file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading {file_path}: {e}")

    def _merge_environment_variables(self) -> Dict[str, Any]:
        """
        Merge environment variables with precedence:
        OS Environment > env-config.secret.yaml > env-config.yaml defaults
        """
        merged = {}
        
        # Start with defaults from config
        if 'variables' in self.config:
            for var_name, var_config in self.config['variables'].items():
                if 'default' in var_config:
                    merged[var_name] = var_config['default']
        
        # Override with values from secret file
        if self.secrets:
            # Secret values
            if 'secrets' in self.secrets:
                merged.update(self.secrets['secrets'])
            
            # Non-secret override values
            if 'values' in self.secrets:
                merged.update(self.secrets['values'])
        
        # Override with OS environment variables (highest precedence)
        for var_name in merged.keys():
            if var_name in os.environ:
                merged[var_name] = os.environ[var_name]
        
        return merged
    
    def get_secret_variables(self) -> Set[str]:
        """Get list of variables marked as secrets."""
        secrets = set()
        
        if 'variables' in self.config:
            for var_name, var_config in self.config['variables'].items():
                if var_config.get('secret', False):
                    secrets.add(var_name)
        
        return secrets
    
    def get_required_variables(self) -> Set[str]:
        """Get list of required variables."""
        required = set()
        
        if 'variables' in self.config:
            for var_name, var_config in self.config['variables'].items():
                if var_config.get('required', False):
                    required.add(var_name)
        
        return required
    
    def validate_configuration(self) -> List[str]:
        """Validate the current configuration and return any errors."""
        errors = []
        
        # Check required variables
        required_vars = self.get_required_variables()
        for var_name in required_vars:
            if var_name not in self.env_vars or not self.env_vars[var_name]:
                errors.append(f"Required variable '{var_name}' is missing or empty")
        
        # Check secret variables have values
        secret_vars = self.get_secret_variables()
        for var_name in secret_vars:
            if var_name in self.env_vars:
                value = str(self.env_vars[var_name])
                if not value or value in ['your_api_key_here', 'your_secret_here', '']:
                    errors.append(f"Secret variable '{var_name}' appears to have placeholder value")
        
        return errors
    
    def sync_github_actions(self, interactive: bool = False) -> bool:
        """Update GitHub Actions workflow with environment variables."""
        try:
            workflow_file = self.project_root / ".github" / "workflows" / "ci-cd-pipeline.yml"
            
            if interactive:
                self._interactive_github_secrets()
                return True
            
            # Read existing workflow or create new one
            if workflow_file.exists():
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                
                # Create backup
                backup_file = workflow_file.with_suffix(f'.yml.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(existing_content)
                print(f"[SUCCESS] Created backup: {backup_file}")
                
                # Update existing workflow
                workflow_content = self._update_github_workflow(existing_content)
            else:
                # Generate new workflow
                workflow_content = self._generate_github_workflow()
            
            # Ensure directory exists
            workflow_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write workflow file
            with open(workflow_file, 'w', encoding='utf-8') as f:
                f.write(workflow_content)
            
            print(f"[SUCCESS] Updated GitHub Actions workflow: {workflow_file}")
            self._list_github_secrets()
            return True
            
        except Exception as e:
            print(f"[ERROR] Error updating GitHub Actions workflow: {e}")
            return False
    
    def _update_github_workflow(self, existing_content: str) -> str:
        """Update existing GitHub Actions workflow with new environment variables."""
        try:
            # Use form template as base for proper structure
            form_template_file = self.project_root / ".github" / "workflows" / "ci-cd-pipeline.form.yml"
            
            if form_template_file.exists():
                print(f"[INFO] Using template from {form_template_file}")
                return self._generate_workflow_from_template(form_template_file)
            else:
                print(f"[WARNING] Template file not found: {form_template_file}")
                # Fallback to updating existing workflow
                return self._update_existing_workflow_content(existing_content)
                
        except Exception as e:
            print(f"Warning: Could not update workflow, generating new one: {e}")
            return self._generate_github_workflow()
    
    def _generate_workflow_from_template(self, template_file: Path) -> str:
        """Generate workflow from form template with proper ENV variables."""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Parse template
            # Remove header comments first to get clean YAML
            yaml_content = template_content
            if yaml_content.startswith('#'):
                lines = yaml_content.split('\n')
                yaml_start = 0
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('# '):
                        yaml_start = i
                        break
                yaml_content = '\n'.join(lines[yaml_start:])
            
            workflow = yaml.safe_load(yaml_content) or {}
            
            # Fix the 'on' key issue - YAML parser converts 'on' to True
            on_triggers = None
            if True in workflow:
                on_triggers = workflow.pop(True)
            elif 'true' in workflow:
                on_triggers = workflow.pop('true')
            elif 'on' in workflow:
                on_triggers = workflow.pop('on')
            
            # Update environment variables
            secret_vars = self.get_secret_variables()
            non_secret_vars = {k: v for k, v in self.env_vars.items() if k not in secret_vars}
            
            # Replace placeholder ENV section with actual values
            # Sort environment variables for better readability
            sorted_env_vars = dict(sorted(non_secret_vars.items()))
            
            # Add secret environment variables with GitHub Actions secrets syntax
            secret_env_vars = {}
            for secret_var in sorted(secret_vars):
                secret_env_vars[secret_var] = f"${{{{ secrets.{secret_var} }}}}"
            
            # Combine non-secret and secret variables
            all_env_vars = {}
            all_env_vars.update(sorted_env_vars)
            all_env_vars.update(secret_env_vars)
            
            # Create ordered workflow structure to ensure correct order
            ordered_workflow = {}
            
            # 1. name
            if 'name' in workflow:
                ordered_workflow['name'] = workflow['name']
            
            # 2. on (triggers) - MUST be second
            if on_triggers:
                ordered_workflow['on'] = on_triggers
            
            # 3. env
            ordered_workflow['env'] = all_env_vars
            
            # 4. jobs
            if 'jobs' in workflow:
                ordered_workflow['jobs'] = workflow['jobs']
            
            # Add any remaining keys
            for key, value in workflow.items():
                if key not in ordered_workflow:
                    ordered_workflow[key] = value
            
            # Add header comment
            header = f"""# ===================================================================
# GitHub Actions CI/CD Pipeline - Tammi API Gateway
# ===================================================================
# Auto-updated by env_deploy.py on {datetime.now().isoformat()}
# DO NOT EDIT MANUALLY - Use 'python scripts/env_deploy.py sync-github'
# ===================================================================

"""
            
            # Generate YAML with proper formatting
            yaml_output = yaml.dump(ordered_workflow, default_flow_style=False, sort_keys=False, width=1000, allow_unicode=True)
            
            # Post-process YAML to fix common issues
            yaml_lines = yaml_output.split('\n')
            formatted_lines = []
            
            for line in yaml_lines:
                # Fix the 'true:' issue that sometimes occurs
                if line.strip() == 'true:':
                    formatted_lines.append('on:')
                # Fix quoted 'on' keys
                elif line.strip() == "'on':" or line.strip() == '"on":':
                    formatted_lines.append('on:')
                else:
                    formatted_lines.append(line)
            
            return header + '\n'.join(formatted_lines)
            
        except Exception as e:
            print(f"Error generating from template: {e}")
            raise
    
    def _update_existing_workflow_content(self, existing_content: str) -> str:
        """Update existing workflow content (fallback method) - preserves complex YAML structures."""
        try:
            # Generate new environment variables
            secret_vars = self.get_secret_variables()
            non_secret_vars = {k: v for k, v in self.env_vars.items() if k not in secret_vars}
            
            # Add secret environment variables with GitHub Actions secrets syntax
            secret_env_vars = {}
            for secret_var in sorted(secret_vars):
                secret_env_vars[secret_var] = f"${{{{ secrets.{secret_var} }}}}"
            
            # Combine non-secret and secret variables
            all_env_vars = {}
            all_env_vars.update(sorted(non_secret_vars.items()))
            all_env_vars.update(secret_env_vars)
            
            # Use regex-based replacement to preserve file structure
            lines = existing_content.split('\n')
            result_lines = []
            
            # Add header comment
            header = f"""# ===================================================================
# GitHub Actions CI/CD Pipeline - Tammi API Gateway
# ===================================================================
# Auto-updated by env_deploy.py on {datetime.now().isoformat()}
# DO NOT EDIT MANUALLY - Use 'python scripts/env_deploy.py sync-github'
# ==================================================================="""
            
            # Skip existing header comments and find the start of YAML content
            yaml_start = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.strip().startswith('#'):
                    yaml_start = i
                    break
            
            # Add new header
            result_lines.extend(header.split('\n'))
            result_lines.append('')  # Empty line after header
            
            # Process the YAML content line by line
            in_env_section = False
            env_section_indent = 0
            in_jobs_section = False
            i = yaml_start
            
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                
                # Track if we're in the jobs section
                if stripped == 'jobs:' or stripped.startswith('jobs:'):
                    in_jobs_section = True
                
                # Check if we're at the env section (only process global env, not job-level env)
                if (stripped == 'env:' or stripped.startswith('env:')) and not in_jobs_section:
                    in_env_section = True
                    env_section_indent = len(line) - len(line.lstrip())
                    result_lines.append(line)  # Add the 'env:' line
                    
                    # Add all environment variables
                    for var_name, var_value in all_env_vars.items():
                        if isinstance(var_value, str) and (var_value.startswith('${{') or var_value.startswith('"${{')):
                            # Secret variable - no quotes needed
                            result_lines.append(f"{' ' * (env_section_indent + 2)}{var_name}: {var_value}")
                        else:
                            # Regular variable - always quote string values for safety
                            if isinstance(var_value, str):
                                # Always quote strings to avoid YAML parsing issues
                                result_lines.append(f"{' ' * (env_section_indent + 2)}{var_name}: \"{var_value}\"")
                            else:
                                # Non-string values (numbers, booleans) don't need quotes
                                result_lines.append(f"{' ' * (env_section_indent + 2)}{var_name}: {var_value}")
                    
                    # Skip existing env variables until we reach the next section
                    i += 1
                    while i < len(lines):
                        next_line = lines[i]
                        next_stripped = next_line.strip()
                        
                        # Skip empty lines and comments
                        if not next_stripped or next_stripped.startswith('#'):
                            i += 1
                            continue
                            
                        next_indent = len(next_line) - len(next_line.lstrip())
                        
                        # If we hit a line with same or less indentation, we're out of env section
                        if next_indent <= env_section_indent:
                            in_env_section = False
                            break
                        
                        # Skip this env variable line (it's part of the old env section)
                        i += 1
                    continue
                
                elif not in_env_section:
                    # Not in env section, preserve the line as-is
                    result_lines.append(line)
                
                i += 1
            
            return '\n'.join(result_lines)
            
        except Exception as e:
            print(f"Error updating existing workflow: {e}")
            raise
    
    def _generate_github_workflow(self) -> str:
        """Generate GitHub Actions workflow YAML content."""
        secret_vars = self.get_secret_variables()
        non_secret_vars = {k: v for k, v in self.env_vars.items() if k not in secret_vars}
        
        workflow = {
            'name': 'CI/CD Pipeline - Tammi API Gateway',
            'on': {
                'push': {
                    'branches': ['main', 'develop']
                },
                'pull_request': {
                    'branches': ['main', 'develop']
                }
            },
            'env': non_secret_vars,
            'jobs': {
                'test': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {
                            'name': 'Checkout code',
                            'uses': 'actions/checkout@v4'
                        },
                        {
                            'name': 'Set up Python',
                            'uses': 'actions/setup-python@v4',
                            'with': {
                                'python-version': '3.11'
                            }
                        },
                        {
                            'name': 'Install dependencies',
                            'run': 'pip install -r requirements.txt'
                        },
                        {
                            'name': 'Run tests',
                            'env': {var: f'${{{{ secrets.{var} }}}}' for var in secret_vars},
                            'run': 'python -m pytest tests/ -v'
                        }
                    ]
                },
                'deploy': {
                    'needs': 'test',
                    'runs-on': 'ubuntu-latest',
                    'if': "github.ref == 'refs/heads/main'",
                    'steps': [
                        {
                            'name': 'Checkout code',
                            'uses': 'actions/checkout@v4'
                        },
                        {
                            'name': 'Deploy to production',
                            'env': {var: f'${{{{ secrets.{var} }}}}' for var in secret_vars},
                            'run': 'echo "Deploy to production"'
                        }
                    ]
                }
            }
        }
        
        # Add header comment
        header = f"""# ===================================================================
# GitHub Actions CI/CD Pipeline - Tammi API Gateway
# ===================================================================
# Auto-generated by env_deploy.py on {datetime.now().isoformat()}
# DO NOT EDIT MANUALLY - Use 'python scripts/env_deploy.py sync-github'
# ===================================================================

"""
        
        return header + yaml.dump(workflow, default_flow_style=False, sort_keys=False)
    
    def _interactive_github_secrets(self):
        """Interactive mode for setting GitHub secrets."""
        secret_vars = self.get_secret_variables()
        
        print("\n" + "="*60)
        print("GitHub Secrets Configuration")
        print("="*60)
        print("The following secrets need to be configured in your GitHub repository:")
        print("Go to: Settings > Secrets and variables > Actions > New repository secret")
        print()
        
        for var_name in sorted(secret_vars):
            value = self.env_vars.get(var_name, '')
            description = ''
            
            if 'variables' in self.config and var_name in self.config['variables']:
                description = self.config['variables'][var_name].get('description', '')
            
            print(f"Secret Name: {var_name}")
            if description:
                print(f"Description: {description}")
            if value and not self._is_placeholder_value(value):
                print(f"Value: {value}")
            else:
                print("Value: [NEEDS TO BE SET]")
            print("-" * 40)
        
        print("\nAfter setting all secrets, run the workflow to test the configuration.")
    
    def _list_github_secrets(self):
        """List GitHub secrets that need to be configured."""
        secret_vars = self.get_secret_variables()
        
        print("\n" + "="*50)
        print("GitHub Secrets Required:")
        print("="*50)
        
        for var_name in sorted(secret_vars):
            print(f"- {var_name}")
        
        print(f"\nTotal: {len(secret_vars)} secrets need to be configured in GitHub.")
        print("Use --interactive flag for detailed setup instructions.")
    
    def sync_kubernetes_configmap(self) -> bool:
        """Generate Kubernetes ConfigMap with all environment variables."""
        try:
            configmap_file = self.project_root / "deploy" / "configmap-full.yaml"
            configmap_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if file exists
            if configmap_file.exists():
                backup_file = configmap_file.with_suffix(f'.yaml.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                configmap_file.rename(backup_file)
                print(f"[SUCCESS] Created backup: {backup_file}")
            
            # Generate ConfigMap content
            configmap_content = self._generate_kubernetes_configmap()
            
            # Write ConfigMap file
            with open(configmap_file, 'w', encoding='utf-8') as f:
                f.write(configmap_content)
            
            print(f"[SUCCESS] Generated Kubernetes ConfigMap: {configmap_file}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error generating Kubernetes ConfigMap: {e}")
            return False
    
    def _generate_kubernetes_configmap(self) -> str:
        """Generate Kubernetes ConfigMap YAML content."""
        # Convert all values to strings for ConfigMap
        data = {k: str(v) for k, v in self.env_vars.items()}
        
        configmap = {
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': 'tammi-edu-agent-config',
                'namespace': 'default',
                'labels': {
                    'app': 'tammi-edu-agent',
                    'component': 'config'
                }
            },
            'data': data
        }
        
        # Add header comment
        header = f"""# ===================================================================
# Kubernetes ConfigMap - Tammi Edu Agent
# ===================================================================
# Auto-generated by env_deploy.py on {datetime.now().isoformat()}
# DO NOT EDIT MANUALLY - Use 'python scripts/env_deploy.py sync-k8s'
#
# Contains all environment variables including secrets.
# In production, consider using Kubernetes Secrets for sensitive data.
# ===================================================================

"""

        dump_yaml = yaml.dump(convert_values_to_strings(configmap), default_flow_style=False, sort_keys=False)

        dump_yaml = dump_yaml.replace("""\'\"""", """\"""")
        dump_yaml = dump_yaml.replace("""\"\'""", """\"""")

        return header + dump_yaml
    
    def _is_placeholder_value(self, value: str) -> bool:
        """Check if a value appears to be a placeholder."""
        placeholder_patterns = [
            r'your_.*_here',
            r'your_.*_key',
            r'your_.*_token',
            r'xxxxx+',
            r'placeholder',
            r'change_me',
            r'replace_me'
        ]
        
        value_str = str(value).lower()
        return any(re.search(pattern, value_str) for pattern in placeholder_patterns)
    
    def list_secrets(self):
        """List all secret variables and their status."""
        secret_vars = self.get_secret_variables()
        
        print("\n" + "="*60)
        print("Secret Variables Status")
        print("="*60)
        
        for var_name in sorted(secret_vars):
            value = self.env_vars.get(var_name, '')
            status = "[SUCCESS] SET" if value and not self._is_placeholder_value(value) else "[ERROR] MISSING/PLACEHOLDER"
            
            description = ''
            if 'variables' in self.config and var_name in self.config['variables']:
                description = self.config['variables'][var_name].get('description', '')
            
            print(f"{var_name:<30} {status}")
            if description:
                print(f"{'':30} {description}")
            print()
    
    def test_local_environment(self) -> bool:
        """Test loading environment variables locally."""
        print("≡ƒº¬ Testing local environment loading...")
        print()
        
        try:
            # Test YAML loading
            print("1. Loading configuration files...")
            config = self._load_yaml_file(self.config_file)
            secrets = self._load_yaml_file(self.secret_file, required=False)
            print("   [SUCCESS] YAML files loaded successfully")
            
            # Test environment merging
            print("2. Merging environment variables...")
            env_vars = self._merge_environment_variables()
            print(f"   [SUCCESS] Merged {len(env_vars)} environment variables")
            
            # Test required variables
            print("3. Checking required variables...")
            required_vars = self.get_required_variables()
            missing_vars = []
            for var in required_vars:
                if var not in env_vars or not env_vars[var]:
                    missing_vars.append(var)
            
            if missing_vars:
                print(f"   [ERROR] Missing required variables: {', '.join(missing_vars)}")
                return False
            else:
                print(f"   [SUCCESS] All {len(required_vars)} required variables are present")
            
            # Test secret variables
            print("4. Checking secret variables...")
            secret_vars = self.get_secret_variables()
            secret_count = sum(1 for var in secret_vars if var in env_vars and env_vars[var])
            print(f"   [SUCCESS] {secret_count}/{len(secret_vars)} secret variables are configured")
            
            # Test environment variable types
            print("5. Validating variable types...")
            type_errors = []
            for var_name, var_config in config.get('variables', {}).items():
                if var_name in env_vars:
                    value = env_vars[var_name]
                    var_type = var_config.get('type', 'string')
                    
                    if var_type == 'int':
                        try:
                            int(value)
                        except ValueError:
                            type_errors.append(f"{var_name}: expected int, got '{value}'")
                    elif var_type == 'bool':
                        if str(value).lower() not in ['true', 'false', '1', '0']:
                            type_errors.append(f"{var_name}: expected bool, got '{value}'")
            
            if type_errors:
                print("   [ERROR] Type validation errors:")
                for error in type_errors:
                    print(f"     - {error}")
                return False
            else:
                print("   [SUCCESS] All variable types are valid")
            
            print()
            print("Γ£à Local environment test passed!")
            print(f"   - Configuration variables: {len(config.get('variables', {}))}")
            print(f"   - Secret variables: {len(secret_vars)}")
            print(f"   - Required variables: {len(required_vars)}")
            print(f"   - Total environment variables: {len(env_vars)}")
            
            return True
            
        except Exception as e:
            print(f"   [ERROR] Error during testing: {e}")
            return False

    def sync_all(self) -> bool:
        """Sync all deployment targets."""
        print("Starting full environment deployment sync...")
        print("="*50)
        
        success = True
        
        # Validate first
        errors = self.validate_configuration()
        if errors:
            print("[ERROR] Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            print()
        
        # Sync GitHub Actions
        print("1. Syncing GitHub Actions...")
        if not self.sync_github_actions():
            success = False
        
        print()
        
        # Sync Kubernetes ConfigMap
        print("2. Syncing Kubernetes ConfigMap...")
        if not self.sync_kubernetes_configmap():
            success = False
        
        print()
        
        if success:
            print("[SUCCESS] All deployments synced successfully!")
        else:
            print("[ERROR] Some deployments failed. Check the errors above.")
        
        return success


class ConfigMapDiff:
    """Handle ConfigMap comparison and diff generation for sync-k8s-diff command."""

    COLORS = {
        'RESET': '\033[0m',
        'RED': '\033[91m',      # Removed
        'GREEN': '\033[92m',    # Added
        'YELLOW': '\033[93m',   # Modified
        'BLUE': '\033[94m',     # Info
        'CYAN': '\033[96m',     # Section headers
    }

    def __init__(self, project_root: Optional[Path] = None, use_colors: bool = True):
        self.use_colors = use_colors
        self.project_root = project_root or Path(__file__).parent.parent

    def _color(self, text: str, color_key: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_colors:
            return text
        return f"{self.COLORS[color_key]}{text}{self.COLORS['RESET']}"

    def load_configmap(self, file_path: Path) -> Dict[str, Any]:
        """Load a Kubernetes ConfigMap YAML file."""
        if not file_path.exists():
            raise FileNotFoundError(f"ConfigMap file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)

            if not content or 'data' not in content:
                raise ValueError(f"Invalid ConfigMap format in {file_path}")

            return content
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file {file_path}: {e}")

    def compare_configmaps(self, old_cm: Dict, new_cm: Dict):
        """
        Compare two ConfigMaps and return added, removed, and modified entries.

        Returns:
            Tuple of (added, removed, modified) dictionaries
        """
        old_data = old_cm.get('data', {})
        new_data = new_cm.get('data', {})

        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())

        added = {k: new_data[k] for k in new_keys - old_keys}
        removed = {k: old_data[k] for k in old_keys - new_keys}

        # Check for modified values
        modified = {}
        for key in old_keys & new_keys:
            old_val = old_data[key]
            new_val = new_data[key]
            if old_val != new_val:
                modified[key] = {
                    'old': old_val,
                    'new': new_val
                }

        return added, removed, modified

    def format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, str):
            # Add quotes if value contains spaces or special characters
            if ' ' in value or value in ('', 'true', 'false', 'null'):
                return f'"{value}"'
            return value
        return str(value)

    def generate_diff_yaml(self, old_cm: Dict, new_cm: Dict,
                          added: Dict, removed: Dict, modified: Dict) -> str:
        """
        Generate a YAML output showing only changes with clear comments.
        """
        lines = []

        # Header
        lines.append("# " + "=" * 70)
        lines.append("# Kubernetes ConfigMap - DIFF Report")
        lines.append("# " + "=" * 70)
        lines.append(f"# Generated: {datetime.now().isoformat()}")
        lines.append(f"# Old ConfigMap: {old_cm.get('metadata', {}).get('name', 'unknown')}")
        lines.append(f"# New ConfigMap: {new_cm.get('metadata', {}).get('name', 'unknown')}")
        lines.append("# " + "=" * 70)
        lines.append("")

        # Summary
        lines.append("# SUMMARY OF CHANGES:")
        lines.append(f"#   Added: {len(added)} new entries")
        lines.append(f"#   Modified: {len(modified)} changed entries")
        lines.append(f"#   Removed: {len(removed)} deleted entries")
        lines.append("# " + "=" * 70)
        lines.append("")

        # Metadata (always show)
        lines.append("apiVersion: v1")
        lines.append("kind: ConfigMap")
        lines.append("metadata:")
        metadata = new_cm.get('metadata', {})
        for key in ['name', 'namespace']:
            if key in metadata:
                lines.append(f"  {key}: {metadata[key]}")

        # Add labels if present
        if 'labels' in metadata:
            lines.append("  labels:")
            for k, v in metadata['labels'].items():
                lines.append(f"    {k}: {v}")

        lines.append("")
        lines.append("data:")

        # Show changes in logical order
        all_keys = sorted(set(list(added.keys()) + list(modified.keys()) + list(removed.keys())))

        if not all_keys:
            lines.append("  # NO CHANGES DETECTED")
            return "\n".join(lines)

        for key in all_keys:
            lines.append("")

            if key in added:
                # NEW ENTRY
                lines.append("  # ========================================")
                lines.append(f"  # ✓ ADDED: {key}")
                lines.append("  # ========================================")
                value = self.format_value(added[key])
                lines.append(f"  {key}: {value}")

            elif key in modified:
                # MODIFIED ENTRY
                lines.append("  # ========================================")
                lines.append(f"  # ⚠ MODIFIED: {key}")
                lines.append(f"  # OLD VALUE: {self.format_value(modified[key]['old'])}")
                lines.append(f"  # NEW VALUE: {self.format_value(modified[key]['new'])}")
                lines.append("  # ========================================")
                value = self.format_value(modified[key]['new'])
                lines.append(f"  {key}: {value}")

            elif key in removed:
                # REMOVED ENTRY
                lines.append("  # ========================================")
                lines.append(f"  # ✗ REMOVED: {key}")
                lines.append(f"  # OLD VALUE: {self.format_value(removed[key])}")
                lines.append("  # ========================================")
                lines.append(f"  # {key}: {self.format_value(removed[key])}  # <-- REMOVED")

        return "\n".join(lines)

    def print_colored_summary(self, added: Dict, removed: Dict, modified: Dict):
        """Print a colored summary to the console."""
        print("\n" + "=" * 70)
        print(self._color("CONFIGMAP SYNC SUMMARY", 'CYAN'))
        print("=" * 70)

        # Added
        if added:
            print(self._color(f"\n✓ ADDED ({len(added)} entries):", 'GREEN'))
            for key in sorted(added.keys()):
                value = self.format_value(added[key])
                print(f"  + {key}: {value}")

        # Modified
        if modified:
            print(self._color(f"\n⚠ MODIFIED ({len(modified)} entries):", 'YELLOW'))
            for key in sorted(modified.keys()):
                old_val = self.format_value(modified[key]['old'])
                new_val = self.format_value(modified[key]['new'])
                print(f"  ~ {key}:")
                print(f"      OLD: {old_val}")
                print(f"      NEW: {new_val}")

        # Removed
        if removed:
            print(self._color(f"\n✗ REMOVED ({len(removed)} entries):", 'RED'))
            for key in sorted(removed.keys()):
                value = self.format_value(removed[key])
                print(f"  - {key}: {value}")

        if not added and not modified and not removed:
            print(self._color("\n✓ NO CHANGES DETECTED", 'GREEN'))

        print("\n" + "=" * 70)

    def sync_k8s_diff(self, old_file: Path, new_file: Path, output_file: Optional[Path] = None):
        """
        Main sync function - compare ConfigMaps and generate diff.
        """
        print(self._color(f"\n[INFO] Loading old ConfigMap: {old_file}", 'BLUE'))
        old_cm = self.load_configmap(old_file)

        print(self._color(f"[INFO] Loading new ConfigMap: {new_file}", 'BLUE'))
        new_cm = self.load_configmap(new_file)

        print(self._color("[INFO] Comparing ConfigMaps...", 'BLUE'))
        added, removed, modified = self.compare_configmaps(old_cm, new_cm)

        # Print colored summary to console
        self.print_colored_summary(added, removed, modified)

        # Generate diff YAML
        diff_yaml = self.generate_diff_yaml(old_cm, new_cm, added, removed, modified)

        # Save to output file
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(diff_yaml)
            print(self._color(f"\n[SUCCESS] Diff saved to: {output_path}", 'GREEN'))
        else:
            # Print to stdout
            print("\n" + "=" * 70)
            print(self._color("DIFF YAML OUTPUT:", 'CYAN'))
            print("=" * 70 + "\n")
            print(diff_yaml)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Environment Deployment Manager for Tammi QA Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/env_deploy.py sync-all
  python scripts/env_deploy.py sync-github --interactive
  python scripts/env_deploy.py sync-k8s
  python scripts/env_deploy.py sync-k8s-diff --old deploy/configmap-full-old.yaml --new deploy/configmap-full.yaml
  python scripts/env_deploy.py list-secrets
  python scripts/env_deploy.py validate
  python scripts/env_deploy.py test-local
        """
    )
    
    parser.add_argument(
        'command',
        choices=['sync-all', 'sync-github', 'sync-k8s', 'sync-k8s-diff', 'list-secrets', 'validate', 'test-local'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Enable interactive mode for GitHub secrets setup'
    )
    
    parser.add_argument(
        '--project-root',
        type=Path,
        help='Project root directory (default: auto-detect)'
    )
    
    # sync-k8s-diff specific arguments
    parser.add_argument(
        '--old',
        type=str,
        default='deploy/configmap-full-old.yaml',
        help='Path to old ConfigMap file (for sync-k8s-diff command)'
    )

    parser.add_argument(
        '--new',
        type=str,
        default='deploy/configmap-full.yaml',
        help='Path to new ConfigMap file (for sync-k8s-diff command)'
    )

    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Output file for diff (for sync-k8s-diff command, optional)'
    )

    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output (for sync-k8s-diff command)'
    )

    args = parser.parse_args()
    
    try:
        # Initialize manager
        manager = EnvDeployManager(args.project_root)
        
        # Execute command
        if args.command == 'sync-all':
            success = manager.sync_all()
            sys.exit(0 if success else 1)
        
        elif args.command == 'sync-github':
            success = manager.sync_github_actions(args.interactive)
            sys.exit(0 if success else 1)
        
        elif args.command == 'sync-k8s':
            success = manager.sync_kubernetes_configmap()
            sys.exit(0 if success else 1)
        
        elif args.command == 'sync-k8s-diff':
            diff_tool = ConfigMapDiff(args.project_root, use_colors=not args.no_color)
            old_path = Path(args.old)
            new_path = Path(args.new)
            output_path = Path(args.output) if args.output else None
            diff_tool.sync_k8s_diff(old_path, new_path, output_path)
            sys.exit(0)

        elif args.command == 'list-secrets':
            manager.list_secrets()
        
        elif args.command == 'validate':
            errors = manager.validate_configuration()
            if errors:
                print("[ERROR] Configuration validation failed:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            else:
                print("[SUCCESS] Configuration is valid!")
                sys.exit(0)
        
        elif args.command == 'test-local':
            success = manager.test_local_environment()
            sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()