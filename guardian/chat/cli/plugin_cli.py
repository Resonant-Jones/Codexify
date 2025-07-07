"""
Guardian Plugin-Based CLI
----------------------
Main CLI entrypoint with plugin system integration.
"""

import logging
import os
import sys
from typing import Optional

import click

from ..config_loader import ConfigLoader
from ..memory.memoryos import MemoryOS
from ..memory.codemap import CodemapService
from ..plugin_host import PluginHost

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GuardianCLI:
    """Guardian CLI with plugin system."""
    
    def __init__(self):
        """Initialize Guardian CLI."""
        self.config = ConfigLoader()
        self.memory_os = MemoryOS(
            conversation_token_limit=self.config.get(
                "core.conversation_token_limit",
                90000
            )
        )
        self.codemap = CodemapService()
        
        # Initialize plugin host
        self.plugin_host = PluginHost(
            plugins_dir=self.config.plugins_dir,
            core_services={
                "config": self.config,
                "memory_os": self.memory_os,
                "codemap": self.codemap
            }
        )
        
        # Create CLI group
        self.cli = click.Group()
        
        # Register core commands
        self._register_core_commands()
    
    def _register_core_commands(self) -> None:
        """Register Guardian core CLI commands."""
        
        @self.cli.command("version")
        def version():
            """Show Guardian version."""
            click.echo("Guardian v1.0.0")
        
        @self.cli.command("plugins:list")
        def list_plugins():
            """List available plugins."""
            click.echo("\nGuardian Plugins")
            click.echo("-" * 50)
            
            for plugin in self.plugin_host.list_plugins():
                name = plugin["name"]
                status = plugin["status"]
                version = plugin.get("version", "unknown")
                description = plugin.get("description", "No description")
                
                click.echo(f"\n{name} (v{version})")
                click.echo(f"Status: {status}")
                click.echo(f"Description: {description}")
        
        @self.cli.command("plugins:status")
        def plugin_status():
            """Show detailed plugin status."""
            click.echo("\nGuardian Plugin Status")
            click.echo("-" * 50)
            
            discovered = self.plugin_host.discover_plugins()
            click.echo(f"\nDiscovered Plugins: {len(discovered)}")
            
            active = len([p for p in self.plugin_host.plugin_states.values() if p])
            click.echo(f"Active Plugins: {active}")
            
            click.echo("\nPlugin Details:")
            for plugin in self.plugin_host.list_plugins():
                name = plugin["name"]
                status = plugin["status"]
                error = plugin.get("error")
                
                click.echo(f"\n{name}:")
                click.echo(f"  Status: {status}")
                if error:
                    click.echo(f"  Error: {error}")
    
    def load_plugins(self) -> None:
        """Discover and load enabled plugins."""
        try:
            # Get enabled plugins
            enabled_plugins = self.config.enabled_plugins
            
            # Discover available plugins
            discovered = self.plugin_host.discover_plugins()
            
            # Activate enabled plugins that are available
            for plugin_name in enabled_plugins:
                if plugin_name in discovered:
                    try:
                        self.plugin_host.activate_plugin(plugin_name)
                    except Exception as e:
                        logger.error(f"Failed to activate plugin {plugin_name}: {e}")
            
            # Register plugin CLI commands
            self.plugin_host.register_plugin_cli_commands(self.cli)
            
        except Exception as e:
            logger.error(f"Error loading plugins: {e}")
    
    def run(self) -> None:
        """Run the CLI."""
        try:
            # Load plugins
            self.load_plugins()
            
            # Run CLI
            self.cli()
            
        except Exception as e:
            logger.error(f"CLI error: {e}")
            sys.exit(1)
        finally:
            # Cleanup
            self.plugin_host.shutdown()

def main():
    """CLI entry point."""
    GuardianCLI().run()

if __name__ == "__main__":
    main()
