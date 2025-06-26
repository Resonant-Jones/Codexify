"""
Threadspace System Demo
---------------------
Demonstrates full system lifecycle and component integration.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardian.codex_awareness import CodexAwareness
from guardian.metacognition import MetacognitionEngine
from guardian.plugin_loader import PluginLoader
from guardian.system_init import SystemInitializer
from guardian.threads.thread_manager import ThreadManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemDemo:
    """Demonstrates system functionality."""
    
    def __init__(self):
        self.initializer = SystemInitializer()
        self.thread_manager = ThreadManager()
        self.plugin_loader = PluginLoader()
        self.codex = CodexAwareness()
        self.metacognition = MetacognitionEngine()
    
    async def run_demo(self):
        """Run the system demonstration."""
        try:
            logger.info("Starting Threadspace System Demo")
            
            # 1. System Initialization
            logger.info("\n=== System Initialization ===")
            await self._init_system()
            
            # 2. Plugin Loading
            logger.info("\n=== Plugin Loading ===")
            await self._load_plugins()
            
            # 3. Agent Initialization
            logger.info("\n=== Agent Initialization ===")
            await self._init_agents()
            
            # 4. Memory Operations
            logger.info("\n=== Memory Operations ===")
            await self._demo_memory_ops()
            
            # 5. Plugin Operations
            logger.info("\n=== Plugin Operations ===")
            await self._demo_plugin_ops()
            
            # 6. System Monitoring
            logger.info("\n=== System Monitoring ===")
            await self._monitor_system()
            
            # 7. Error Handling
            logger.info("\n=== Error Handling ===")
            await self._demo_error_handling()
            
            # 8. System Status
            logger.info("\n=== System Status ===")
            await self._check_system_status()
            
            logger.info("\nDemo completed successfully!")
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            raise
    
    async def _init_system(self):
        """Initialize system components."""
        try:
            logger.info("Initializing system components...")
            
            # Initialize core system
            success = await self.initializer.initialize()
            logger.info(f"System initialization: {'Success' if success else 'Failed'}")
            
            # Load configuration
            config = self.initializer.get_config()
            logger.info(f"Loaded configuration: {len(config)} settings")
            
            # Initialize thread manager
            self.thread_manager.initialize()
            logger.info("Thread manager initialized")
            
            # Initialize memory system
            self.codex.initialize()
            logger.info("Memory system initialized")
            
            # Initialize metacognition
            self.metacognition.initialize()
            logger.info("Metacognition system initialized")
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            raise
    
    async def _load_plugins(self):
        """Load and initialize plugins."""
        try:
            logger.info("Loading plugins...")
            
            # Load all plugins
            plugin_count = self.plugin_loader.load_all_plugins()
            logger.info(f"Loaded {plugin_count} plugins")
            
            # Verify plugin health
            for plugin_name, plugin in self.plugin_loader.plugins.items():
                health = plugin.health_check()
                logger.info(f"Plugin {plugin_name}: {health['status']}")
            
        except Exception as e:
            logger.error(f"Plugin loading failed: {e}")
            raise
    
    async def _init_agents(self):
        """Initialize system agents."""
        try:
            logger.info("Initializing agents...")
            
            # Get agent status
            agents = self.thread_manager.get_agents()
            for agent in agents:
                status = await agent.get_status()
                logger.info(f"Agent {agent.name}: {status['status']}")
            
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            raise
    
    async def _demo_memory_ops(self):
        """Demonstrate memory operations."""
        try:
            logger.info("Demonstrating memory operations...")
            
            # Store test memory
            memory_id = self.codex.store_memory(
                content={
                    'type': 'test_memory',
                    'data': 'Hello, Threadspace!',
                    'timestamp': datetime.utcnow().isoformat()
                },
                source='demo',
                tags=['test', 'demo'],
                confidence=1.0
            )
            logger.info(f"Stored memory: {memory_id}")
            
            # Query memory
            memory = self.codex.query_memory(memory_id)
            logger.info(f"Retrieved memory: {memory}")
            
            # Pattern analysis
            patterns = await self.codex.analyze_patterns()
            logger.info(f"Found {len(patterns)} patterns")
            
        except Exception as e:
            logger.error(f"Memory operations failed: {e}")
            raise
    
    async def _demo_plugin_ops(self):
        """Demonstrate plugin operations."""
        try:
            logger.info("Demonstrating plugin operations...")
            
            # Get system diagnostics plugin
            diagnostics = self.plugin_loader.get_plugin('system_diagnostics')
            if diagnostics:
                # Run diagnostics
                results = await diagnostics.run_diagnostics()
                logger.info(f"Diagnostic results: {json.dumps(results, indent=2)}")
            
            # Get pattern analyzer plugin
            analyzer = self.plugin_loader.get_plugin('pattern_analyzer')
            if analyzer:
                # Analyze patterns
                patterns = await analyzer.analyze_patterns()
                logger.info(f"Pattern analysis: {len(patterns)} patterns found")
            
        except Exception as e:
            logger.error(f"Plugin operations failed: {e}")
            raise
    
    async def _monitor_system(self):
        """Monitor system health and performance."""
        try:
            logger.info("Monitoring system...")
            
            # Get thread status
            thread_info = self.thread_manager.get_thread_info()
            logger.info(f"Thread status: {thread_info}")
            
            # Get memory usage
            memory_info = self.thread_manager.get_memory_info()
            logger.info(f"Memory usage: {memory_info}")
            
            # Get performance metrics
            metrics = self.thread_manager.get_performance_metrics()
            logger.info(f"Performance metrics: {metrics}")
            
        except Exception as e:
            logger.error(f"System monitoring failed: {e}")
            raise
    
    async def _demo_error_handling(self):
        """Demonstrate error handling capabilities."""
        try:
            logger.info("Demonstrating error handling...")
            
            # Simulate error condition
            try:
                raise Exception("Test error")
            except Exception as e:
                await self.metacognition.handle_error(
                    error=e,
                    context={'source': 'demo'}
                )
                logger.info("Error handled successfully")
            
            # Check error recovery
            recovery_status = await self.metacognition.check_recovery_status()
            logger.info(f"Recovery status: {recovery_status}")
            
        except Exception as e:
            logger.error(f"Error handling demo failed: {e}")
            raise
    
    async def _check_system_status(self):
        """Check overall system status."""
        try:
            logger.info("Checking system status...")
            
            # Get system health
            health = await self.initializer.health_check()
            logger.info(f"System health: {health['status']}")
            
            # Get component status
            components = await self.initializer.get_component_status()
            logger.info("Component status:")
            for component, status in components.items():
                logger.info(f"  {component}: {status['status']}")
            
            # Get system metrics
            metrics = await self.initializer.get_system_metrics()
            logger.info(f"System metrics: {metrics}")
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            raise

async def main():
    """Run the system demonstration."""
    try:
        demo = SystemDemo()
        await demo.run_demo()
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise

if __name__ == "__main__":
    # Run demo
    asyncio.run(main())
