"""
Geopolitical Data Caching Layer
Optimizes Lambda performance with intelligent caching
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class GeopoliticalCache:
    def __init__(self):
        # In-memory cache for Lambda execution
        self.memory_cache = {}
        self.cache_ttl = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes default
        
    def get_cached_analysis(self, cache_key: str = 'geopolitical_analysis') -> Optional[Dict]:
        """Get cached geopolitical analysis"""
        try:
            if cache_key in self.memory_cache:
                cached_data = self.memory_cache[cache_key]
                cache_time = datetime.fromisoformat(cached_data['timestamp'])
                
                # Check if cache is still valid
                if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                    logger.info(f"Cache hit for {cache_key}")
                    return cached_data['data']
                else:
                    # Remove expired cache
                    del self.memory_cache[cache_key]
                    logger.info(f"Cache expired for {cache_key}")
            
            logger.info(f"Cache miss for {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None
    
    def cache_analysis(self, data: Dict, cache_key: str = 'geopolitical_analysis') -> bool:
        """Cache geopolitical analysis"""
        try:
            cache_entry = {
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            self.memory_cache[cache_key] = cache_entry
            logger.info(f"Cached analysis for {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")
            return False
    
    def clear_cache(self, cache_key: str = None) -> bool:
        """Clear cache entries"""
        try:
            if cache_key:
                if cache_key in self.memory_cache:
                    del self.memory_cache[cache_key]
                    logger.info(f"Cleared cache for {cache_key}")
            else:
                self.memory_cache.clear()
                logger.info("Cleared all cache")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            return {
                'cache_size': len(self.memory_cache),
                'cache_ttl_seconds': self.cache_ttl,
                'cache_keys': list(self.memory_cache.keys()),
                'memory_usage_mb': self._estimate_memory_usage()
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        try:
            import sys
            total_size = 0
            for key, value in self.memory_cache.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(str(value))
            return round(total_size / (1024 * 1024), 2)
        except:
            return 0.0


class GeopoliticalCacheManager:
    """Enhanced cache manager with multiple strategies"""
    
    def __init__(self):
        self.cache = GeopoliticalCache()
        self.cache_strategies = {
            'memory': self.cache,
            # Future: Add DynamoDB cache here
        }
        
    def get_analysis(self, use_cache: bool = True) -> Optional[Dict]:
        """Get analysis with intelligent caching"""
        if not use_cache:
            return None
            
        # Try memory cache first
        cached_data = self.cache.get_cached_analysis()
        if cached_data:
            return cached_data
            
        # Future: Try DynamoDB cache
        # cached_data = self.dynamodb_cache.get_cached_analysis()
        # if cached_data:
        #     return cached_data
            
        return None
    
    def store_analysis(self, data: Dict, use_cache: bool = True) -> bool:
        """Store analysis with intelligent caching"""
        if not use_cache:
            return False
            
        # Store in memory cache
        success = self.cache.cache_analysis(data)
        
        # Future: Store in DynamoDB cache
        # self.dynamodb_cache.cache_analysis(data)
        
        return success
    
    def invalidate_cache(self) -> bool:
        """Invalidate all caches"""
        return self.cache.clear_cache()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get cache performance metrics"""
        return {
            'cache_stats': self.cache.get_cache_stats(),
            'cache_hit_rate': self._calculate_hit_rate(),
            'last_updated': datetime.now().isoformat()
        }
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate (placeholder for future implementation)"""
        # This would require tracking hits/misses over time
        return 0.0
