import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from .monitor import PerformanceMonitor, ToolMetrics, SystemMetrics

@pytest.fixture
def temp_output_dir(tmp_path):
	return tmp_path / "metrics"

@pytest.fixture
def monitor(temp_output_dir):
	return PerformanceMonitor(temp_output_dir)

@pytest.mark.asyncio
async def test_monitor_initialization(monitor, temp_output_dir):
	"""Test monitor initialization"""
	assert monitor.output_dir == temp_output_dir / "metrics"
	assert monitor.output_dir.exists()
	assert not monitor.monitoring
	assert len(monitor.tool_metrics) == 0
	assert len(monitor.system_metrics) == 0

@pytest.mark.asyncio
async def test_system_monitoring(monitor):
	"""Test system monitoring functionality"""
	with patch('psutil.cpu_percent', return_value=50.0):
		with patch('psutil.virtual_memory') as mock_memory:
			with patch('psutil.disk_usage') as mock_disk:
				with patch('psutil.net_io_counters') as mock_net:
					mock_memory.return_value.percent = 60.0
					mock_disk.return_value.percent = 70.0
					mock_net.return_value.bytes_sent = 1000
					mock_net.return_value.bytes_recv = 2000
					
					await monitor.start_monitoring()
					await asyncio.sleep(0.1)  # Allow monitoring to run
					await monitor.stop_monitoring()
					
					assert len(monitor.system_metrics) > 0
					latest = monitor.system_metrics[-1]
					assert latest.cpu_percent == 50.0
					assert latest.memory_percent == 60.0
					assert latest.disk_percent == 70.0

@pytest.mark.asyncio
async def test_tool_monitoring(monitor):
	"""Test tool-specific monitoring"""
	monitor.start_tool_monitoring("test-tool")
	await asyncio.sleep(0.1)
	monitor.stop_tool_monitoring("test-tool", success=True)
	
	metrics = monitor.get_tool_performance("test-tool")
	assert metrics is not None
	assert metrics['success_rate'] == 1.0
	assert metrics['retries'] == 0
	assert metrics['execution_time'] > 0

@pytest.mark.asyncio
async def test_tool_retry_tracking(monitor):
	"""Test tool retry tracking"""
	monitor.start_tool_monitoring("test-tool")
	monitor.record_tool_retry("test-tool")
	monitor.record_tool_retry("test-tool")
	monitor.stop_tool_monitoring("test-tool", success=False)
	
	metrics = monitor.get_tool_performance("test-tool")
	assert metrics['retries'] == 2
	assert metrics['success_rate'] == 0.0

@pytest.mark.asyncio
async def test_metrics_saving(monitor, temp_output_dir):
	"""Test metrics saving functionality"""
	monitor.start_tool_monitoring("test-tool")
	monitor.stop_tool_monitoring("test-tool")
	
	await monitor._save_metrics()
	
	metrics_files = list(temp_output_dir.glob("metrics_*.json"))
	assert len(metrics_files) > 0
	
	with open(metrics_files[0]) as f:
		data = json.loads(f.read())
		assert 'system_metrics' in data
		assert 'tool_metrics' in data
		assert 'test-tool' in data['tool_metrics']

@pytest.mark.asyncio
async def test_system_health_check(monitor):
	"""Test system health check functionality"""
	with patch('psutil.cpu_percent', return_value=95.0):
		with patch('psutil.virtual_memory') as mock_memory:
			with patch('psutil.disk_usage') as mock_disk:
				mock_memory.return_value.percent = 80.0
				mock_disk.return_value.percent = 85.0
				
				await monitor.start_monitoring()
				await asyncio.sleep(0.1)
				health = monitor.get_system_health()
				await monitor.stop_monitoring()
				
				assert health['status'] == 'warning'
				assert health['metrics']['cpu_percent'] == 95.0

def test_is_healthy(monitor):
	"""Test health status determination"""
	healthy_metrics = SystemMetrics(
		cpu_percent=70.0,
		memory_percent=80.0,
		disk_percent=85.0
	)
	assert monitor._is_healthy(healthy_metrics)
	
	unhealthy_metrics = SystemMetrics(
		cpu_percent=95.0,
		memory_percent=92.0,
		disk_percent=91.0
	)
	assert not monitor._is_healthy(unhealthy_metrics)