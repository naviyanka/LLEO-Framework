import asyncio
import time
from typing import Optional, Dict, List
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta

@dataclass
class RateLimitConfig:
    calls_per_second: int = 10
    burst_size: int = 100
    min_interval: float = 0.1
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class RateLimitStats:
    total_requests: int = 0
    throttled_requests: int = 0
    last_reset: float = time.monotonic()
    intervals: List[float] = None

    def __post_init__(self):
        self.intervals = []

class RateLimiter:
    def __init__(self, calls_per_second: int = 10, burst_size: Optional[int] = None):
        self.config = RateLimitConfig(
            calls_per_second=calls_per_second,
            burst_size=burst_size or calls_per_second
        )
        self.tokens = self.config.burst_size
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger('RateLimiter')
        self.stats = RateLimitStats()
        self._monitoring_task = None

    async def start_monitoring(self):
        """Start monitoring task"""
        if not self._monitoring_task:
            self._monitoring_task = asyncio.create_task(self._monitor_usage())

    async def stop_monitoring(self):
        """Stop monitoring task"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

    async def _monitor_usage(self):
        """Monitor rate limit usage"""
        while True:
            await asyncio.sleep(60)  # Monitor every minute
            now = time.monotonic()
            if now - self.stats.last_reset >= 3600:  # Reset stats every hour
                self._reset_stats()
            
            if self.stats.throttled_requests > 0:
                throttle_rate = self.stats.throttled_requests / self.stats.total_requests
                if throttle_rate > 0.2:  # More than 20% requests throttled
                    self.logger.warning(
                        f"High throttle rate: {throttle_rate:.2%}. "
                        f"Consider adjusting rate limits."
                    )

    def _reset_stats(self):
        """Reset monitoring statistics"""
        self.stats = RateLimitStats()

    async def acquire(self, tokens: int = 1, retry: bool = True) -> bool:
        """Acquire tokens respecting rate limits with retry support"""
        self.stats.total_requests += 1
        
        for attempt in range(self.config.max_retries if retry else 1):
            try:
                async with self.lock:
                    await self._add_new_tokens()
                    
                    if self.tokens >= tokens:
                        self.tokens -= tokens
                        if self.stats.intervals:
                            self.stats.intervals.append(
                                time.monotonic() - self.stats.intervals[-1]
                            )
                        else:
                            self.stats.intervals.append(time.monotonic())
                        return True
                    
                    wait_time = self._time_to_tokens(tokens)
                    if wait_time > 0:
                        self.stats.throttled_requests += 1
                        if attempt < self.config.max_retries - 1:
                            await asyncio.sleep(min(wait_time, self.config.retry_delay))
                            continue
                        
                        self.logger.warning(
                            f"Rate limit exceeded. "
                            f"Required tokens: {tokens}, "
                            f"Available: {self.tokens:.2f}"
                        )
                        return False
                    
                    self.tokens -= tokens
                    return True
                    
            except Exception as e:
                self.logger.error(f"Error acquiring tokens: {e}")
                if attempt == self.config.max_retries - 1:
                    return False

    async def _add_new_tokens(self) -> None:
        """Add new tokens based on elapsed time with burst handling"""
        now = time.monotonic()
        time_passed = now - self.last_update
        
        # Calculate token replenishment with burst consideration
        new_tokens = time_passed * self.config.calls_per_second
        max_tokens = self.config.burst_size
        
        # Allow burst recovery but prevent token hoarding
        if self.tokens < max_tokens / 2:
            new_tokens *= 1.5  # Faster recovery when low on tokens
        
        self.tokens = min(max_tokens, self.tokens + new_tokens)
        self.last_update = now

    def _time_to_tokens(self, tokens: int) -> float:
        """Calculate time needed to acquire specified tokens"""
        needed = tokens - self.tokens
        if needed <= 0:
            return 0
        return needed / self.config.calls_per_second

    async def __aenter__(self):
        """Async context manager entry"""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        pass

    def get_stats(self) -> Dict:
        """Get current rate limiting statistics"""
        now = time.monotonic()
        return {
            'total_requests': self.stats.total_requests,
            'throttled_requests': self.stats.throttled_requests,
            'throttle_rate': (
                self.stats.throttled_requests / self.stats.total_requests 
                if self.stats.total_requests > 0 else 0
            ),
            'uptime': now - self.stats.last_reset,
            'current_tokens': self.tokens,
            'burst_size': self.config.burst_size
        }