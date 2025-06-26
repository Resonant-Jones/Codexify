"""
Guardian Cache Module
-------------------
Provides caching decorators and utilities for efficient resource usage.
"""

import functools
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variables for generic function signatures
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')

class CacheConfig:
    """Global cache configuration."""
    CACHE_DIR = Path("guardian/.cache")
    CACHE_ENABLED = True
    DEFAULT_EXPIRE = 3600  # 1 hour
    
    @classmethod
    def ensure_cache_dir(cls) -> None:
        """Ensure cache directory exists."""
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

def hash_args(*args: Any, **kwargs: Any) -> str:
    """
    Generate stable hash for function arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        str: Stable hash of arguments
    """
    # Convert args/kwargs to JSON-serializable format
    arg_dict = {
        'args': args,
        'kwargs': kwargs
    }
    
    # Generate stable hash
    serialized = json.dumps(arg_dict, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()

def memoize_to_disk(expire: int = CacheConfig.DEFAULT_EXPIRE) -> Callable[[F], F]:
    """
    Decorator for disk-persistent JSONL caching with input hashing.
    
    Args:
        expire: Cache expiration time in seconds
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: F) -> F:
        CacheConfig.ensure_cache_dir()
        cache_file = CacheConfig.CACHE_DIR / f"{func.__name__}.jsonl"
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not CacheConfig.CACHE_ENABLED:
                return func(*args, **kwargs)
            
            # Generate cache key
            key = hash_args(*args, **kwargs)
            
            # Check cache file
            if cache_file.exists():
                with open(cache_file) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if (
                                entry['key'] == key and
                                time.time() - entry['timestamp'] < expire
                            ):
                                logger.debug(f"Cache hit for {func.__name__}")
                                return entry['result']
                        except json.JSONDecodeError:
                            continue
            
            # Cache miss - call function
            result = func(*args, **kwargs)
            
            # Store in cache
            entry = {
                'key': key,
                'timestamp': time.time(),
                'result': result
            }
            
            with open(cache_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            
            return result
        
        return wrapper  # type: ignore
    
    return decorator

def lru_cache_safe(
    maxsize: Optional[int] = 128,
    typed: bool = False,
    expire: int = CacheConfig.DEFAULT_EXPIRE
) -> Callable[[F], F]:
    """
    Safe LRU cache decorator with expiration.
    
    Args:
        maxsize: Maximum cache size
        typed: Whether to cache different types separately
        expire: Cache expiration time in seconds
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: F) -> F:
        # Create cache storage
        cache: Dict[str, tuple[Any, float]] = {}
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not CacheConfig.CACHE_ENABLED:
                return func(*args, **kwargs)
            
            # Generate cache key
            key = hash_args(*args, **kwargs)
            
            # Check cache
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < expire:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
                else:
                    del cache[key]
            
            # Cache miss
            result = func(*args, **kwargs)
            
            # Store in cache
            cache[key] = (result, time.time())
            
            # Enforce maxsize
            if maxsize and len(cache) > maxsize:
                # Remove oldest entry
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                del cache[oldest_key]
            
            return result
        
        return wrapper  # type: ignore
    
    return decorator

def semantic_cache(query: str) -> Optional[Any]:
    """
    Placeholder for semantic caching using embeddings.
    
    Args:
        query: Query string to match
        
    Returns:
        Optional[Any]: Cached result if found
    """
    # TODO: Implement semantic caching using embeddings
    return None
