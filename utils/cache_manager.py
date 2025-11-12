import diskcache
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching of processed documents"""
    
    def __init__(self, cache_dir: str, ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = diskcache.Cache(str(self.cache_dir))
        self.ttl_seconds = ttl_hours * 3600
        logger.info(f"CacheManager initialized: {self.cache_dir}, TTL={ttl_hours}h")
    
    def _generate_key(self, file_path: str) -> str:
        """Generate cache key from file path and content hash"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return f"doc_{file_hash}"
        except Exception as e:
            logger.error(f"Error generating cache key: {str(e)}")
            # Fallback to path-based key
            return f"doc_{hashlib.md5(file_path.encode()).hexdigest()}"
    
    def get(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached processed document"""
        try:
            key = self._generate_key(file_path)
            cached_data = self.cache.get(key)
            if cached_data:
                logger.debug(f"Cache hit for {Path(file_path).name}")
            return cached_data
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None
    
    def set(self, file_path: str, processed_data: Dict[str, Any]):
        """Cache processed document"""
        try:
            key = self._generate_key(file_path)
            self.cache.set(key, processed_data, expire=self.ttl_seconds)
            logger.debug(f"Cached document: {Path(file_path).name}")
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
    
    def clear_expired(self):
        """Remove expired cache entries"""
        try:
            # diskcache handles expiration automatically, but we can trigger cleanup
            self.cache.expire()
            logger.info("Cache expiration check completed")
        except Exception as e:
            logger.error(f"Error clearing expired cache: {str(e)}")
    
    def clear_all(self):
        """Clear all cache entries"""
        try:
            self.cache.clear()
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            return {
                "size": len(self.cache),
                "volume": self.cache.volume(),
                "directory": str(self.cache_dir)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "size": 0,
                "volume": 0,
                "directory": str(self.cache_dir),
                "error": str(e)
            }

# Made with Bob
