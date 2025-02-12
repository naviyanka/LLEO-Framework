from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
import asyncio
import json
import aiohttp
from datetime import datetime
from pathlib import Path
import logging
from ..utils.secure_config import ConfigManager

@dataclass
class WorkerInfo:
	"""Information about worker node"""
	id: str
	address: str
	status: str = 'idle'
	capabilities: Set[str] = field(default_factory=set)
	last_heartbeat: datetime = field(default_factory=datetime.now)
	current_task: Optional[str] = None
	metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskInfo:
	"""Information about distributed task"""
	id: str
	module: str
	tool: str
	params: Dict[str, Any]
	status: str = 'pending'
	worker_id: Optional[str] = None
	start_time: Optional[datetime] = None
	end_time: Optional[datetime] = None
	result: Optional[Dict[str, Any]] = None
	error: Optional[str] = None

class DistributedExecutor:
	"""Manages distributed task execution"""
	def __init__(self, config: ConfigManager):
		self.config = config
		self.logger = logging.getLogger('DistributedExecutor')
		self.workers: Dict[str, WorkerInfo] = {}
		self.tasks: Dict[str, TaskInfo] = {}
		self._task_queue = asyncio.Queue()
		self._worker_lock = asyncio.Lock()
		self._setup_monitoring()

	async def start(self):
		"""Start distributed executor"""
		await self._start_worker_monitor()
		await self._start_task_scheduler()

	async def stop(self):
		"""Stop distributed executor"""
		# Cleanup tasks and notify workers
		pass

	async def submit_task(self, module: str, tool: str, params: Dict[str, Any]) -> str:
		"""Submit task for distributed execution"""
		task_id = f"{module}_{tool}_{datetime.now().timestamp()}"
		task = TaskInfo(
			id=task_id,
			module=module,
			tool=tool,
			params=params
		)
		self.tasks[task_id] = task
		await self._task_queue.put(task)
		return task_id

	async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
		"""Get task result"""
		if task_id in self.tasks:
			task = self.tasks[task_id]
			if task.status == 'completed':
				return task.result
			elif task.status == 'failed':
				raise Exception(f"Task failed: {task.error}")
		return None

	async def register_worker(self, worker_id: str, address: str, capabilities: Set[str]):
		"""Register new worker"""
		async with self._worker_lock:
			self.workers[worker_id] = WorkerInfo(
				id=worker_id,
				address=address,
				capabilities=capabilities
			)

	async def _start_worker_monitor(self):
		"""Monitor worker health"""
		while True:
			try:
				await self._check_workers()
				await asyncio.sleep(30)  # Check every 30 seconds
			except Exception as e:
				self.logger.error(f"Error monitoring workers: {e}")

	async def _check_workers(self):
		"""Check worker health status"""
		async with self._worker_lock:
			current_time = datetime.now()
			dead_workers = []
			
			for worker_id, worker in self.workers.items():
				if (current_time - worker.last_heartbeat).total_seconds() > 60:
					dead_workers.append(worker_id)
					if worker.current_task:
						await self._reschedule_task(worker.current_task)

			for worker_id in dead_workers:
				del self.workers[worker_id]

	async def _start_task_scheduler(self):
		"""Schedule tasks to workers"""
		while True:
			try:
				task = await self._task_queue.get()
				await self._schedule_task(task)
			except Exception as e:
				self.logger.error(f"Error scheduling task: {e}")

	async def _schedule_task(self, task: TaskInfo):
		"""Schedule task to appropriate worker"""
		async with self._worker_lock:
			available_workers = [
				w for w in self.workers.values()
				if w.status == 'idle' and task.tool in w.capabilities
			]
			
			if not available_workers:
				await self._task_queue.put(task)
				return

			worker = available_workers[0]
			worker.status = 'busy'
			worker.current_task = task.id
			task.worker_id = worker.id
			task.status = 'running'
			task.start_time = datetime.now()

			try:
				await self._execute_on_worker(worker, task)
			except Exception as e:
				task.status = 'failed'
				task.error = str(e)
				worker.status = 'idle'
				worker.current_task = None

	async def _execute_on_worker(self, worker: WorkerInfo, task: TaskInfo):
		"""Execute task on worker"""
		async with aiohttp.ClientSession() as session:
			try:
				async with session.post(
					f"http://{worker.address}/execute",
					json={
						'task_id': task.id,
						'module': task.module,
						'tool': task.tool,
						'params': task.params
					}
				) as response:
					result = await response.json()
					task.status = 'completed'
					task.result = result
					task.end_time = datetime.now()
			except Exception as e:
				raise Exception(f"Worker execution failed: {e}")
			finally:
				worker.status = 'idle'
				worker.current_task = None

	async def _reschedule_task(self, task_id: str):
		"""Reschedule failed task"""
		if task_id in self.tasks:
			task = self.tasks[task_id]
			task.status = 'pending'
			task.worker_id = None
			task.start_time = None
			await self._task_queue.put(task)

	def _setup_monitoring(self):
		"""Setup monitoring for distributed execution"""
		# Implementation for monitoring setup
		pass