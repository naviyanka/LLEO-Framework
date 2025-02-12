from typing import Dict, Any, List, Optional, Set, Type
from pathlib import Path
import json
import asyncio
import aiofiles
import shutil
from datetime import datetime
from .base_module import BaseModule, ToolResult
from core.utils.rate_limiter import RateLimiter
from core.utils.cache_manager import CacheManager

class WebFuzzingModule(BaseModule):
    def __init__(self, framework):
        super().__init__(framework)
        self.tools = {
            'dirsearch': self._run_dirsearch,
            'gobuster': self._run_gobuster,
            'ffuf': self._run_ffuf,
            'wfuzz': self._run_wfuzz,
            'katana': self._run_katana
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

    async def setup(self) -> None:
        """Setup module resources"""
        await super().setup()
        self.logger.info("Setting up web fuzzing module...")
        
        # Verify tool versions
        for tool, min_version in self.get_required_tools().items():
            try:
                if tool == 'dirsearch':
                    result = await self.execute_tool(['dirsearch', '--version'])
                elif tool == 'gobuster':
                    result = await self.execute_tool(['gobuster', 'version'])
                elif tool == 'ffuf':
                    result = await self.execute_tool(['ffuf', '-V'])
                elif tool == 'wfuzz':
                    result = await self.execute_tool(['wfuzz', '--version'])
                elif tool == 'katana':
                    result = await self.execute_tool(['katana', '-version'])
                else:
                    result = await self.execute_tool([tool, '--version'])
                    
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

        # Create necessary directories
        for dir_name in ['raw', 'processed', 'temp']:
            dir_path = self.output_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize rate limiter monitoring
        await self.rate_limiter.start_monitoring()

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
                shutil.rmtree(temp_dir)
            
            await super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def get_dependencies(self) -> List[Type]:
        """Get module dependencies"""
        return ['web_probing']

    def get_event_handlers(self) -> Dict[str, callable]:
        """Get event handlers"""
        return {}

    async def _run_implementation(self) -> Dict[str, Any]:
        """Actual module implementation"""
        return await self.run()

    def get_required_tools(self) -> Dict[str, Optional[str]]:
        """Return required tools and their minimum versions"""
        return {
            'dirsearch': '0.4.2',
            'gobuster': '3.1.0',
            'ffuf': '1.3.1',
            'wfuzz': '3.1.0',
            'katana': '1.0.0'
        }

    async def run(self) -> Dict[str, Any]:
        """Run web fuzzing tools"""
        try:
            await self.setup()
            self.logger.info("Starting web fuzzing...")
            
            results = {
                'directories': [],
                'files': [],
                'endpoints': [],
                'errors': []
            }
            
            targets = await self._get_targets()
            
            for target in targets:
                try:
                    self.logger.info(f"Running dirsearch on {target}")
                    dirsearch_results = await self._run_dirsearch(target)
                    if dirsearch_results:
                        results['directories'].extend(dirsearch_results.get('directories', []))
                        results['files'].extend(dirsearch_results.get('files', []))
                        results['endpoints'].extend(dirsearch_results.get('endpoints', []))
                
                    self.logger.info(f"Running gobuster on {target}")
                    gobuster_results = await self._run_gobuster(target)
                    if gobuster_results:
                        results['directories'].extend(gobuster_results.get('directories', []))
                        results['files'].extend(gobuster_results.get('files', []))
                        results['endpoints'].extend(gobuster_results.get('endpoints', []))
                
                    self.logger.info(f"Running ffuf on {target}")
                    ffuf_results = await self._run_ffuf(target)
                    if ffuf_results:
                        results['directories'].extend(ffuf_results.get('directories', []))
                        results['files'].extend(ffuf_results.get('files', []))
                        results['endpoints'].extend(ffuf_results.get('endpoints', []))
                
                    self.logger.info(f"Running wfuzz on {target}")
                    wfuzz_results = await self._run_wfuzz(target)
                    if wfuzz_results:
                        results['directories'].extend(wfuzz_results.get('directories', []))
                        results['files'].extend(wfuzz_results.get('files', []))
                        results['endpoints'].extend(wfuzz_results.get('endpoints', []))
                
                    self.logger.info(f"Running katana on {target}")
                    katana_results = await self._run_katana(target)
                    if katana_results:
                        results['directories'].extend(katana_results.get('directories', []))
                        results['files'].extend(katana_results.get('files', []))
                        results['endpoints'].extend(katana_results.get('endpoints', []))
                
                except Exception as e:
                    error_msg = f"Error in fuzzing {target}: {str(e)}"
                    self.logger.error(error_msg)
                    results['errors'].append(error_msg)
            
            # Remove duplicates while preserving order
            results['directories'] = list(dict.fromkeys(results['directories']))
            results['files'] = list(dict.fromkeys(results['files']))
            results['endpoints'] = list(dict.fromkeys(results['endpoints']))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in web fuzzing module: {str(e)}")
            return {"directories": [], "files": [], "endpoints": [], "errors": [str(e)]}
        finally:
            await self.cleanup()

    async def _get_targets(self) -> List[str]:
        """Get targets from web probing results"""
        try:
            results = await self.framework.session_manager.get_results("web_probing")
            if not results:
                self.logger.warning("No web probing results found, using target domain")
                return [f"http://{self.framework.target}"]
            
            targets = []
            for result in results:
                if isinstance(result, dict) and "url" in result:
                    targets.append(result["url"])
            
            if not targets:
                self.logger.warning("No valid targets found in web probing results, using target domain")
                targets = [f"http://{self.framework.target}"]
            
            return targets
        except Exception as e:
            self.logger.error(f"Error getting targets: {str(e)}")
            return [f"http://{self.framework.target}"]

    async def _run_dirsearch(self, target: str) -> Dict[str, Any]:
        """Run dirsearch for directory enumeration"""
        try:
            output_file = self.output_dir / 'raw' / f'dirsearch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                'dirsearch',
                '--url', target,
                '--wordlist', str(self.config.wordlists.content),
                '--format', 'json',
                '--output', str(output_file),
                '--random-agent',
                '--threads', str(self.config.tools.threads),
                '--timeout', str(self.config.tools.timeout),
                '--recursion-depth', '2'
            ]
            
            result = await self.execute_tool(cmd)
            if not result.success:
                return {'error': result.error}
            
            try:
                if output_file.exists():
                    with open(output_file) as f:
                        return json.load(f)
                return {'error': 'No output file generated'}
            except Exception as e:
                return {'error': f"Error processing dirsearch results: {e}"}
        except Exception as e:
            return {'error': f"Error in dirsearch: {e}"}

    async def _run_gobuster(self, target: str) -> Dict[str, Any]:
        """Run gobuster for directory enumeration"""
        try:
            output_file = self.output_dir / 'raw' / f'gobuster_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                'gobuster',
                'dir',
                '--url', target,
                '--wordlist', str(self.config.wordlists.content),
                '--output', str(output_file),
                '--threads', str(self.config.tools.threads),
                '--timeout', str(self.config.tools.timeout) + 's',
                '--no-error',
                '--quiet'
            ]
            
            result = await self.execute_tool(cmd)
            if not result.success:
                return {'error': result.error}
            
            try:
                if output_file.exists():
                    with open(output_file) as f:
                        return {'directories': [line.strip() for line in f if line.strip()]}
                return {'error': 'No output file generated'}
            except Exception as e:
                return {'error': f"Error processing gobuster results: {e}"}
        except Exception as e:
            return {'error': f"Error in gobuster: {e}"}

    async def _run_ffuf(self, target: str) -> Dict[str, Any]:
        """Run ffuf for directory enumeration"""
        try:
            output_file = self.output_dir / 'raw' / f'ffuf_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                'ffuf',
                '-u', target + '/FUZZ',
                '-w', str(self.config.wordlists.content),
                '-o', str(output_file),
                '-of', 'json',
                '-t', str(self.config.tools.threads),
                '-timeout', str(self.config.tools.timeout),
                '-s'
            ]
            
            result = await self.execute_tool(cmd)
            if not result.success:
                return {'error': result.error}
            
            try:
                if output_file.exists():
                    with open(output_file) as f:
                        return json.load(f)
                return {'error': 'No output file generated'}
            except Exception as e:
                return {'error': f"Error processing ffuf results: {e}"}
        except Exception as e:
            return {'error': f"Error in ffuf: {e}"}

    async def _run_wfuzz(self, target: str) -> Dict[str, Any]:
        """Run wfuzz for directory enumeration"""
        try:
            output_file = self.output_dir / 'raw' / f'wfuzz_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                'wfuzz',
                '-w', str(self.config.wordlists.content),
                '--hc', '404',
                '-f', str(output_file),
                '-o', 'json',
                '-t', str(self.config.tools.threads),
                '-Z',
                target + '/FUZZ'
            ]
            
            result = await self.execute_tool(cmd)
            if not result.success:
                return {'error': result.error}
            
            try:
                if output_file.exists():
                    with open(output_file) as f:
                        return json.load(f)
                return {'error': 'No output file generated'}
            except Exception as e:
                return {'error': f"Error processing wfuzz results: {e}"}
        except Exception as e:
            return {'error': f"Error in wfuzz: {e}"}

    async def _run_katana(self, target: str) -> Dict[str, Any]:
        """Run katana for crawling and directory enumeration"""
        try:
            output_file = self.output_dir / 'raw' / f'katana_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                'katana',
                '-u', target,
                '-jc',
                '-o', str(output_file),
                '-c', str(self.config.tools.threads),
                '-timeout', str(self.config.tools.timeout),
                '-silent'
            ]
            
            result = await self.execute_tool(cmd)
            if not result.success:
                return {'error': result.error}
            
            try:
                if output_file.exists():
                    with open(output_file) as f:
                        return json.load(f)
                return {'error': 'No output file generated'}
            except Exception as e:
                return {'error': f"Error processing katana results: {e}"}
        except Exception as e:
            return {'error': f"Error in katana: {e}"}
