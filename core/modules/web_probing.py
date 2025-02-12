import asyncio
import json
from typing import Dict, Any, List, Optional, Set, Type
from pathlib import Path
from datetime import datetime
from core.utils.rate_limiter import RateLimiter
from core.utils.cache_manager import CacheManager
from .base_module import BaseModule, ToolResult

class WebProbingModule(BaseModule):
    def __init__(self, framework):
        super().__init__(framework)
        self.tools = {
            'naabu': self._run_naabu,
            'httpx': self._run_httpx
        }
        self.running_tasks: Set[asyncio.Task] = set()
        self.max_concurrent_tasks = self.config.tools.threads
        self.rate_limiter = RateLimiter(
            calls_per_second=self.config.tools.rate_limit,
            burst_size=self.config.tools.burst_size
        )
        self.cache = CacheManager(
            cache_dir=self.output_dir / 'cache',
            ttl=self.config.performance.cache_ttl
        )

    def get_required_tools(self) -> Dict[str, Optional[str]]:
        """Return required tools and their minimum versions"""
        return {
            'naabu': '2.1.0',
            'httpx': '1.3.0'
        }

    async def setup(self) -> None:
        """Setup module resources"""
        await super().setup()
        self.logger.info("Setting up web probing module...")
        
        # Verify tool versions
        for tool, min_version in self.get_required_tools().items():
            try:
                if tool == 'naabu':
                    result = await self.execute_tool(['naabu', '--version'])
                elif tool == 'httpx':
                    result = await self.execute_tool(['httpx', '--version'])
                else:
                    result = await self.execute_tool([tool, '-version'])
                    
                if result.success:
                    version = result.output
                    if version:
                        self.logger.info(f"Found {tool} version {version}")
                    else:
                        self.logger.warning(f"Could not determine {tool} version")
                else:
                    self.logger.error(f"Error checking {tool} version: {result.error}")
            except Exception as e:
                self.logger.error(f"Error checking {tool} version: {e}")

    async def cleanup(self) -> None:
        """Cleanup module resources"""
        try:
            # Stop rate limiter monitoring
            await self.rate_limiter.stop_monitoring()
            
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
            
            await super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def get_dependencies(self) -> List[Type]:
        """Get module dependencies"""
        return []

    def get_event_handlers(self) -> Dict[str, callable]:
        """Get event handlers"""
        return {}

    async def run(self) -> Dict[str, Any]:
        """Run web probing tools"""
        try:
            await self.setup()
            self.logger.info("Starting web probing...")
            
            # Get targets from discovery results
            targets = await self._get_targets()
            if not targets:
                self.logger.warning("No discovery results found, using target domain")
                targets = [self.framework.args.domain]
            
            results = {}
            
            # Run naabu for port scanning
            naabu_results = await self._run_naabu(targets)
            if naabu_results and naabu_results.success:
                results['ports'] = naabu_results.output
            
            # Run httpx for web probing
            httpx_results = await self._run_httpx(targets)
            if httpx_results and httpx_results.success:
                results['web'] = httpx_results.output
            
            return results
            
        except Exception as e:
            self.logger.error(f"Critical error in web probing module: {e}")
            return {'error': str(e)}
        finally:
            await self.cleanup()

    async def _run_naabu(self, targets: List[str]) -> ToolResult:
        """Run naabu port scanner"""
        try:
            output_file = self.output_dir / 'naabu_results.txt'
            
            cmd = [
                'naabu',
                '--silent',
                '--json',
                '--output', str(output_file)
            ]
            cmd.extend(['--host', ','.join(targets)])
            
            result = await self.execute_tool(cmd)
            if not result.success:
                self.logger.error(f"Naabu failed: {result.error}")
                return result
            
            if output_file.exists():
                try:
                    results = []
                    for line in output_file.read_text().splitlines():
                        if line.strip():
                            try:
                                results.append(json.loads(line))
                            except json.JSONDecodeError:
                                self.logger.warning(f"Failed to parse naabu result line: {line}")
                    
                    result.output = results
                    return result
                except Exception as e:
                    self.logger.error(f"Error reading naabu results: {e}")
                    return ToolResult(success=False, error=str(e), exit_code=-1)
            
            return ToolResult(success=False, error="No output file generated", exit_code=-1)
            
        except Exception as e:
            self.logger.error(f"Error in naabu: {e}")
            return ToolResult(success=False, error=str(e), exit_code=-1)

    async def _run_httpx(self, targets: List[str]) -> ToolResult:
        """Run httpx web prober"""
        try:
            output_file = self.output_dir / 'httpx_results.json'
            
            cmd = [
                'httpx',
                '--silent',
                '--json',
                '--output', str(output_file),
                '--status-code',
                '--title',
                '--web-server',
                '--tech-detect',
                '--follow-redirects'
            ]
            cmd.extend(['--url', ','.join(targets)])
            
            result = await self.execute_tool(cmd)
            if not result.success:
                self.logger.error(f"Httpx failed: {result.error}")
                return result
            
            if output_file.exists():
                try:
                    results = []
                    for line in output_file.read_text().splitlines():
                        if line.strip():
                            try:
                                results.append(json.loads(line))
                            except json.JSONDecodeError:
                                self.logger.warning(f"Failed to parse httpx result line: {line}")
                    
                    result.output = results
                    return result
                except Exception as e:
                    self.logger.error(f"Error reading httpx results: {e}")
                    return ToolResult(success=False, error=str(e), exit_code=-1)
            
            return ToolResult(success=False, error="No output file generated", exit_code=-1)
            
        except Exception as e:
            self.logger.error(f"Error in httpx: {e}")
            return ToolResult(success=False, error=str(e), exit_code=-1)

    async def _get_targets(self) -> List[str]:
        """Get targets from discovery results"""
        try:
            discovery_results = await self.framework.session_manager.get_results('discovery')
            if discovery_results and 'subdomains' in discovery_results:
                return discovery_results['subdomains']
        except Exception as e:
            self.logger.error(f"Error getting discovery results: {e}")
        return []