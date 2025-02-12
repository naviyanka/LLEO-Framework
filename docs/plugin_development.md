# LLEO Framework Plugin Development Guide

## Plugin System Overview

### Plugin Architecture
- Plugins are Python modules that extend core functionality
- Each plugin is a self-contained package
- Plugins can add new modules, tools, or utilities
- Plugin configuration is managed through the framework

### Plugin Directory Structure
```
plugins/
├── my_plugin/
│   ├── __init__.py
│   ├── module.py
│   ├── tools.json
│   ├── config.yml
│   └── tests/
│       ├── __init__.py
│       └── test_module.py
```

## Creating a Plugin

### Basic Plugin Template
```python
from core.modules.base import BaseModule
from typing import Dict, Any

class MyPlugin(BaseModule):
	"""Custom plugin implementation"""
	
	def __init__(self, framework):
		super().__init__(framework)
		self.plugin_config = self._load_plugin_config()
		self.tools = self._initialize_tools()
	
	def get_required_tools(self) -> Dict[str, str]:
		return {
			'custom-tool': '1.0.0'
		}
	
	async def run(self) -> Dict[str, Any]:
		"""Plugin execution logic"""
		try:
			results = await self._execute_plugin_tasks()
			return {
				'status': 'success',
				'results': results
			}
		except Exception as e:
			self.logger.error(f"Plugin execution failed: {e}")
			return {'error': str(e)}
```

### Plugin Configuration
```yaml
# config.yml
plugin:
  name: "My Plugin"
  version: "1.0.0"
  description: "Custom functionality plugin"
  author: "Your Name"
  
settings:
  enabled: true
  max_threads: 4
  timeout: 30
  
tools:
  custom-tool:
	path: /usr/local/bin/custom-tool
	args:
	  - "--json"
	  - "--quiet"
```

### Tool Integration
```python
def _initialize_tools(self) -> Dict[str, callable]:
	"""Initialize plugin tools"""
	return {
		'custom-tool': self._run_custom_tool
	}

async def _run_custom_tool(self, target: str) -> Dict[str, Any]:
	"""Execute custom tool"""
	output_file = self._create_temp_file('custom_tool_', '.json')
	
	try:
		cmd = [
			'custom-tool',
			'-t', target,
			'-o', str(output_file)
		]
		
		result = await self.execute_tool(cmd)
		return self._process_custom_tool_output(result, output_file)
	except Exception as e:
		self.logger.error(f"Custom tool execution failed: {e}")
		return {'error': str(e)}
```

## Plugin Integration

### Registration
```python
# __init__.py
from .module import MyPlugin

def register_plugin(framework):
	"""Register plugin with framework"""
	return {
		'name': 'my_plugin',
		'module': MyPlugin,
		'config': 'config.yml',
		'tools': 'tools.json'
	}
```

### Tool Definition
```json
{
	"custom-tool": {
		"name": "custom-tool",
		"version": "1.0.0",
		"path": "/usr/local/bin/custom-tool",
		"installer": "go",
		"repository": "github.com/user/custom-tool",
		"dependencies": []
	}
}
```

## Plugin Development Best Practices

### Configuration Management
```python
def _load_plugin_config(self) -> Dict[str, Any]:
	"""Load plugin configuration"""
	try:
		config_path = self.get_plugin_path() / 'config.yml'
		return self.load_yaml_config(config_path)
	except Exception as e:
		self.logger.error(f"Failed to load plugin config: {e}")
		return {}

def get_plugin_path(self) -> Path:
	"""Get plugin directory path"""
	return Path(__file__).parent
```

### Resource Management
```python
async def _execute_plugin_tasks(self) -> Dict[str, Any]:
	"""Execute plugin tasks with resource management"""
	async with self.resource_manager() as rm:
		if not await rm.check_resources():
			raise ResourceExhaustedError("Insufficient resources")
		return await self._run_tasks()
```

### Error Handling
```python
class PluginError(Exception):
	"""Base class for plugin errors"""
	pass

class PluginConfigError(PluginError):
	"""Plugin configuration error"""
	pass

class PluginToolError(PluginError):
	"""Plugin tool execution error"""
	pass
```

## Testing Plugins

### Unit Tests
```python
import pytest
from my_plugin.module import MyPlugin

@pytest.fixture
def plugin(mock_framework):
	return MyPlugin(mock_framework)

@pytest.mark.asyncio
async def test_plugin_execution(plugin):
	result = await plugin.run()
	assert result['status'] == 'success'
```

### Integration Tests
```python
@pytest.mark.integration
async def test_plugin_integration(framework):
	plugin = MyPlugin(framework)
	await framework.register_plugin(plugin)
	
	result = await framework.run_plugin('my_plugin')
	assert result['status'] == 'success'
```

## Plugin Distribution

### Package Structure
```
my_plugin/
├── setup.py
├── README.md
├── requirements.txt
├── my_plugin/
│   ├── __init__.py
│   ├── module.py
│   └── config.yml
└── tests/
```

### Setup Configuration
```python
# setup.py
from setuptools import setup, find_packages

setup(
	name='lleo-my-plugin',
	version='1.0.0',
	packages=find_packages(),
	install_requires=[
		'lleo-framework>=1.0.0',
		'custom-dependency>=2.0.0'
	],
	entry_points={
		'lleo.plugins': [
			'my_plugin = my_plugin:register_plugin'
		]
	}
)
```

## Plugin Maintenance

### Version Management
- Follow semantic versioning
- Document breaking changes
- Maintain compatibility matrix
- Test against framework versions

### Documentation
- Maintain README.md
- Document configuration options
- Provide usage examples
- Include troubleshooting guide

### Updates
- Monitor dependency updates
- Test with new framework versions
- Release security patches
- Update documentation