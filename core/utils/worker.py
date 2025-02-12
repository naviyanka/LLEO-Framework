from dataclasses import dataclass
from typing import Dict, Any, Set, Optional
import asyncio
import aiohttp
import json
import logging
import platform
import psutil
from datetime import datetime
from pathlib import Path
from ..utils.secure_config import ConfigManager
from ..utils.tool_manager import ToolManager

@dataclass
class WorkerConfig:
	"""Worker configuration"""
	id: str
	coordinator_url: str
	max_tasks: int = 5
	heartbeat_interval: int = 30
	capabilities: Set[str] = None

class Worker:
	"""Worker node implementation"""
	def __init__(self, config: WorkerConfig, tool_manager: ToolManager):
		self.config = config
		self.tool_manager = tool_manager
		self.logger = logging.getLogger('Worker')
		self.current_tasks: Dict[str, asyncio.Task] = {}
		self._running = False
		self._setup_monitoring()

	async def start(self):
		"""Start worker"""
		self._running = True
		await self._register_with_coordinator()
		await asyncio.gather(
			self._start_heartbeat(),
			self._start_task_listener()
		)

	async def stop(self):
		"""Stop worker"""
		self._running = False
		for task in self.current_tasks.values():
			task.cancel()
		await self._notify_coordinator_shutdown()

	async def _register_with_coordinator(self):
		"""Register with coordinator"""
		try:
			async with aiohttp.ClientSession() as session:
				async with session.post(
					f"{self.config.coordinator_url}/register",
					json={
						'worker_id': self.config.id,
						'address': self._get_address(),
						'capabilities': list(self._get_capabilities()),
						'system_info': self._get_system_info()
					}
				) as response:
					if response.status != 200:
						raise Exception("Registration failed")
		except Exception as e:
			self.logger.error(f"Registration failed: {e}")
			raise

	async def _start_heartbeat(self):
		"""Send periodic heartbeats"""
		while self._running:
			try:
				await self._send_heartbeat()
				await asyncio.sleep(self.config.heartbeat_interval)
			except Exception as e:
				self.logger.error(f"Heartbeat failed: {e}")

	async def _send_heartbeat(self):
		"""Send heartbeat to coordinator"""
		async with aiohttp.ClientSession() as session:
			await session.post(
				f"{self.config.coordinator_url}/heartbeat",
				json={
					'worker_id': self.config.id,
					'timestamp': datetime.now().isoformat(),
					'metrics': self._get_metrics()
				}
			)

	async def _start_task_listener(self):
		"""Listen for incoming tasks"""
		async with aiohttp.ClientSession() as session:
			while self._running:
				try:
					async with session.get(
						f"{self.config.coordinator_url}/tasks/{self.config.id}"
					) as response:
						if response.status == 200:
							task_data = await response.json()
							await self._handle_task(task_data)
				except Exception as e:
					self.logger.error(f"Task listener error: {e}")
				await asyncio.sleep(1)

	async def _handle_task(self, task_data: Dict[str, Any]):
		"""Handle incoming task"""
		task_id = task_data['task_id']
		if len(self.current_tasks) >= self.config.max_tasks:
			await self._reject_task(task_id, "Worker at capacity")
			return

		try:
			task = asyncio.create_task(
				self._execute_task(task_data)
			)
			self.current_tasks[task_id] = task
			await task
		except Exception as e:
			await self._report_task_error(task_id, str(e))
		finally:
			self.current_tasks.pop(task_id, None)

	async def _execute_task(self, task_data: Dict[str, Any]):
		"""Execute task"""
		task_id = task_data['task_id']
		try:
			result = await self.tool_manager.execute_tool(
				task_data['tool'],
				task_data['params']
			)
			await self._report_task_result(task_id, result)
		except Exception as e:
			await self._report_task_error(task_id, str(e))

	async def _report_task_result(self, task_id: str, result: Dict[str, Any]):
		"""Report task result"""
		async with aiohttp.ClientSession() as session:
			await session.post(
				f"{self.config.coordinator_url}/task_result",
				json={
					'task_id': task_id,
					'worker_id': self.config.id,
					'result': result,
					'timestamp': datetime.now().isoformat()
				}
			)

	async def _report_task_error(self, task_id: str, error: str):
		"""Report task error"""
		async with aiohttp.ClientSession() as session:
			await session.post(
				f"{self.config.coordinator_url}/task_error",
				json={
					'task_id': task_id,
					'worker_id': self.config.id,
					'error': error,
					'timestamp': datetime.now().isoformat()
				}
			)

	def _get_capabilities(self) -> Set[str]:
		"""Get worker capabilities"""
		if self.config.capabilities:
			return self.config.capabilities
		return set(self.tool_manager.tools_info.keys())

	def _get_system_info(self) -> Dict[str, Any]:
		"""Get system information"""
		return {
			'platform': platform.platform(),
			'python_version': platform.python_version(),
			'cpu_count': psutil.cpu_count(),
			'memory_total': psutil.virtual_memory().total,
			'disk_total': psutil.disk_usage('/').total
		}

	def _get_metrics(self) -> Dict[str, Any]:
		"""Get current metrics"""
		return {
			'cpu_percent': psutil.cpu_percent(),
			'memory_percent': psutil.virtual_memory().percent,
			'disk_percent': psutil.disk_usage('/').percent,
			'task_count': len(self.current_tasks)
		}

	def _get_address(self) -> str:
		"""Get worker address"""
		# Implementation to get worker's network address
		return "localhost:8000"  # Placeholder

	def _setup_monitoring(self):
		"""Setup worker monitoring"""
		# Implementation for monitoring setup
		pass