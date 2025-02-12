# LLEO Framework Implementation Guide

## Module Implementation

### Core Module Structure
```python
from core.modules.base import BaseModule
from typing import Dict, Any, Optional
from pathlib import Path

class NewModule(BaseModule):
	def __init__(self, framework):
		super().__init__(framework)
		self.tools = {
			'tool1': self._run_tool1,
			'tool2': self._run_tool2
		}
		self.running_tasks = set()

	def get_required_tools(self) -> Dict[str, Optional[str]]:
		return {
			'tool1': '1.0.0',
			'tool2': '2.0.0'
		}

	async def run(self) -> Dict[str, Any]:
		try:
			results = {}
			for tool_name, tool_func in self.tools.items():
				result = await self.run_with_monitoring(tool_func)
				results[tool_name] = result
			return results
		finally:
			self.cleanup()
```

### Tool Integration
1. Tool Execution Method:
```python
async def _run_tool1(self, target: str) -> Dict[str, Any]:
	output_file = self._create_temp_file('tool1_output_', '.json')
	
	try:
		cmd = [
			'tool1',
			'-t', target,
			'-o', str(output_file),
			'--json'
		]
		
		result = await self.execute_tool(cmd)
		if not result.success:
			return {'error': result.error}
			
		return self._process_tool1_output(output_file)
	except Exception as e:
		self.logger.error(f"Tool1 execution failed: {e}")
		return {'error': str(e)}
```

2. Result Processing:
```python
def _process_tool1_output(self, output_file: Path) -> Dict[str, Any]:
	try:
		if output_file.exists():
			data = json.loads(output_file.read_text())
			return {
				'status': 'success',
				'findings': data.get('findings', []),
				'metadata': data.get('metadata', {})
			}
	except Exception as e:
		self.logger.error(f"Error processing tool1 output: {e}")
	return {'error': 'Failed to process output'}
```

## Feature Implementation

### New Configuration Options
1. Define Configuration Class:
```python
@dataclass_json
@dataclass
class NewFeatureConfig:
	enabled: bool = True
	max_items: int = 100
	timeout: int = 30
```

2. Update Secure Config:
```python
@dataclass_json
@dataclass
class SecureConfig:
	tools: ToolConfig
	new_feature: NewFeatureConfig
```

### Custom Metrics
1. Define Metrics Class:
```python
@dataclass
class CustomMetrics:
	start_time: datetime
	processed_items: int = 0
	success_rate: float = 0.0
	average_time: float = 0.0
```

2. Implement Collection:
```python
async def collect_metrics(self):
	metrics = CustomMetrics(start_time=datetime.now())
	try:
		# Collect metrics
		return metrics
	except Exception as e:
		self.logger.error(f"Metrics collection failed: {e}")
		return None
```

### Error Handling
1. Custom Exceptions:
```python
class ToolExecutionError(Exception):
	def __init__(self, tool: str, message: str, exit_code: int = None):
		self.tool = tool
		self.exit_code = exit_code
		super().__init__(f"{tool} failed: {message}")

class ResourceExhaustedError(Exception):
	def __init__(self, resource: str, limit: float, current: float):
		super().__init__(
			f"{resource} limit exceeded: {current:.1f}/{limit:.1f}"
		)
```

2. Error Recovery:
```python
async def recover_from_error(self, error: Exception) -> bool:
	if isinstance(error, ToolExecutionError):
		return await self._recover_tool_error(error)
	elif isinstance(error, ResourceExhaustedError):
		return await self._recover_resource_error(error)
	return False
```

## Testing Implementation

### Unit Tests
1. Module Tests:
```python
@pytest.mark.asyncio
async def test_new_module():
	framework = MockFramework()
	module = NewModule(framework)
	
	result = await module.run()
	assert result['status'] == 'success'
	assert 'findings' in result
```

2. Tool Tests:
```python
@pytest.mark.asyncio
async def test_tool_execution():
	with patch('subprocess.run') as mock_run:
		mock_run.return_value.returncode = 0
		mock_run.return_value.stdout = b'{"status": "success"}'
		
		result = await module._run_tool1('test.com')
		assert result['status'] == 'success'
```

### Integration Tests
```python
@pytest.mark.integration
async def test_module_integration():
	framework = create_test_framework()
	module = NewModule(framework)
	
	await framework.start_monitoring()
	result = await module.run()
	metrics = await framework.get_metrics()
	
	assert result['status'] == 'success'
	assert metrics.memory_usage < 90
```

## Performance Optimization

### Caching Implementation
```python
class ResultCache:
	def __init__(self, max_size: int = 1000):
		self.cache = {}
		self.max_size = max_size
		self._lock = asyncio.Lock()

	async def get(self, key: str) -> Optional[Dict]:
		async with self._lock:
			return self.cache.get(key)

	async def set(self, key: str, value: Dict):
		async with self._lock:
			if len(self.cache) >= self.max_size:
				self._evict_oldest()
			self.cache[key] = value
```

### Resource Management
```python
class ResourceManager:
	def __init__(self, limits: Dict[str, float]):
		self.limits = limits
		self.usage = {}
		self._lock = asyncio.Lock()

	async def check_resources(self) -> bool:
		async with self._lock:
			current = await self._get_current_usage()
			return all(
				current[resource] < limit
				for resource, limit in self.limits.items()
			)
```

## API Extensions

### REST API Implementation
```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.post("/scan")
async def start_scan(domain: str):
	try:
		framework = Framework()
		result = await framework.run_scan(domain)
		return result
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
```

### WebSocket Updates
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
	await websocket.accept()
	try:
		while True:
			data = await websocket.receive_json()
			updates = await process_updates(data)
			await websocket.send_json(updates)
	except WebSocketDisconnect:
		pass
```