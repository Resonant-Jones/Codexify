#!/bin/bash

# Codexify Development Environment Setup Script
# ----------------------------------------------
# Initializes the development environment, installs dependencies,
# sets up pre-commit hooks, and configures the guardianctl command.

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Codexify Development Environment Setup${NC}"
echo "======================================="

# Check Python 3 availability
echo -e "\n${YELLOW}Checking for Python 3...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

python_version=$(python3 --version)
echo "Found $python_version"

# Create virtual environment if it doesn't exist
echo -e "\n${YELLOW}Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
source venv/bin/activate

# Confirm virtual environment activation
echo -e "\n${YELLOW}Virtual environment activated.${NC}"
echo "Using Python interpreter: $(which python)"

# Install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip setuptools wheel

# Ensure pip-tools is installed
if ! pip show pip-tools &> /dev/null; then
    echo "pip-tools not found. Installing pip-tools..."
    pip install pip-tools
else
    echo "pip-tools is already installed."
fi

# Optionally compile .in files if pip-compile is available
if command -v pip-compile &> /dev/null; then
    echo "Compiling requirements/*.in files to requirements/*.txt..."
    for req_in in requirements/*.in; do
        req_txt="requirements/$(basename "${req_in%.*}").txt"
        pip-compile "$req_in" --output-file "$req_txt"
    done
else
    echo "pip-compile not found; skipping requirements compilation."
fi

pip install -r requirements/requirements.txt
pip install -r requirements/requirements-dev.txt

# Setup pre-commit hooks
echo -e "\n${YELLOW}Setting up pre-commit hooks...${NC}"
pre-commit install
pre-commit install --hook-type pre-push

# Create necessary directories
echo -e "\n${YELLOW}Creating required directories...${NC}"
mkdir -p codexify/memory/jsonl
mkdir -p codexify/memory/sqlite
mkdir -p codexify/logs
mkdir -p codexify/plugins
mkdir -p codexify/temp

# Setup guardianctl command
echo -e "\n${YELLOW}Configuring guardianctl command...${NC}"
if [ ! -f "/usr/local/bin/guardianctl" ]; then
    sudo ln -s "$(pwd)/Codexify/guardian/cli/guardianctl.py" /usr/local/bin/guardianctl
    sudo chmod +x /usr/local/bin/guardianctl
    echo "guardianctl command created."
else
    echo "guardianctl command already exists."
fi

# Run tests
echo -e "\n${YELLOW}Running test suite...${NC}"
python -m pytest tests/

echo -e "\n${GREEN}Setup complete!${NC}"
echo "You can now use 'guardianctl' to manage the Guardian system."
echo "Run 'guardianctl --help' for available commands."
