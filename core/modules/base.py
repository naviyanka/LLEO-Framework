from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
import os
import json
import shutil
import psutil
import asyncio
from typing import Dict, Any, Optional, List, Type, Set, Union
from pathlib import Path
import subprocess
from datetime import datetime
import logging
from dataclasses import dataclass, field
from ..utils.tools import ToolExecutor
from ..utils.rate_limiter import RateLimiter
from ..utils.tool_checker import check_tool_exists, run_tool

@dataclass
class ModuleEvent:
    """Base class for module events"""
    type: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class EventBus:
    """Event bus for inter-module communication"""
    def __init__(self):
        self.subscribers: Dict[str, Set[callable]] = {}
        
    async def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to all subscribers"""
        event = ModuleEvent(type=event_type, data=data)
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    await callback(event)
                except Exception as e:
                    logging.error(f"Error in event handler: {e}")

    async def subscribe(self, event_type: str, callback: callable) -> None:
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
        self.subscribers[event_type].add(callback)

    async def unsubscribe(self, event_type: str, callback: callable) -> None:
        """Unsubscribe from an event type"""
        if event_type in self.subscribers:
            self.subscribers[event_type].discard(callback)

class ModuleContainer:
    """Dependency injection container"""
    def __init__(self):
        self._services: Dict[type, Any] = {}

    def register(self, service_type: type, instance: Any) -> None:
        """Register a service instance"""
        self._services[service_type] = instance

    def resolve(self, service_type: type) -> Any:
        """Resolve a service instance"""
        if service_type not in self._services:
            raise KeyError(f"Service not registered: {service_type}")
        return self._services[service_type]

@dataclass
class ModuleMetrics:
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    memory_usage: float = 0.0
    disk_usage: float = 0.0

class BaseModule:
    """Base class for all modules"""
    
    def __init__(self, framework):
        self.framework = framework
        self.config = framework.config
        self.event_bus = framework.event_bus
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = framework.output_dir / self.__class__.__name__.lower()
        self.running = False
        self.running_tasks: Set[asyncio.Task] = set()
        self.max_concurrent_tasks = self.config.tools.threads
        self.rate_limiter = None

    async def setup(self) -> None:
        """Setup module resources"""
        self.logger.info(f"Setting up {self.__class__.__name__}...")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create standard subdirectories
        for dir_name in ['raw', 'processed', 'temp']:
            dir_path = self.output_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)

    async def cleanup(self) -> None:
        """Cleanup module resources"""
        try:
            # Cancel any running tasks
            for task in self.running_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self.running_tasks:
                await asyncio.gather(*self.running_tasks, return_exceptions=True)
            
            # Clean up temporary files
            temp_dir = self.output_dir / 'temp'
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                
            self.logger.info(f"Cleaned up {self.__class__.__name__}")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    async def run(self) -> Dict[str, Any]:
        """Run the module"""
        raise NotImplementedError("Subclasses must implement run()")

    def get_dependencies(self) -> List[Type]:
        """Get module dependencies"""
        return []

    def get_event_handlers(self) -> Dict[str, callable]:
        """Get event handlers"""
        return {}

    def get_required_tools(self) -> Dict[str, Optional[str]]:
        """Return required tools and their minimum versions"""
        return {}

    async def execute_tool(self, cmd: List[str], cwd: Optional[Path] = None) -> Any:
        """Execute an external tool"""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else f"Tool exited with code {process.returncode}"
                self.logger.error(f"Tool execution failed: {error_msg}")
                return {'success': False, 'error': error_msg}
                
            return {'success': True, 'output': stdout.decode()}
            
        except Exception as e:
            self.logger.error(f"Error executing tool: {e}")
            return {'success': False, 'error': str(e)}

    async def run_with_retry(self, func, *args, max_retries: int = 3, **kwargs):
        """Run a function with retry logic"""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
