import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
from core.modules.base import BaseModule, ModuleMetrics

class TestModule(BaseModule):
	"""Test implementation of BaseModule"""
	def get_required_tools(self):
		return {
			'test-tool': '1.0.0'
		}
	
	async def run(self):
		return {'status': 'success'}

@pytest.fixture
def mock_framework():
	framework = Mock()
	framework.logger = Mock()
	framework.config.tools.rate_limit = 10
	framework.config.tools.burst_size = 100
	framework.config.tools.max_memory_percent = 90.0
	framework.config.tools.max_disk_percent = 90.0
	framework.config.tools.threads = 4
	framework.args = Mock()
	framework.session_manager.get_module_dir.return_value = '/tmp/test_module'
	return framework

@pytest.fixture
def test_module(mock_framework):
	with patch('core.modules.base.check_tool_exists', return_value=True):
		with patch('core.modules.base.psutil.virtual_memory') as mock_mem:
			with patch('core.modules.base.psutil.disk_usage') as mock_disk:
				mock_mem.return_value.percent = 50.0
				mock_disk.return_value.percent = 50.0
				module = TestModule(mock_framework)
				yield module

@pytest.mark.asyncio
async def test_module_initialization(test_module):
	"""Test module initialization"""
	assert test_module.metrics.start_time is not None
	assert test_module.metrics.total_tasks == 0
	assert test_module.metrics.completed_tasks == 0

@pytest.mark.asyncio
async def test_health_check(test_module):
	"""Test health check functionality"""
	health = await test_module.health_check()
	assert health['status'] == 'healthy'
	assert 'metrics' in health
	assert 'resources' in health

@pytest.mark.asyncio
async def test_run_with_monitoring(test_module):
	"""Test task monitoring"""
	async def mock_task():
		return "success"

	result = await test_module.run_with_monitoring(mock_task)
	assert result == "success"
	assert test_module.metrics.total_tasks == 1
	assert test_module.metrics.completed_tasks == 1

@pytest.mark.asyncio
async def test_run_with_retry(test_module):
	"""Test retry mechanism"""
	attempts = 0
	async def failing_task():
		nonlocal attempts
		attempts += 1
		if attempts < 3:
			raise Exception("Test error")
		return "success"

	result = await test_module.run_with_retry(failing_task, retries=3, delay=0.1)
	assert result == "success"
	assert attempts == 3

@pytest.mark.asyncio
async def test_resource_monitoring(test_module):
	"""Test resource monitoring"""
	with patch('core.modules.base.psutil.Process') as mock_process:
		mock_process.return_value.memory_percent.return_value = 95.0
		await test_module._update_metrics()
		assert test_module.metrics.memory_usage == 95.0
		test_module.framework.logger.warning.assert_called()

@pytest.mark.asyncio
async def test_cleanup(test_module, tmp_path):
	"""Test cleanup functionality"""
	test_file = tmp_path / "test.txt"
	test_file.write_text("test")
	test_module.temp_files.add(str(test_file))
	test_module.cleanup()
	assert not test_file.exists()

@pytest.mark.asyncio
async def test_version_comparison(test_module):
	"""Test version comparison logic"""
	assert test_module._version_satisfies("2.0.0", "1.0.0")
	assert not test_module._version_satisfies("1.0.0", "2.0.0")
	assert test_module._version_satisfies("1.0.0", "1.0.0")
	assert test_module._version_satisfies("1.1.0", "1.0.0")

def test_parallel_execution(test_module):
	"""Test parallel task execution"""
	def task(x):
		return x * 2

	items = [1, 2, 3, 4]
	results = test_module.run_parallel(task, items)
	assert sorted(results) == [2, 4, 6, 8]