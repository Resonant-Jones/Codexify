"""
System Diagnostic Checklist
-------------------------
Verifies system configuration and readiness for operation.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemCheck:
    """System configuration and readiness verification."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.results: Dict[str, Any] = {
            'status': 'pending',
            'checks': {},
            'errors': [],
            'warnings': []
        }
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all system checks."""
        try:
            logger.info("Starting system checks...")
            
            # Core files check
            self._check_core_files()
            
            # Configuration check
            self._check_configuration()
            
            # Plugin check
            self._check_plugins()
            
            # Documentation check
            self._check_documentation()
            
            # Development setup check
            self._check_development_setup()
            
            # Test suite check
            self._check_test_suite()
            
            # Set final status
            self._set_final_status()
            
            return self.results
            
        except Exception as e:
            logger.error(f"System check failed: {e}")
            self.results['status'] = 'error'
            self.results['errors'].append(str(e))
            return self.results
    
    def _check_core_files(self) -> None:
        """Check core system files."""
        logger.info("Checking core files...")
        
        core_files = [
            'guardian/system_init.py',
            'guardian/codex_awareness.py',
            'guardian/metacognition.py',
            'guardian/plugin_loader.py',
            'guardian/threads/thread_manager.py',
            'guardian/agents/vestige.py',
            'guardian/agents/axis.py',
            'guardian/agents/echoform.py'
        ]
        
        missing_files = []
        for file in core_files:
            if not (self.root_dir / file).exists():
                missing_files.append(file)
        
        self.results['checks']['core_files'] = {
            'status': 'error' if missing_files else 'success',
            'missing_files': missing_files
        }
        
        if missing_files:
            self.results['errors'].append(
                f"Missing core files: {', '.join(missing_files)}"
            )
    
    def _check_configuration(self) -> None:
        """Check system configuration."""
        logger.info("Checking configuration...")
        
        config_files = [
            '.env.template',
            'guardian/config/system_config.py',
            'setup.py',
            'requirements.txt'
        ]
        
        missing_configs = []
        for file in config_files:
            if not (self.root_dir / file).exists():
                missing_configs.append(file)
        
        # Check .env.template content
        env_issues = []
        env_path = self.root_dir / '.env.template'
        if env_path.exists():
            required_vars = [
                'THREADSPACE_ENV',
                'LOG_LEVEL',
                'SYSTEM_NAME',
                'PLUGIN_DIR'
            ]
            
            with open(env_path, 'r') as f:
                content = f.read()
                for var in required_vars:
                    if var not in content:
                        env_issues.append(f"Missing {var}")
        
        self.results['checks']['configuration'] = {
            'status': 'error' if missing_configs or env_issues else 'success',
            'missing_configs': missing_configs,
            'env_issues': env_issues
        }
        
        if missing_configs:
            self.results['errors'].append(
                f"Missing configuration files: {', '.join(missing_configs)}"
            )
        if env_issues:
            self.results['warnings'].extend(env_issues)
    
    def _check_plugins(self) -> None:
        """Check plugin system."""
        logger.info("Checking plugins...")
        
        plugins_dir = self.root_dir / 'plugins'
        if not plugins_dir.exists():
            self.results['errors'].append("Plugins directory not found")
            self.results['checks']['plugins'] = {'status': 'error'}
            return
        
        plugin_issues = []
        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir() and not plugin_dir.name.startswith('__'):
                # Check plugin structure
                required_files = [
                    'plugin.json',
                    'main.py'
                ]
                
                for file in required_files:
                    if not (plugin_dir / file).exists():
                        plugin_issues.append(
                            f"Missing {file} in {plugin_dir.name}"
                        )
                
                # Check plugin.json content
                try:
                    with open(plugin_dir / 'plugin.json', 'r') as f:
                        config = json.load(f)
                        required_fields = [
                            'name',
                            'version',
                            'description',
                            'capabilities',
                            'config'
                        ]
                        for field in required_fields:
                            if field not in config:
                                plugin_issues.append(
                                    f"Missing {field} in {plugin_dir.name}/plugin.json"
                                )
                except Exception as e:
                    plugin_issues.append(
                        f"Invalid plugin.json in {plugin_dir.name}: {e}"
                    )
        
        self.results['checks']['plugins'] = {
            'status': 'error' if plugin_issues else 'success',
            'issues': plugin_issues
        }
        
        if plugin_issues:
            self.results['warnings'].extend(plugin_issues)
    
    def _check_documentation(self) -> None:
        """Check documentation files."""
        logger.info("Checking documentation...")
        
        doc_files = [
            'README.md',
            'CONTRIBUTING.md',
            'CODE_OF_CONDUCT.md',
            'CHANGELOG.md',
            'LICENSE',
            'docs/plugin_development.md',
            'docs/system_architecture.md'
        ]
        
        missing_docs = []
        for file in doc_files:
            if not (self.root_dir / file).exists():
                missing_docs.append(file)
        
        self.results['checks']['documentation'] = {
            'status': 'error' if missing_docs else 'success',
            'missing_docs': missing_docs
        }
        
        if missing_docs:
            self.results['warnings'].append(
                f"Missing documentation files: {', '.join(missing_docs)}"
            )
    
    def _check_development_setup(self) -> None:
        """Check development setup."""
        logger.info("Checking development setup...")
        
        dev_files = [
            '.pre-commit-config.yaml',
            'Makefile',
            '.github/ISSUE_TEMPLATE/bug_report.md',
            '.github/ISSUE_TEMPLATE/feature_request.md',
            '.github/pull_request_template.md'
        ]
        
        missing_files = []
        for file in dev_files:
            if not (self.root_dir / file).exists():
                missing_files.append(file)
        
        # Check Makefile targets
        makefile_issues = []
        makefile_path = self.root_dir / 'Makefile'
        if makefile_path.exists():
            required_targets = [
                'install',
                'test',
                'lint',
                'format',
                'clean'
            ]
            
            with open(makefile_path, 'r') as f:
                content = f.read()
                for target in required_targets:
                    if f"{target}:" not in content:
                        makefile_issues.append(f"Missing target: {target}")
        
        self.results['checks']['development'] = {
            'status': 'error' if missing_files or makefile_issues else 'success',
            'missing_files': missing_files,
            'makefile_issues': makefile_issues
        }
        
        if missing_files:
            self.results['warnings'].append(
                f"Missing development files: {', '.join(missing_files)}"
            )
        if makefile_issues:
            self.results['warnings'].extend(makefile_issues)
    
    def _check_test_suite(self) -> None:
        """Check test suite."""
        logger.info("Checking test suite...")
        
        test_files = [
            'tests/test_system_integration.py',
            'tests/test_agents_and_plugins.py',
            'tests/run_tests.py'
        ]
        
        missing_tests = []
        for file in test_files:
            if not (self.root_dir / file).exists():
                missing_tests.append(file)
        
        # Check plugin tests
        plugins_dir = self.root_dir / 'plugins'
        if plugins_dir.exists():
            for plugin_dir in plugins_dir.iterdir():
                if plugin_dir.is_dir() and not plugin_dir.name.startswith('__'):
                    test_dir = plugin_dir / 'tests'
                    if not test_dir.exists() or not any(test_dir.iterdir()):
                        missing_tests.append(
                            f"Missing tests for plugin: {plugin_dir.name}"
                        )
        
        self.results['checks']['tests'] = {
            'status': 'error' if missing_tests else 'success',
            'missing_tests': missing_tests
        }
        
        if missing_tests:
            self.results['warnings'].append(
                f"Missing test files: {', '.join(missing_tests)}"
            )
    
    def _set_final_status(self) -> None:
        """Set final system status."""
        if self.results['errors']:
            self.results['status'] = 'error'
        elif self.results['warnings']:
            self.results['status'] = 'warning'
        else:
            self.results['status'] = 'success'
    
    def print_results(self) -> None:
        """Print check results."""
        print("\n=== System Check Results ===")
        print(f"Status: {self.results['status'].upper()}")
        
        print("\nChecks:")
        for check, result in self.results['checks'].items():
            print(f"\n{check}:")
            print(f"  Status: {result['status']}")
            for key, value in result.items():
                if key != 'status' and value:
                    print(f"  {key}: {value}")
        
        if self.results['errors']:
            print("\nErrors:")
            for error in self.results['errors']:
                print(f"  - {error}")
        
        if self.results['warnings']:
            print("\nWarnings:")
            for warning in self.results['warnings']:
                print(f"  - {warning}")

def main():
    """Run system checks."""
    checker = SystemCheck()
    results = checker.run_checks()
    checker.print_results()
    
    # Exit with appropriate status code
    if results['status'] == 'error':
        sys.exit(1)
    elif results['status'] == 'warning':
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":
    main()
