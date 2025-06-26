"""
Guardian Configuration
-------------------
System-wide configuration and safety settings.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Global configuration settings."""
    
    # Safety and Performance Settings
    SAFE_MODE = True  # Caps plugin usage, enables safety features
    MAX_MODEL_CALLS_PER_MIN = 20  # Rate limit for model API calls
    VERBOSE_LOGGING = False  # Detailed logging output
    COMPACT_LOGGING = True  # Use compact log format
    
    # Cache Settings
    CACHE_ENABLED = True
    CACHE_DIR = Path("guardian/.cache")
    DEFAULT_CACHE_EXPIRE = 3600  # 1 hour
    
    # Plugin Settings
    PLUGIN_TIMEOUT = 30  # seconds
    MAX_CONCURRENT_PLUGINS = 5
    DEFAULT_RATE_LIMIT = 2.0  # calls per second
    SAFE_MODE_RATE_LIMIT = 1.0  # reduced rate in safe mode
    
    # Memory Settings
    MEMORY_BATCH_SIZE = 20  # events per batch
    MEMORY_FLUSH_INTERVAL = 5.0  # seconds
    MAX_MEMORY_BUFFER = 1000  # max events in memory
    
    # System Paths
    BASE_DIR = Path("guardian")
    PLUGIN_DIR = BASE_DIR / "plugins"
    MEMORY_DIR = BASE_DIR / "memory"
    LOG_DIR = BASE_DIR / "logs"
    
    @classmethod
    def load_from_env(cls) -> None:
        """Load settings from environment variables."""
        # Safety settings
        cls.SAFE_MODE = os.getenv("GUARDIAN_SAFE_MODE", "1") == "1"
        cls.MAX_MODEL_CALLS_PER_MIN = int(
            os.getenv("GUARDIAN_MAX_MODEL_CALLS", "20")
        )
        cls.VERBOSE_LOGGING = os.getenv("GUARDIAN_VERBOSE", "0") == "1"
        cls.COMPACT_LOGGING = os.getenv("GUARDIAN_COMPACT_LOGS", "1") == "1"
        
        # Cache settings
        cls.CACHE_ENABLED = os.getenv("GUARDIAN_CACHE_ENABLED", "1") == "1"
        cls.DEFAULT_CACHE_EXPIRE = int(
            os.getenv("GUARDIAN_CACHE_EXPIRE", "3600")
        )
        
        # Plugin settings
        cls.PLUGIN_TIMEOUT = int(os.getenv("GUARDIAN_PLUGIN_TIMEOUT", "30"))
        cls.MAX_CONCURRENT_PLUGINS = int(
            os.getenv("GUARDIAN_MAX_PLUGINS", "5")
        )
        
        # Memory settings
        cls.MEMORY_BATCH_SIZE = int(
            os.getenv("GUARDIAN_MEMORY_BATCH", "20")
        )
        cls.MEMORY_FLUSH_INTERVAL = float(
            os.getenv("GUARDIAN_FLUSH_INTERVAL", "5.0")
        )
    
    @classmethod
    def load_plugin_manifest(cls) -> Optional[Dict[str, Any]]:
        """Load plugin manifest settings."""
        manifest_path = cls.PLUGIN_DIR / "plugin_manifest.json"
        
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
                
            # Update global settings
            global_settings = manifest.get("global_settings", {})
            
            if "default_rate_limit" in global_settings:
                try:
                    rate_str = global_settings["default_rate_limit"]
                    cls.DEFAULT_RATE_LIMIT = float(rate_str.split("/")[0])
                except (ValueError, IndexError):
                    logger.warning(
                        f"Invalid default rate limit: {global_settings['default_rate_limit']}"
                    )
            
            if "safe_mode_rate_limit" in global_settings:
                try:
                    rate_str = global_settings["safe_mode_rate_limit"]
                    cls.SAFE_MODE_RATE_LIMIT = float(rate_str.split("/")[0])
                except (ValueError, IndexError):
                    logger.warning(
                        f"Invalid safe mode rate limit: {global_settings['safe_mode_rate_limit']}"
                    )
            
            if "max_concurrent_plugins" in global_settings:
                cls.MAX_CONCURRENT_PLUGINS = int(
                    global_settings["max_concurrent_plugins"]
                )
            
            if "plugin_timeout_seconds" in global_settings:
                cls.PLUGIN_TIMEOUT = int(
                    global_settings["plugin_timeout_seconds"]
                )
            
            return manifest
            
        except Exception as e:
            logger.error(f"Failed to load plugin manifest: {e}")
            return None
    
    @classmethod
    def initialize(cls) -> None:
        """Initialize configuration and create directories."""
        # Load settings
        cls.load_from_env()
        cls.load_plugin_manifest()
        
        # Create directories
        cls.BASE_DIR.mkdir(parents=True, exist_ok=True)
        cls.PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        cls.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.info("Guardian configuration initialized")
        if cls.SAFE_MODE:
            logger.info("Running in SAFE MODE with restricted capabilities")

# Initialize configuration
Config.initialize()
