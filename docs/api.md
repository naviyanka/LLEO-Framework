# LLEO Framework API Documentation

## Core Components

### BaseModule

The foundation class for all LLEO modules, providing common functionality and standardized interfaces.

```python
class BaseModule(ABC):
	def __init__(self, framework):
		"""
		Initialize module with framework reference
		
		Args:
			framework: Framework instance providing configuration and utilities
		"""
```

#### Key Methods

##### run()
```python
@abstractmethod
async def run(self) -> Dict[str, Any]:
	"""
	Execute module functionality
	
	Returns:
		Dict containing module execution results
	"""
```

##### health_check()
```python
async def health_check(self) -> Dict[str, Any]:
	"""
	Check module health status
	
	Returns:
		Dict containing:
			- status: 'healthy' or 'unhealthy'
			- metrics: Current module metrics
			- resources: Resource usage warnings
	"""
```

##### run_with_monitoring()
```python
async def run_with_monitoring(self, func, *args, **kwargs) -> Any:
	"""
	Execute function with performance monitoring
	
	Args:
		func: Async function to execute
		*args: Function arguments
		**kwargs: Function keyword arguments
	
	Returns:
		Function execution result
	"""
```

### Usage Examples

#### Creating a Custom Module
```python
from core.modules.base import BaseModule

class CustomModule(BaseModule):
	def get_required_tools(self):
		return {
			'tool-name': '1.0.0'  # Minimum version required
		}
	
	async def run(self):
		# Initialize metrics
		self.metrics.total_tasks = 1
		
		try:
			# Run task with monitoring
			result = await self.run_with_monitoring(
				self._execute_task,
				arg1="value"
			)
			
			# Save results
			self._save_results(result, 'output.json')
			return result
			
		except Exception as e:
			self.logger.error(f"Task failed: {e}")
			return {'error': str(e)}
```

#### Resource Management
```python
# Automatic cleanup of temporary files
def process_data(self):
	temp_file = self._create_temp_file('data_', '.tmp')
	try:
		# Process data
		return result
	finally:
		# Cleanup handled automatically
		pass
```

#### Parallel Execution
```python
# Run multiple tasks in parallel
results = self.run_parallel(
	process_item,
	items,
	max_workers=4
)
```

### Best Practices

1. Resource Management
   - Use `_create_temp_file()` for temporary files
   - Always implement cleanup in finally blocks
   - Monitor resource usage with metrics

2. Error Handling
   - Use run_with_retry for unreliable operations
   - Log errors with appropriate severity
   - Include context in error messages

3. Performance
   - Use parallel execution for independent tasks
   - Monitor memory and disk usage
   - Implement rate limiting for API calls

4. Testing
   - Write unit tests for custom modules
   - Mock external dependencies
   - Test error handling paths
```