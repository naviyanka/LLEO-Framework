from typing import Any, Dict, Optional
from cachetools import TTLCache
from datetime import timedelta
import json
from pathlib import Path
import logging

class CacheManager:
	def __init__(self, cache_dir: Path, ttl: int = 3600):
		self.cache_dir = cache_dir
		self.cache_dir.mkdir(parents=True, exist_ok=True)
		self.memory_cache = TTLCache(maxsize=100, ttl=ttl)
		self.logger = logging.getLogger(__name__)

	def get(self, key: str) -> Optional[Any]:
		"""Get value from cache"""
		return self.memory_cache.get(key)

	def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
		"""Set value in cache"""
		self.memory_cache[key] = value

	def clear(self) -> None:
		"""Clear cache"""
		self.memory_cache.clear()

	def persist(self, filename: str = 'cache.json') -> None:
		"""Persist cache to disk"""
		try:
			cache_file = self.cache_dir / filename
			with open(cache_file, 'w') as f:
				json.dump(dict(self.memory_cache), f)
		except Exception as e:
			self.logger.error(f"Error persisting cache: {e}")

	def load(self, filename: str = 'cache.json') -> None:
		"""Load cache from disk"""
		try:
			cache_file = self.cache_dir / filename
			if cache_file.exists():
				with open(cache_file) as f:
					data = json.load(f)
					self.memory_cache.update(data)
		except Exception as e:
			self.logger.error(f"Error loading cache: {e}")