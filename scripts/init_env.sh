#!/bin/bash

# Guardian Development Environment Setup Script
# ------------------------------------------
# Initializes development environment, installs dependencies,
# and configures pre-commit hooks.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Guardian Development Environment Setup${NC}"
echo "======================================="

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version)
if [[ $? -ne 0 ]]; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi
echo "Found $python_version"

# Create virtual environment
echo -e "\n${YELLOW}Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created new virtual environment"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
echo -e "\n${YELLOW}Setting up pre-commit hooks...${NC}"
pre-commit install
pre-commit install --hook-type pre-push

# Create necessary directories
echo -e "\n${YELLOW}Creating system directories...${NC}"
mkdir -p guardian/memory/jsonl
mkdir -p guardian/memory/sqlite
mkdir -p guardian/logs
mkdir -p guardian/plugins
mkdir -p guardian/temp

# Generate default configuration if needed
echo -e "\n${YELLOW}Checking configuration...${NC}"
if [ ! -f "guardian/config/system_config.py" ]; then
    echo "Creating default configuration..."
    cat > guardian/config/system_config.py << EOL
"""
System Configuration
------------------
Default configuration for Guardian system.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Base directories
BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / 'memory'
PLUGINS_DIR = BASE_DIR / 'plugins'
LOGS_DIR = BASE_DIR / 'logs'
TEMP_DIR = BASE_DIR / 'temp'

# Plugin configuration
PLUGIN_CONFIG = {
    'max_retries': 3,
    'health_check_interval': 300,  # 5 minutes
    'auto_disable_threshold': 5    # Disable after 5 errors
}

# Memory system configuration
MEMORY_CONFIG = {
    'default_backend': 'sqlite',
    'max_query_limit': 1000,
    'retention_days': 30
}

# Logging configuration
LOGGING_CONFIG = {
    'level': logging.INFO,
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': LOGS_DIR / 'guardian.log'
}

def get_path(name: str) -> Path:
    """Get system path by name."""
    paths = {
        'base': BASE_DIR,
        'memory': MEMORY_DIR,
        'plugins': PLUGINS_DIR,
        'logs': LOGS_DIR,
        'temp': TEMP_DIR
    }
    return paths[name]

def get(section: str, key: str) -> Any:
    """Get configuration value."""
    configs = {
        'plugins': PLUGIN_CONFIG,
        'memory': MEMORY_CONFIG,
        'logging': LOGGING_CONFIG
    }
    return configs[section][key]
EOL
fi

# Set up symbolic link for guardianctl
echo -e "\n${YELLOW}Setting up guardianctl command...${NC}"
if [ ! -f "/usr/local/bin/guardianctl" ]; then
    sudo ln -s "$(pwd)/guardian/cli/guardianctl.py" /usr/local/bin/guardianctl
    sudo chmod +x /usr/local/bin/guardianctl
    echo "Created guardianctl command"
else
    echo "guardianctl command already exists"
fi

# Run tests
echo -e "\n${YELLOW}Running tests...${NC}"
python -m pytest tests/

echo -e "\n${GREEN}Setup complete!${NC}"
echo "You can now use 'guardianctl' to manage the Guardian system."
echo "Run 'guardianctl --help' for available commands."
