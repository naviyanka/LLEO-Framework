from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import psutil
import asyncio
import logging
from pathlib import Path
import json
import aiofiles
from dataclasses import asdict
import time

@dataclass
class ToolMetrics:
	name: str
	start_time: datetime
	end_time: Optional[datetime] = None
	execution_time: float = 0.0
	memory_usage: float = 0.0
	cpu_usage: float = 0.0
	success_count: int = 0
	error_count: int = 0
	retries: int = 0

@dataclass
class SystemMetrics:
	timestamp: datetime = field(default_factory=datetime.now)
	cpu_percent: float = 0.0
	memory_percent: float = 0.0
	disk_percent: float = 0.0
	network_io: Dict[str, int] = field(default_factory=dict)

@dataclass
class ResourceMetrics:
	cpu_percent: float = 0.0
	memory_percent: float = 0.0
	disk_usage_percent: float = 0.0
	open_files: int = 0
	network_io_counters: Dict[str, int] = None
	timestamp: str = None

@dataclass
class ModuleMetrics:
	start_time: str
	end_time: Optional[str] = None
	duration: float = 0.0
	peak_cpu_percent: float = 0.0
	peak_memory_percent: float = 0.0
	avg_cpu_percent: float = 0.0
	avg_memory_percent: float = 0.0
	total_network_bytes: int = 0
	error_count: int = 0

class PerformanceMonitor:
	def __init__(self, output_dir: Path, interval: float = 1.0):
		self.logger = logging.getLogger('PerformanceMonitor')
		self.output_dir = output_dir / 'metrics'
		self.output_dir.mkdir(parents=True, exist_ok=True)
		self.tool_metrics: Dict[str, ToolMetrics] = {}
		self.system_metrics: List[SystemMetrics] = []
		self.monitoring = False
		self._monitor_task = None
		self.interval = interval
		self.monitoring_tasks = {}
		self.metrics = {}
		self.running = False
		self._monitoring_lock = asyncio.Lock()
		
		# Initialize process info
		self.process = psutil.Process()
		self.start_time = datetime.now()
		
		# Resource thresholds
		self.cpu_threshold = 90.0  # 90% CPU usage
		self.memory_threshold = 85.0  # 85% memory usage
		self.disk_threshold = 90.0  # 90% disk usage

	async def start_monitoring(self):
		"""Start system monitoring"""
		self.monitoring = True
		self._monitor_task = asyncio.create_task(self._monitor_system())
		self.logger.info("System monitoring started")

	async def stop_monitoring(self):
		"""Stop system monitoring"""
		self.monitoring = False
		if self._monitor_task:
			self._monitor_task.cancel()
			try:
				await self._monitor_task
			except asyncio.CancelledError:
				pass
		await self._save_metrics()
		self.logger.info("System monitoring stopped")

	async def _monitor_system(self):
		"""Monitor system metrics"""
		while self.monitoring:
			try:
				metrics = SystemMetrics(
					cpu_percent=psutil.cpu_percent(interval=1),
					memory_percent=psutil.virtual_memory().percent,
					disk_percent=psutil.disk_usage('/').percent,
					network_io={
						'bytes_sent': psutil.net_io_counters().bytes_sent,
						'bytes_recv': psutil.net_io_counters().bytes_recv
					}
				)
				self.system_metrics.append(metrics)
				
				# Check resource thresholds
				if metrics.cpu_percent > 90:
					self.logger.warning(f"High CPU usage: {metrics.cpu_percent}%")
				if metrics.memory_percent > 90:
					self.logger.warning(f"High memory usage: {metrics.memory_percent}%")
				if metrics.disk_percent > 90:
					self.logger.warning(f"High disk usage: {metrics.disk_percent}%")
				
				await asyncio.sleep(5)  # Monitor every 5 seconds
				
			except Exception as e:
				self.logger.error(f"Error monitoring system: {e}")
				await asyncio.sleep(5)

	def start_tool_monitoring(self, tool_name: str):
		"""Start monitoring a specific tool"""
		self.tool_metrics[tool_name] = ToolMetrics(
			name=tool_name,
			start_time=datetime.now()
		)

	def stop_tool_monitoring(self, tool_name: str, success: bool = True):
		"""Stop monitoring a specific tool"""
		if tool_name in self.tool_metrics:
			metrics = self.tool_metrics[tool_name]
			metrics.end_time = datetime.now()
			metrics.execution_time = (metrics.end_time - metrics.start_time).total_seconds()
			if success:
				metrics.success_count += 1
			else:
				metrics.error_count += 1

	def record_tool_retry(self, tool_name: str):
		"""Record a tool retry attempt"""
		if tool_name in self.tool_metrics:
			self.tool_metrics[tool_name].retries += 1

	async def _save_metrics(self):
		"""Save metrics to file"""
		try:
			metrics_file = self.output_dir / f'metrics_{datetime.now():%Y%m%d_%H%M%S}.json'
			metrics = {
				'system_metrics': [
					{
						'timestamp': m.timestamp.isoformat(),
						'cpu_percent': m.cpu_percent,
						'memory_percent': m.memory_percent,
						'disk_percent': m.disk_percent,
						'network_io': m.network_io
					}
					for m in self.system_metrics
				],
				'tool_metrics': {
					name: {
						'start_time': m.start_time.isoformat(),
						'end_time': m.end_time.isoformat() if m.end_time else None,
						'execution_time': m.execution_time,
						'memory_usage': m.memory_usage,
						'cpu_usage': m.cpu_usage,
						'success_count': m.success_count,
						'error_count': m.error_count,
						'retries': m.retries
					}
					for name, m in self.tool_metrics.items()
				}
			}
			
			async with aiofiles.open(metrics_file, 'w') as f:
				await f.write(json.dumps(metrics, indent=4))
			
		except Exception as e:
			self.logger.error(f"Error saving metrics: {e}")

	async def get_metrics(self) -> Dict:
		"""Get all metrics including system and tool performance"""
		if not self.system_metrics:
			return {
				'duration': '0s',
				'peak_memory_mb': 0,
				'avg_cpu_percent': 0,
				'data_processed_mb': 0
			}
		
		first_metric = self.system_metrics[0]
		last_metric = self.system_metrics[-1]
		duration = (last_metric.timestamp - first_metric.timestamp).total_seconds()
		
		peak_memory = max(m.memory_percent for m in self.system_metrics)
		avg_cpu = sum(m.cpu_percent for m in self.system_metrics) / len(self.system_metrics)
		
		# Calculate data processed from network IO
		initial_bytes = first_metric.network_io.get('bytes_recv', 0)
		final_bytes = last_metric.network_io.get('bytes_recv', 0)
		data_processed = (final_bytes - initial_bytes) / (1024 * 1024)  # Convert to MB
		
		return {
			'duration': f"{duration:.1f}s",
			'peak_memory_mb': f"{peak_memory:.1f}",
			'avg_cpu_percent': f"{avg_cpu:.1f}",
			'data_processed_mb': f"{data_processed:.1f}"
		}

	def get_tool_performance(self, tool_name: str) -> Optional[Dict]:
		"""Get performance metrics for a specific tool"""
		if tool_name in self.tool_metrics:
			m = self.tool_metrics[tool_name]
			return {
				'execution_time': m.execution_time,
				'success_rate': (
					m.success_count / (m.success_count + m.error_count)
					if (m.success_count + m.error_count) > 0 else 0
				),
				'retries': m.retries,
				'memory_usage': m.memory_usage,
				'cpu_usage': m.cpu_usage
			}
		return None

	def get_system_health(self) -> Dict:
		"""Get current system health metrics"""
		if self.system_metrics:
			latest = self.system_metrics[-1]
			return {
				'status': 'healthy' if self._is_healthy(latest) else 'warning',
				'metrics': {
					'cpu_percent': latest.cpu_percent,
					'memory_percent': latest.memory_percent,
					'disk_percent': latest.disk_percent,
					'network_io': latest.network_io
				}
			}
		return {'status': 'unknown', 'metrics': {}}

	def _is_healthy(self, metrics: SystemMetrics) -> bool:
		"""Check if system metrics are within healthy ranges"""
		return (
			metrics.cpu_percent < 90 and
			metrics.memory_percent < 90 and
			metrics.disk_percent < 90
		)

	async def start_monitoring_module(self, module_name: str) -> None:
		"""Start monitoring a module's performance"""
		async with self._monitoring_lock:
			if module_name in self.monitoring_tasks:
				return
			
			self.metrics[module_name] = ModuleMetrics(
				start_time=datetime.now().isoformat()
			)
			
			# Create monitoring task
			task = asyncio.create_task(self._monitor_module(module_name))
			self.monitoring_tasks[module_name] = task
			self.logger.debug(f"Started monitoring {module_name}")

	async def stop_monitoring_module(self, module_name: str) -> None:
		"""Stop monitoring a module's performance"""
		async with self._monitoring_lock:
			if module_name not in self.monitoring_tasks:
				return
			
			# Cancel monitoring task
			task = self.monitoring_tasks.pop(module_name)
			task.cancel()
			try:
				await task
			except asyncio.CancelledError:
				pass
			
			# Update final metrics
			if module_name in self.metrics:
				metrics = self.metrics[module_name]
				metrics.end_time = datetime.now().isoformat()
				if metrics.start_time:
					start = datetime.fromisoformat(metrics.start_time)
					end = datetime.fromisoformat(metrics.end_time)
					metrics.duration = (end - start).total_seconds()
			
			self.logger.debug(f"Stopped monitoring {module_name}")

	async def _monitor_module(self, module_name: str) -> None:
		"""Monitor module performance metrics"""
		cpu_samples = []
		memory_samples = []
		start_net_io = psutil.net_io_counters()
		
		try:
			while True:
				metrics = await self._get_resource_metrics()
				
				# Update module metrics
				module_metrics = self.metrics[module_name]
				
				# Update peak values
				module_metrics.peak_cpu_percent = max(
					module_metrics.peak_cpu_percent,
					metrics.cpu_percent
				)
				module_metrics.peak_memory_percent = max(
					module_metrics.peak_memory_percent,
					metrics.memory_percent
				)
				
				# Collect samples for averages
				cpu_samples.append(metrics.cpu_percent)
				memory_samples.append(metrics.memory_percent)
				
				# Calculate averages
				module_metrics.avg_cpu_percent = sum(cpu_samples) / len(cpu_samples)
				module_metrics.avg_memory_percent = sum(memory_samples) / len(memory_samples)
				
				# Check resource thresholds
				await self._check_resource_thresholds(metrics, module_name)
				
				await asyncio.sleep(self.interval)
				
		except asyncio.CancelledError:
			# Calculate final network I/O
			end_net_io = psutil.net_io_counters()
			total_bytes = (
				(end_net_io.bytes_sent - start_net_io.bytes_sent) +
				(end_net_io.bytes_recv - start_net_io.bytes_recv)
			)
			if module_name in self.metrics:
				self.metrics[module_name].total_network_bytes = total_bytes
		
		except Exception as e:
			self.logger.error(f"Error monitoring {module_name}: {e}")
			if module_name in self.metrics:
				self.metrics[module_name].error_count += 1

	async def _get_resource_metrics(self) -> ResourceMetrics:
		"""Get current resource metrics"""
		try:
			cpu_percent = psutil.cpu_percent(interval=0.1)
			memory = psutil.virtual_memory()
			disk = psutil.disk_usage('/')
			open_files = len(self.process.open_files())
			net_io = psutil.net_io_counters()._asdict()
			
			return ResourceMetrics(
				cpu_percent=cpu_percent,
				memory_percent=memory.percent,
				disk_usage_percent=disk.percent,
				open_files=open_files,
				network_io_counters=net_io,
				timestamp=datetime.now().isoformat()
			)
			
		except Exception as e:
			self.logger.error(f"Error getting resource metrics: {e}")
			return ResourceMetrics(timestamp=datetime.now().isoformat())

	async def _check_resource_thresholds(self, metrics: ResourceMetrics, module_name: str) -> None:
		"""Check if resource usage exceeds thresholds"""
		warnings = []
		
		if metrics.cpu_percent > self.cpu_threshold:
			warnings.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
		
		if metrics.memory_percent > self.memory_threshold:
			warnings.append(f"High memory usage: {metrics.memory_percent:.1f}%")
		
		if metrics.disk_usage_percent > self.disk_threshold:
			warnings.append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")
		
		if warnings:
			warning_msg = f"Resource warning for {module_name}: " + ", ".join(warnings)
			self.logger.warning(warning_msg)

	def get_module_metrics(self, module_name: str) -> Optional[Dict[str, Any]]:
		"""Get metrics for a specific module"""
		if module_name in self.metrics:
			return asdict(self.metrics[module_name])
		return None

	def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
		"""Get metrics for all modules"""
		return {name: asdict(metrics) for name, metrics in self.metrics.items()}

	async def save_metrics(self, output_dir: Path) -> None:
		"""Save metrics to file"""
		try:
			metrics_file = output_dir / 'metrics.json'
			metrics_data = {
				'timestamp': datetime.now().isoformat(),
				'total_duration': (datetime.now() - self.start_time).total_seconds(),
				'modules': self.get_all_metrics()
			}
			
			metrics_file.write_text(json.dumps(metrics_data, indent=2))
			self.logger.info(f"Saved performance metrics to {metrics_file}")
			
		except Exception as e:
			self.logger.error(f"Error saving metrics: {e}")

	def print_module_summary(self, module_name: str) -> None:
		"""Print performance summary for a module"""
		metrics = self.get_module_metrics(module_name)
		if not metrics:
			return
		
		self.logger.info(f"\nPerformance Summary for {module_name}:")
		self.logger.info(f"Duration: {metrics['duration']:.2f}s")
		self.logger.info(f"Peak CPU: {metrics['peak_cpu_percent']:.1f}%")
		self.logger.info(f"Peak Memory: {metrics['peak_memory_percent']:.1f}%")
		self.logger.info(f"Avg CPU: {metrics['avg_cpu_percent']:.1f}%")
		self.logger.info(f"Avg Memory: {metrics['avg_memory_percent']:.1f}%")
		self.logger.info(f"Network I/O: {metrics['total_network_bytes'] / 1024 / 1024:.2f} MB")
		if metrics['error_count'] > 0:
			self.logger.info(f"Errors: {metrics['error_count']}")

	def print_overall_summary(self) -> None:
		"""Print overall performance summary"""
		total_duration = (datetime.now() - self.start_time).total_seconds()
		
		self.logger.info("\nOverall Performance Summary:")
		self.logger.info(f"Total Duration: {total_duration:.2f}s")
		self.logger.info(f"Current CPU: {psutil.cpu_percent():.1f}%")
		self.logger.info(f"Current Memory: {psutil.virtual_memory().percent:.1f}%")
		self.logger.info(f"Current Disk: {psutil.disk_usage('/').percent:.1f}%")
		
		# Print module summaries
		for module_name in self.metrics:
			self.print_module_summary(module_name)