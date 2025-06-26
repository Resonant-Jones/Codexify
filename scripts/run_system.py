#!/usr/bin/env python3
"""
Threadspace System Runner
-----------------------
Initializes and runs the complete system with monitoring.
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardian.system_init import SystemInitializer
from scripts.system_check import SystemCheck

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemRunner:
    """Manages system lifecycle and monitoring."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.initializer = SystemInitializer()
        self.running = False
        self.start_time = None
        self.stats: Dict[str, Any] = {}
    
    async def start(self) -> None:
        """Start the system."""
        try:
            logger.info("Starting Threadspace system...")
            
            # Run system checks
            await self._run_checks()
            
            # Initialize system
            await self._initialize_system()
            
            # Start monitoring
            self.running = True
            self.start_time = datetime.utcnow()
            await self._monitor_system()
            
        except Exception as e:
            logger.error(f"System start failed: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the system."""
        try:
            logger.info("Stopping Threadspace system...")
            self.running = False
            
            # Cleanup
            await self.initializer.cleanup()
            
            # Print final stats
            self._print_final_stats()
            
        except Exception as e:
            logger.error(f"System stop failed: {e}")
            raise
    
    async def _run_checks(self) -> None:
        """Run system checks."""
        logger.info("Running system checks...")
        
        checker = SystemCheck()
        results = checker.run_checks()
        
        if results['status'] == 'error':
            raise RuntimeError("System checks failed")
        elif results['status'] == 'warning':
            logger.warning("System checks completed with warnings")
        else:
            logger.info("System checks passed")
    
    async def _initialize_system(self) -> None:
        """Initialize system components."""
        logger.info("Initializing system components...")
        
        # Load configuration
        if self.config_path:
            self.initializer.load_config(self.config_path)
        
        # Initialize system
        success = await self.initializer.initialize()
        if not success:
            raise RuntimeError("System initialization failed")
        
        logger.info("System initialized successfully")
    
    async def _monitor_system(self) -> None:
        """Monitor system health and performance."""
        logger.info("Starting system monitoring...")
        
        while self.running:
            try:
                # Get system status
                status = await self.initializer.get_system_status()
                self._update_stats(status)
                
                # Print status
                self._print_status()
                
                # Check for issues
                if status['status'] != 'healthy':
                    logger.warning(f"System status: {status['status']}")
                    if status['status'] == 'error':
                        await self._handle_system_error(status)
                
                # Wait before next check
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)  # Error backoff
    
    def _update_stats(self, status: Dict[str, Any]) -> None:
        """Update system statistics."""
        self.stats = {
            'uptime': self._get_uptime(),
            'status': status['status'],
            'components': {
                name: component['status']
                for name, component in status.get('components', {}).items()
            },
            'metrics': status.get('metrics', {}),
            'memory_usage': status.get('memory_usage', {}),
            'thread_count': status.get('thread_count', 0),
            'plugin_count': status.get('plugin_count', 0),
            'error_count': status.get('error_count', 0)
        }
    
    def _print_status(self) -> None:
        """Print current system status."""
        # Clear screen
        print("\033[2J\033[H")
        
        print("=== Threadspace System Status ===")
        print(f"Uptime: {self.stats['uptime']}")
        print(f"Status: {self.stats['status']}")
        
        print("\nComponents:")
        for name, status in self.stats['components'].items():
            print(f"  {name}: {status}")
        
        print("\nMetrics:")
        for name, value in self.stats['metrics'].items():
            print(f"  {name}: {value}")
        
        print("\nResources:")
        print(f"  Memory: {self.stats['memory_usage']}")
        print(f"  Threads: {self.stats['thread_count']}")
        print(f"  Plugins: {self.stats['plugin_count']}")
        print(f"  Errors: {self.stats['error_count']}")
    
    def _print_final_stats(self) -> None:
        """Print final system statistics."""
        print("\n=== Final System Statistics ===")
        print(f"Total Uptime: {self._get_uptime()}")
        print(f"Final Status: {self.stats['status']}")
        print(f"Total Errors: {self.stats['error_count']}")
        
        if self.stats.get('metrics'):
            print("\nPerformance Metrics:")
            for name, value in self.stats['metrics'].items():
                print(f"  {name}: {value}")
    
    def _get_uptime(self) -> str:
        """Get system uptime."""
        if not self.start_time:
            return "Not started"
        
        delta = datetime.utcnow() - self.start_time
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60
        
        return f"{delta.days}d {hours}h {minutes}m {seconds}s"
    
    async def _handle_system_error(self, status: Dict[str, Any]) -> None:
        """Handle system error state."""
        logger.error(f"System error detected: {status.get('error', 'Unknown error')}")
        
        # Get error details
        error_info = await self.initializer.get_error_info()
        
        # Log error details
        logger.error("Error details:")
        for component, errors in error_info.items():
            for error in errors:
                logger.error(f"  {component}: {error}")
        
        # Check if recovery is possible
        if status.get('recoverable'):
            logger.info("Attempting system recovery...")
            success = await self.initializer.attempt_recovery()
            if success:
                logger.info("System recovery successful")
            else:
                logger.error("System recovery failed")
        else:
            logger.error("System in unrecoverable state")
            await self.stop()

async def main():
    """Run the system."""
    parser = argparse.ArgumentParser(description="Threadspace System Runner")
    parser.add_argument(
        "--config",
        help="Path to configuration file",
        default=None
    )
    args = parser.parse_args()
    
    runner = SystemRunner(args.config)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(runner.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await runner.start()
        
        # Keep running until stopped
        while runner.running:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"System error: {e}")
        await runner.stop()
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
