from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
import subprocess
import asyncio
import logging
from pathlib import Path
import json
import aiohttp
import semver
from datetime import datetime, timedelta
from ..utils.secure_config import ConfigManager

@dataclass
class CacheEntry:
	data: Any
	timestamp: datetime
	ttl: timedelta
	metadata: Dict[str, Any] = field(default_factory=dict)

class ResultCache:
	"""Cache for tool results"""
	def __init__(self, max_size: int = 1000):
		self.cache: Dict[str, CacheEntry] = {}
		self.max_size = max_size
		self._lock = asyncio.Lock()

	async def get(self, key: str) -> Optional[Any]:
		"""Get cached result"""
		async with self._lock:
			if key in self.cache:
				entry = self.cache[key]
				if datetime.now() - entry.timestamp < entry.ttl:
					return entry.data
				del self.cache[key]
		return None

	async def set(self, key: str, value: Any, ttl: timedelta, metadata: Dict[str, Any] = None):
		"""Set cached result"""
		async with self._lock:
			if len(self.cache) >= self.max_size:
				self._evict_oldest()
			self.cache[key] = CacheEntry(
				data=value,
				timestamp=datetime.now(),
				ttl=ttl,
				metadata=metadata or {}
			)

	def _evict_oldest(self):
		"""Evict oldest cache entries"""
		if not self.cache:
			return
		oldest_key = min(
			self.cache.keys(),
			key=lambda k: self.cache[k].timestamp
		)
		del self.cache[oldest_key]

@dataclass
class ToolInfo:
	name: str
	version: str
	path: Path
	installer: str  # pip, go, apt, etc.
	repository: Optional[str] = None
	dependencies: List[str] = None

class ToolManager:
	def __init__(self, config: ConfigManager):
		self.config = config
		self.logger = logging.getLogger('ToolManager')
		self.tools_info = self._load_tools_info()
		self.installation_lock = asyncio.Lock()
		self.result_cache = ResultCache()
		self.version_cache: Dict[str, str] = {}
		self._setup_monitoring()

	async def execute_tool(self, tool_name: str, cmd: List[str], cache_ttl: Optional[timedelta] = None) -> Dict[str, Any]:
		"""Execute tool with caching"""
		cache_key = f"{tool_name}:{':'.join(cmd)}"
		
		if cache_ttl:
			cached = await self.result_cache.get(cache_key)
			if cached:
				self.logger.debug(f"Cache hit for {tool_name}")
				return cached

		try:
			result = await self._execute_with_monitoring(tool_name, cmd)
			
			if cache_ttl and result.get('success'):
				await self.result_cache.set(
					cache_key,
					result,
					cache_ttl,
					{'tool': tool_name, 'command': cmd}
				)
			
			return result

		except Exception as e:
			self.logger.error(f"Error executing {tool_name}: {e}")
			return {'error': str(e), 'success': False}

	async def _execute_with_monitoring(self, tool_name: str, cmd: List[str]) -> Dict[str, Any]:
		"""Execute tool with resource monitoring"""
		start_time = datetime.now()
		try:
			process = await asyncio.create_subprocess_exec(
				*cmd,
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.PIPE
			)
			
			stdout, stderr = await process.communicate()
			
			execution_time = (datetime.now() - start_time).total_seconds()
			
			return {
				'success': process.returncode == 0,
				'output': stdout.decode(),
				'error': stderr.decode() if process.returncode != 0 else None,
				'execution_time': execution_time,
				'return_code': process.returncode
			}

		except Exception as e:
			return {
				'success': False,
				'error': str(e),
				'execution_time': (datetime.now() - start_time).total_seconds()
			}

	def _load_tools_info(self) -> Dict[str, ToolInfo]:
		"""Load tool information from configuration"""
		tools_file = Path(__file__).parent / 'tools.json'
		try:
			with open(tools_file) as f:
				data = json.load(f)
				return {
					name: ToolInfo(**info)
					for name, info in data.items()
				}
		except Exception as e:
			self.logger.error(f"Error loading tools info: {e}")
			return {}

	async def verify_tool_version(self, name: str, required_version: str) -> bool:
		"""Verify tool version with caching"""
		if name in self.version_cache:
			current = self.version_cache[name]
			return self._version_satisfies(current, required_version)

		try:
			process = await asyncio.create_subprocess_exec(
				name, '--version',
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.PIPE
			)
			stdout, _ = await process.communicate()
			version = stdout.decode().strip()
			
			self.version_cache[name] = version
			return self._version_satisfies(version, required_version)

		except Exception as e:
			self.logger.error(f"Error checking {name} version: {e}")
			return False

	def _version_satisfies(self, current: str, required: str) -> bool:
		"""Check version compatibility"""
		try:
			return semver.VersionInfo.parse(current) >= semver.VersionInfo.parse(required)
		except ValueError:
			self.logger.warning(f"Invalid version format: {current} or {required}")
			return False

	async def update_tool(self, name: str) -> bool:
		"""Update tool to latest version"""
		if name not in self.tools_info:
			return False

		tool_info = self.tools_info[name]
		try:
			if tool_info.installer == 'go':
				cmd = ['go', 'install', f"{tool_info.repository}@latest"]
			elif tool_info.installer == 'pip':
				cmd = ['pip', 'install', '--upgrade', name]
			else:
				return False

			result = await self._execute_with_monitoring(name, cmd)
			if result['success']:
				self.version_cache.pop(name, None)  # Clear version cache
				return True
			return False

		except Exception as e:
			self.logger.error(f"Error updating {name}: {e}")
			return False

	def _setup_monitoring(self):
		"""Setup tool execution monitoring"""
		# Implementation for monitoring setup
		pass

	async def install_tool(self, name: str) -> bool:
		"""Install or update a tool"""
		if name not in self.tools_info:
			self.logger.error(f"Unknown tool: {name}")
			return False

		async with self.installation_lock:
			tool_info = self.tools_info[name]
			try:
				if tool_info.installer == 'go':
					return await self._install_go_tool(tool_info)
				elif tool_info.installer == 'pip':
					return await self._install_pip_tool(tool_info)
				elif tool_info.installer == 'apt':
					return await self._install_apt_tool(tool_info)
				else:
					self.logger.error(f"Unsupported installer: {tool_info.installer}")
					return False

			except Exception as e:
				self.logger.error(f"Error installing {name}: {e}")
				return False

	async def _install_go_tool(self, tool_info: ToolInfo) -> bool:
		"""Install Go tool"""
		try:
			process = await asyncio.create_subprocess_exec(
				'go', 'install', f"{tool_info.repository}@latest",
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.PIPE
			)
			_, stderr = await process.communicate()
			
			if process.returncode != 0:
				self.logger.error(f"Go install failed: {stderr.decode()}")
				return False
				
			return True

		except Exception as e:
			self.logger.error(f"Error installing Go tool {tool_info.name}: {e}")
			return False

	async def _install_pip_tool(self, tool_info: ToolInfo) -> bool:
		"""Install Python package"""
		try:
			process = await asyncio.create_subprocess_exec(
				'pip', 'install', '--upgrade', tool_info.name,
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.PIPE
			)
			_, stderr = await process.communicate()
			
			if process.returncode != 0:
				self.logger.error(f"Pip install failed: {stderr.decode()}")
				return False
				
			return True

		except Exception as e:
			self.logger.error(f"Error installing Python package {tool_info.name}: {e}")
			return False

	async def _install_apt_tool(self, tool_info: ToolInfo) -> bool:
		"""Install system package"""
		try:
			process = await asyncio.create_subprocess_exec(
				'sudo', 'apt-get', 'install', '-y', tool_info.name,
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.PIPE
			)
			_, stderr = await process.communicate()
			
			if process.returncode != 0:
				self.logger.error(f"Apt install failed: {stderr.decode()}")
				return False
				
			return True

		except Exception as e:
			self.logger.error(f"Error installing system package {tool_info.name}: {e}")
			return False

	def _version_satisfies(self, current: str, required: str) -> bool:
		"""Check if current version satisfies required version"""
		try:
			return semver.VersionInfo.parse(current) >= semver.VersionInfo.parse(required)
		except ValueError:
			self.logger.warning(f"Invalid version format: {current} or {required}")
			return False

	async def check_dependencies(self, name: str) -> bool:
		"""Check and install tool dependencies"""
		if name not in self.tools_info:
			return False

		tool_info = self.tools_info[name]
		if not tool_info.dependencies:
			return True

		for dep in tool_info.dependencies:
			if not await self.verify_tool(dep):
				self.logger.info(f"Installing dependency: {dep}")
				if not await self.install_tool(dep):
					return False

		return True