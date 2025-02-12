from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Set
from pathlib import Path
import asyncio
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from ..utils.secure_config import ConfigManager
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import subprocess
from datetime import datetime
from core.utils.event_bus import EventBus
import re

class ToolExecutionError(Exception):
	"""Base exception for tool execution errors"""
	pass

class ToolNotFoundError(ToolExecutionError):
	"""Exception raised when a required tool is not found"""
	pass

class ToolTimeoutError(ToolExecutionError):
	"""Exception raised when a tool execution times out"""
	pass

class ToolResult:
	def __init__(self, success: bool = False, output: str = "", error: str = "", exit_code: int = 0):
		self.success = success
		self.output = output
		self.error = error
		self.exit_code = exit_code

	def __getitem__(self, key):
		if key == "output":
			return self.output
		elif key == "error":
			return self.error
		elif key == "exit_code":
			return self.exit_code
		elif key == "success":
			return self.success
		raise KeyError(f"Invalid key: {key}")

	def __str__(self):
		return f"ToolResult(success={self.success}, output={self.output}, error={self.error}, exit_code={self.exit_code})"

class BaseModule(ABC):
	def __init__(self, framework):
		self.framework = framework
		self.config = framework.config
		self.logger = logging.getLogger(self.__class__.__name__)
		self.output_dir = framework.output_dir / self.__class__.__name__.lower()
		self.output_dir.mkdir(parents=True, exist_ok=True)
		self.running_tasks: Set[asyncio.Task] = set()
		self.max_concurrent_tasks = self.config.tools.threads
		self.event_bus = EventBus()
		self.required_tools = self.get_required_tools()
		self.tool_status = {}

	async def verify_tools(self) -> Dict[str, Dict[str, Any]]:
		"""Verify all required tools and their versions"""
		self.logger.info("\n=== Verifying Required Tools ===")
		tool_status = {}
		missing_tools = []
		outdated_tools = []
		
		for tool, min_version in self.required_tools.items():
			self.logger.info(f"\nChecking {tool}...")
			
			# Check if tool exists
			exists = await self._check_tool_exists(tool)
			if not exists:
				self.logger.error(f"❌ {tool} not found")
				missing_tools.append(tool)
				tool_status[tool] = {
					'installed': False,
					'version': None,
					'min_version': min_version,
					'status': 'missing'
				}
				continue
			
			# Get tool version
			current_version = await self._get_tool_version(tool)
			is_outdated = False
			
			if current_version and min_version:
				try:
					current_parts = [int(x) for x in current_version.split('.')]
					min_parts = [int(x) for x in min_version.split('.')]
					is_outdated = current_parts < min_parts
					if is_outdated:
						self.logger.warning(f"⚠️  {tool} is outdated (Current: {current_version}, Required: {min_version})")
						outdated_tools.append((tool, current_version, min_version))
					else:
						self.logger.info(f"✅ {tool} version {current_version} is up to date")
				except:
					self.logger.warning(f"⚠️  Could not compare versions for {tool}")
			else:
				if current_version:
					self.logger.info(f"✅ {tool} version {current_version} found")
				else:
					self.logger.warning(f"⚠️  Could not determine {tool} version")
			
			tool_status[tool] = {
				'installed': True,
				'version': current_version,
				'min_version': min_version,
				'status': 'outdated' if is_outdated else 'ok'
			}
		
		self.tool_status = tool_status
		
		if missing_tools or outdated_tools:
			self.logger.warning("\n=== Tool Status Summary ===")
			if missing_tools:
				self.logger.warning("\nMissing Tools:")
				for tool in missing_tools:
					self.logger.warning(f"❌ {tool} (Required)")
			
			if outdated_tools:
				self.logger.warning("\nOutdated Tools:")
				for tool, current, required in outdated_tools:
					self.logger.warning(f"⚠️  {tool} (Current: {current}, Required: {required})")
			
			self.logger.warning("\nRecommendation:")
			if missing_tools:
				self.logger.warning("- Install missing tools before continuing")
			if outdated_tools:
				self.logger.warning("- Update outdated tools to ensure best results")
			
			return tool_status
		else:
			self.logger.info("\n✅ All tools are installed and up to date!")
		
		return tool_status

	async def check_dependencies(self) -> bool:
		"""Check if all module dependencies are satisfied"""
		dependencies = self.get_dependencies()
		if not dependencies:
			return True
			
		for dep in dependencies:
			results = await self.framework.session_manager.get_results(dep.lower())
			if not results:
				self.logger.error(f"Required dependency '{dep}' has no results")
				return False
		return True

	async def setup(self) -> None:
		"""Setup module resources with enhanced tool verification"""
		try:
			self.logger.info(f"\n=== Setting up {self.__class__.__name__} ===")
			
			# Create necessary directories
			for dir_name in ['raw', 'processed', 'temp']:
				dir_path = self.output_dir / dir_name
				dir_path.mkdir(parents=True, exist_ok=True)

			# Verify tools and their versions
			tool_status = await self.verify_tools()
			
			# Check if there are any issues
			issues = any(status['status'] != 'ok' for status in tool_status.values())
			if issues:
				self.logger.warning("\nTool verification found issues.")
				response = input("\nDo you want to continue with the current tool status? (y/n): ").lower()
				if response != 'y':
					raise ToolExecutionError("Tool verification failed. Please install/update the required tools.")
				self.logger.info("\nContinuing with available tools...")
			
			# Check dependencies
			if not await self.check_dependencies():
				raise ToolExecutionError("Module dependencies not satisfied")
				
		except Exception as e:
			self.logger.error(f"Error during setup: {e}")
			raise

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
				import shutil
				shutil.rmtree(temp_dir)
				
		except Exception as e:
			self.logger.error(f"Error during cleanup: {e}")

	@abstractmethod
	async def run(self) -> Dict[str, Any]:
		"""Run the module"""
		pass

	@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
	async def execute_tool(self, cmd: List[str], timeout: Optional[int] = None) -> ToolResult:
		"""Execute a tool with retry logic and proper error handling"""
		start_time = datetime.now()
		try:
			if not await self._check_tool_exists(cmd[0]):
				return ToolResult(
					success=False,
					error=f"Tool {cmd[0]} not found",
					exit_code=-1
				)

			process = await asyncio.create_subprocess_exec(
				*cmd,
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.PIPE
			)

			try:
				stdout, stderr = await asyncio.wait_for(
					process.communicate(),
					timeout=timeout or self.config.tools.timeout
				)
			except asyncio.TimeoutError:
				process.kill()
				return ToolResult(
					success=False,
					error=f"Tool {cmd[0]} execution timed out",
					exit_code=-1
				)

			return ToolResult(
				success=process.returncode == 0,
				output=stdout.decode() if stdout else None,
				error=stderr.decode() if stderr else None,
				exit_code=process.returncode
			)

		except Exception as e:
			self.logger.error(f"Error executing {cmd[0]}: {e}")
			return ToolResult(
				success=False,
				error=str(e),
				exit_code=-1
			)

	async def _check_tool_exists(self, tool_name: str) -> bool:
		"""Check if a tool is installed"""
		try:
			process = await asyncio.create_subprocess_exec(
				'which',
				tool_name,
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.PIPE
			)
			stdout, stderr = await process.communicate()
			return process.returncode == 0 and bool(stdout)
		except Exception as e:
			self.logger.error(f"Error checking tool {tool_name}: {e}")
			return False

	def save_results(self, results: Dict[str, Any], filename: str) -> None:
		"""Save module results to file with proper error handling"""
		try:
			output_file = self.output_dir / filename
			output_file.write_text(str(results))
			self.logger.info(f"Results saved to {output_file}")
		except Exception as e:
			self.logger.error(f"Error saving results: {e}")

	async def run_parallel(self, func, items: List[Any], max_workers: Optional[int] = None) -> List[Any]:
		"""Run tasks in parallel with proper resource management"""
		max_workers = max_workers or self.config.tools.threads
		loop = asyncio.get_event_loop()
		
		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			tasks = [
				loop.run_in_executor(executor, func, item)
				for item in items
			]
			results = []
			for task in asyncio.as_completed(tasks):
				try:
					result = await task
					if result:
						results.append(result)
				except Exception as e:
					self.logger.error(f"Error in parallel execution: {e}")
			
			return results

	def get_required_tools(self) -> Dict[str, str]:
		"""Return required tools and their minimum versions"""
		return {}

	def get_dependencies(self) -> List[Type]:
		"""Get module dependencies"""
		return []

	def get_event_handlers(self) -> Dict[str, callable]:
		"""Get event handlers"""
		return {}

	async def _get_tool_version(self, tool: str) -> Optional[str]:
		"""Get tool version using appropriate command"""
		version_commands = {
			'subfinder': ['subfinder', '-version'],
			'amass': ['amass', 'version'],
			'findomain': ['findomain', '--version'],
			'naabu': ['naabu', '-version'],
			'httpx': ['httpx', '-version'],
			'dnsx': ['dnsx', '-version'],
			'nuclei': ['nuclei', '-version'],
			'katana': ['katana', '-version'],
			'ffuf': ['ffuf', '-V'],
			'gobuster': ['gobuster', 'version'],
			'wpscan': ['wpscan', '--version'],
			'nikto': ['nikto', '-Version'],
			'sqlmap': ['sqlmap', '--version'],
			'dalfox': ['dalfox', 'version'],
			'ghauri': ['ghauri', '--version'],
			'kxss': ['kxss', '--version'],
			'crlfuzz': ['crlfuzz', '--version']
		}
		
		try:
			if tool not in version_commands:
				self.logger.warning(f"No version command defined for {tool}")
				return None
				
			cmd = version_commands[tool]
			result = await self.execute_tool(cmd, timeout=10)
			
			if result and (result.output or result.error):
				# Combine output and error for version extraction
				output = ''
				if result.output:
					output += result.output
				if result.error:
					output += result.error
				
				# Try to extract version using common patterns
				patterns = [
					r'(?i)version\s*[:]?\s*v?(\d+\.\d+\.\d+)',  # version: 1.2.3
					r'(?i)v?(\d+\.\d+\.\d+)',  # v1.2.3 or 1.2.3
					r'(?i)(\d+\.\d+\.\d+(?:-\w+)?)',  # 1.2.3 or 1.2.3-dev
					r'(?i)(\d+\.\d+)',  # 1.2
				]
				
				for pattern in patterns:
					match = re.search(pattern, output)
					if match:
						version = match.group(1)
						self.logger.info(f"Found {tool} version {version}")
						return version
				
				# If no pattern matches but we have output, log it for debugging
				if output:
					self.logger.debug(f"Could not extract version from output: {output[:200]}...")
				return None
			
			return None
			
		except Exception as e:
			self.logger.error(f"Error getting {tool} version: {e}")
			return None

	async def _check_tool_version(self, tool_name: str) -> str:
		try:
			result = await self._run_tool(tool_name, ["-version"])
			if not result.success:
				result = await self._run_tool(tool_name, ["--version"])
			
			if result.success and result.output:
				version_patterns = [
					r'(?i)Current Version:?\s*v?(\d+\.\d+\.\d+)',
					r'(?i)Version:?\s*v?(\d+\.\d+\.\d+)',
					r'(?i)v?(\d+\.\d+\.\d+)',
					r'(?i)version\s+v?(\d+\.\d+\.\d+)',
				]
				
				for pattern in version_patterns:
					match = re.search(pattern, result.output)
					if match:
						return match.group(1)
				
				# If no version pattern matched but command succeeded, return the output
				return result.output
				
			self.logger.warning(f"Could not determine {tool_name} version")
			return None
		except Exception as e:
			self.logger.error(f"Error checking {tool_name} version: {str(e)}")
			return None