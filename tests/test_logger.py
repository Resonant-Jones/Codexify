"""
Test Logger Module
---------------
Test-specific logger implementation with async support.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

pytestmark = pytest.mark.asyncio

from guardian.config import Config
from guardian.utils.safeguard import throttle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestLogger:
    """Simple test logger with rate limiting."""
    
    def __init__(self, name: str, log_dir: Optional[Path] = None):
        """Initialize test logger."""
        self.name = name
        self.log_dir = log_dir or Path("test_logs") / name
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.buffer: List[Dict[str, Any]] = []
    
    @throttle(rate=10.0)
    async def log(self, message: str, level: str = "INFO", **kwargs: Any) -> None:
        """Log a message with rate limiting."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
        
        self.buffer.append(event)
        
        # Write immediately for testing
        log_file = self.log_dir / f"{self.name}.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(event) + '\n')
    
    async def info(self, message: str, **kwargs: Any) -> None:
        """Log INFO level message."""
        await self.log(message, "INFO", **kwargs)
    
    async def warning(self, message: str, **kwargs: Any) -> None:
        """Log WARNING level message."""
        await self.log(message, "WARNING", **kwargs)
    
    async def error(self, message: str, **kwargs: Any) -> None:
        """Log ERROR level message."""
        await self.log(message, "ERROR", **kwargs)
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """Get all logged events."""
        return self.buffer.copy()
    
    async def cleanup(self) -> None:
        """Clean up test logs."""
        for file in self.log_dir.glob("*.jsonl"):
            file.unlink()
        self.log_dir.rmdir()
