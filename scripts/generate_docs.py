#!/usr/bin/env python3
"""
Documentation Generator
---------------------
Generates comprehensive system documentation from codebase.
"""

import ast
import inspect
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DocGenerator:
    """Documentation generator for the system."""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.docs_dir = self.root_dir / 'docs'
        self.output_dir = self.docs_dir / 'generated'
        
        # Documentation sections
        self.sections = {
            'overview': 'System Overview',
            'architecture': 'System Architecture',
            'components': 'Core Components',
            'plugins': 'Plugin System',
            'agents': 'Agent System',
            'api': 'API Reference',
            'deployment': 'Deployment Guide'
        }
    
    def generate_docs(self) -> None:
        """Generate all documentation."""
        try:
            logger.info("Generating system documentation...")
            
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate documentation sections
            self._generate_overview()
            self._generate_architecture()
            self._generate_components()
            self._generate_plugins()
            self._generate_agents()
            self._generate_api()
            self._generate_deployment()
            
            # Generate index
            self._generate_index()
            
            logger.info("Documentation generation complete")
            
        except Exception as e:
            logger.error(f"Documentation generation failed: {e}")
            raise
    
    def _generate_overview(self) -> None:
        """Generate system overview documentation."""
        content = [
            "# System Overview\n",
            "## Introduction\n",
            "Threadspace is a modular, extensible system designed for advanced "
            "thread management and plugin-based functionality.\n",
            
            "## Key Features\n",
            "- Modular architecture with plugin support\n",
            "- Advanced thread management\n",
            "- Memory system with pattern recognition\n",
            "- Agent-based decision making\n",
            "- Comprehensive monitoring and diagnostics\n",
            
            "## System Components\n",
            "1. GuardianOS - Core system management\n",
            "2. Thread Manager - Thread lifecycle and monitoring\n",
            "3. Plugin System - Extensible functionality\n",
            "4. Memory System - Data management and analysis\n",
            "5. Agent System - Autonomous operations\n",
            
            "## Getting Started\n",
            "```bash\n",
            "# Install dependencies\n",
            "make install\n\n",
            "# Run system checks\n",
            "python scripts/system_check.py\n\n",
            "# Start the system\n",
            "python scripts/run_system.py\n",
            "```\n"
        ]
        
        self._write_doc('overview', content)
    
    def _generate_architecture(self) -> None:
        """Generate architecture documentation."""
        content = [
            "# System Architecture\n",
            
            "## High-Level Architecture\n",
            "```mermaid\n",
            "graph TB\n",
            "    Client[Client Applications] --> API[System API]\n",
            "    API --> Guardian[GuardianOS]\n",
            "    Guardian --> Components[Core Components]\n",
            "    Guardian --> Plugins[Plugin System]\n",
            "    Guardian --> Agents[Agent System]\n",
            "```\n",
            
            "## Core Components\n",
            "### GuardianOS\n",
            "Central system orchestrator managing:\n",
            "- System initialization\n",
            "- Component lifecycle\n",
            "- Resource management\n",
            "- Error handling\n",
            
            "### Thread Manager\n",
            "Handles:\n",
            "- Thread creation and lifecycle\n",
            "- Resource allocation\n",
            "- Performance monitoring\n",
            "- Thread synchronization\n",
            
            "### Plugin System\n",
            "Provides:\n",
            "- Dynamic plugin loading\n",
            "- Plugin isolation\n",
            "- Resource management\n",
            "- Plugin communication\n",
            
            "### Memory System\n",
            "Manages:\n",
            "- Data storage and retrieval\n",
            "- Pattern recognition\n",
            "- Memory optimization\n",
            "- Data analysis\n",
            
            "## System Flow\n",
            "```mermaid\n",
            "sequenceDiagram\n",
            "    participant C as Client\n",
            "    participant G as GuardianOS\n",
            "    participant T as Thread Manager\n",
            "    participant P as Plugins\n",
            "    participant A as Agents\n",
            "    \n",
            "    C->>G: Request\n",
            "    G->>T: Allocate Resources\n",
            "    T->>P: Execute Plugins\n",
            "    P->>A: Process Data\n",
            "    A->>G: Return Results\n",
            "    G->>C: Response\n",
            "```\n"
        ]
        
        self._write_doc('architecture', content)
    
    def _generate_components(self) -> None:
        """Generate component documentation."""
        components = self._analyze_components()
        
        content = [
            "# Core Components\n",
            
            "## Component Overview\n",
            "Detailed documentation of core system components.\n\n"
        ]
        
        for name, info in components.items():
            content.extend([
                f"## {name}\n",
                f"{info['docstring']}\n\n",
                "### Methods\n"
            ])
            
            for method in info['methods']:
                content.extend([
                    f"#### `{method['name']}`\n",
                    f"{method['docstring']}\n",
                    "```python\n",
                    f"{method['signature']}\n",
                    "```\n\n"
                ])
        
        self._write_doc('components', content)
    
    def _generate_plugins(self) -> None:
        """Generate plugin documentation."""
        plugins = self._analyze_plugins()
        
        content = [
            "# Plugin System\n",
            
            "## Overview\n",
            "Documentation for the plugin system and available plugins.\n\n",
            
            "## Plugin Architecture\n",
            "```mermaid\n",
            "graph TB\n",
            "    Loader[Plugin Loader] --> Registry[Plugin Registry]\n",
            "    Registry --> Plugins[Active Plugins]\n",
            "    Plugins --> Resources[System Resources]\n",
            "```\n\n"
        ]
        
        for name, info in plugins.items():
            content.extend([
                f"## {name}\n",
                f"{info['description']}\n\n",
                "### Configuration\n",
                "```json\n",
                f"{json.dumps(info['config'], indent=2)}\n",
                "```\n\n",
                "### Capabilities\n"
            ])
            
            for capability in info['capabilities']:
                content.append(f"- {capability}\n")
            
            content.append("\n")
        
        self._write_doc('plugins', content)
    
    def _generate_agents(self) -> None:
        """Generate agent documentation."""
        agents = self._analyze_agents()
        
        content = [
            "# Agent System\n",
            
            "## Overview\n",
            "Documentation for the autonomous agent system.\n\n",
            
            "## Agent Architecture\n",
            "```mermaid\n",
            "graph TB\n",
            "    Vestige[Vestige Agent] --> Memory[Memory System]\n",
            "    Axis[Axis Agent] --> Decision[Decision Engine]\n",
            "    Echoform[Echoform Agent] --> State[State Manager]\n",
            "```\n\n"
        ]
        
        for name, info in agents.items():
            content.extend([
                f"## {name}\n",
                f"{info['docstring']}\n\n",
                "### Capabilities\n"
            ])
            
            for capability in info['capabilities']:
                content.append(f"- {capability}\n")
            
            content.extend([
                "\n### Methods\n"
            ])
            
            for method in info['methods']:
                content.extend([
                    f"#### `{method['name']}`\n",
                    f"{method['docstring']}\n",
                    "```python\n",
                    f"{method['signature']}\n",
                    "```\n\n"
                ])
        
        self._write_doc('agents', content)
    
    def _generate_api(self) -> None:
        """Generate API documentation."""
        content = [
            "# API Reference\n",
            
            "## Overview\n",
            "Complete API reference for system interaction.\n\n",
            
            "## Core API\n",
            
            "### System Management\n",
            "```python\n",
            "# Initialize system\n",
            "system = SystemInitializer()\n",
            "await system.initialize()\n",
            "\n",
            "# Get system status\n",
            "status = await system.get_system_status()\n",
            "```\n",
            
            "### Thread Management\n",
            "```python\n",
            "# Create thread\n",
            "thread_id = thread_manager.create_thread(\n",
            "    name='worker',\n",
            "    target=worker_function\n",
            ")\n",
            "\n",
            "# Monitor thread\n",
            "info = thread_manager.get_thread_info(thread_id)\n",
            "```\n",
            
            "### Plugin Management\n",
            "```python\n",
            "# Load plugin\n",
            "plugin = plugin_loader.load_plugin('plugin_name')\n",
            "\n",
            "# Execute plugin\n",
            "result = await plugin.execute(data)\n",
            "```\n",
            
            "### Memory Operations\n",
            "```python\n",
            "# Store memory\n",
            "memory_id = codex.store_memory(\n",
            "    content=data,\n",
            "    source='application',\n",
            "    tags=['important']\n",
            ")\n",
            "\n",
            "# Query memory\n",
            "result = codex.query_memory(memory_id)\n",
            "```\n",
            
            "### Agent Interaction\n",
            "```python\n",
            "# Process with Vestige\n",
            "result = await vestige.process_memory(\n",
            "    memory_id,\n",
            "    context={}\n",
            ")\n",
            "\n",
            "# Make decision with Axis\n",
            "decision = await axis.make_decision(\n",
            "    decision_type='action',\n",
            "    context={},\n",
            "    options=[]\n",
            ")\n",
            "```\n"
        ]
        
        self._write_doc('api', content)
    
    def _generate_deployment(self) -> None:
        """Generate deployment documentation."""
        content = [
            "# Deployment Guide\n",
            
            "## Requirements\n",
            "- Python 3.8 or higher\n",
            "- Required packages (see requirements.txt)\n",
            "- Sufficient system resources\n",
            
            "## Installation\n",
            "```bash\n",
            "# Clone repository\n",
            "git clone https://github.com/threadspace/threadspace.git\n",
            "cd threadspace\n",
            "\n",
            "# Create virtual environment\n",
            "python -m venv venv\n",
            "source venv/bin/activate  # Linux/Mac\n",
            "# venv\\Scripts\\activate  # Windows\n",
            "\n",
            "# Install dependencies\n",
            "make install\n",
            "```\n",
            
            "## Configuration\n",
            "1. Copy `.env.template` to `.env`\n",
            "2. Configure environment variables\n",
            "3. Adjust system settings in `config/`\n",
            
            "## Running the System\n",
            "```bash\n",
            "# Run system checks\n",
            "python scripts/system_check.py\n",
            "\n",
            "# Start the system\n",
            "python scripts/run_system.py\n",
            "```\n",
            
            "## Monitoring\n",
            "- Check system status: `http://localhost:8000/status`\n",
            "- View metrics: `http://localhost:9090`\n",
            "- Check logs: `tail -f logs/system.log`\n",
            
            "## Troubleshooting\n",
            "1. Check system logs\n",
            "2. Run diagnostics plugin\n",
            "3. Check component status\n",
            "4. Verify configuration\n",
            
            "## Security\n",
            "- Keep system updated\n",
            "- Monitor access logs\n",
            "- Regular security audits\n",
            "- Follow security guidelines\n"
        ]
        
        self._write_doc('deployment', content)
    
    def _generate_index(self) -> None:
        """Generate documentation index."""
        content = [
            "# System Documentation\n",
            f"Generated: {datetime.utcnow().isoformat()}\n\n",
            "## Contents\n"
        ]
        
        for section, title in self.sections.items():
            content.append(f"- [{title}]({section}.md)\n")
        
        self._write_doc('index', content)
    
    def _analyze_components(self) -> Dict[str, Any]:
        """Analyze core components."""
        components = {}
        
        component_files = [
            ('GuardianOS', 'guardian/system_init.py'),
            ('ThreadManager', 'guardian/threads/thread_manager.py'),
            ('PluginLoader', 'guardian/plugin_loader.py'),
            ('CodexAwareness', 'guardian/codex_awareness.py'),
            ('MetacognitionEngine', 'guardian/metacognition.py')
        ]
        
        for name, path in component_files:
            file_path = self.root_dir / path
            if file_path.exists():
                components[name] = self._analyze_python_file(file_path)
        
        return components
    
    def _analyze_plugins(self) -> Dict[str, Any]:
        """Analyze plugins."""
        plugins = {}
        plugins_dir = self.root_dir / 'plugins'
        
        if plugins_dir.exists():
            for plugin_dir in plugins_dir.iterdir():
                if plugin_dir.is_dir() and not plugin_dir.name.startswith('__'):
                    config_file = plugin_dir / 'plugin.json'
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            plugins[plugin_dir.name] = json.load(f)
        
        return plugins
    
    def _analyze_agents(self) -> Dict[str, Any]:
        """Analyze agents."""
        agents = {}
        agents_dir = self.root_dir / 'guardian/agents'
        
        if agents_dir.exists():
            for agent_file in agents_dir.glob('*.py'):
                if not agent_file.name.startswith('__'):
                    agents[agent_file.stem] = self._analyze_python_file(agent_file)
        
        return agents
    
    def _analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Python source file."""
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        result = {
            'docstring': ast.get_docstring(tree) or 'No description available.',
            'methods': []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                method = {
                    'name': node.name,
                    'docstring': ast.get_docstring(node) or 'No description available.',
                    'signature': self._get_function_signature(node)
                }
                result['methods'].append(method)
        
        return result
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature as string."""
        args = []
        
        # Add arguments
        for arg in node.args.args:
            args.append(arg.arg)
        
        # Add *args if present
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        
        # Add **kwargs if present
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        
        return f"def {node.name}({', '.join(args)}):"
    
    def _write_doc(self, name: str, content: List[str]) -> None:
        """Write documentation file."""
        output_file = self.output_dir / f"{name}.md"
        with open(output_file, 'w') as f:
            f.writelines(content)
        logger.info(f"Generated {name} documentation")

def main():
    """Generate system documentation."""
    try:
        generator = DocGenerator()
        generator.generate_docs()
    except Exception as e:
        logger.error(f"Documentation generation failed: {e}")
        raise

if __name__ == "__main__":
    main()
