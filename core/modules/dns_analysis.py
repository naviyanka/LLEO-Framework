from typing import Dict, Any, List, Optional, Set, Type
from pathlib import Path
import json
import asyncio
import aiofiles
from datetime import datetime, timedelta
import aiohttp
import aiodns
from cachetools import TTLCache
import re
from dataclasses import dataclass, field
from ..utils.rate_limiter import RateLimiter
from ..utils.cache_manager import CacheManager
from .base_module import BaseModule, ToolResult
import shutil
import tempfile
import os

@dataclass
class DNSResult:
    tool: str
    raw_output: Optional[Path] = None
    records: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration: float = 0.0
    success_rate: float = 0.0

class DNSAnalysisModule(BaseModule):
    # Define module dependencies
    dependencies = ['discovery']
    
    def __init__(self, framework):
        super().__init__(framework)
        self.tools = {
            'dnsx': self._run_dnsx,
            'altdns': self._run_altdns,
            'dnsgen': self._run_dnsgen,
            'massdns': self._run_massdns
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
        self.resolver = aiodns.DNSResolver()
        self.session = None

    async def setup(self) -> None:
        """Setup module resources"""
        await super().setup()
        self.logger.info("Setting up DNS analysis module...")
        
        # Create necessary directories
        for dir_name in ['raw', 'processed', 'temp']:
            dir_path = self.output_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize rate limiter monitoring
        await self.rate_limiter.start_monitoring()
        
        # Setup DNS resolver
        self.resolver = aiodns.DNSResolver()

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

    def get_required_tools(self) -> Dict[str, Optional[str]]:
        """Return required tools and their minimum versions"""
        return {
            'dnsx': '1.1.0',
            'altdns': '1.0.2',
            'dnsgen': '1.0.0',
            'massdns': '1.0.0'
        }

    def get_dependencies(self) -> List[Type]:
        """Get module dependencies"""
        return ['discovery']

    def get_event_handlers(self) -> Dict[str, callable]:
        """Get event handlers"""
        return {}

    async def run(self) -> Dict[str, Any]:
        try:
            self.logger.info("Setting up DNS analysis module...")
            results = {
                "dns_records": [],
                "errors": []
            }
            
            try:
                self.logger.info("Starting DNS analysis...")
                
                # Get targets from discovery module
                targets = await self._get_targets()
                if not targets:
                    self.logger.warning("No targets found for DNS analysis")
                    return results
                
                for target in targets:
                    try:
                        # Run dnsx
                        dnsx_results = await self._run_dnsx(target)
                        if dnsx_results and isinstance(dnsx_results, dict):
                            results["dns_records"].extend(dnsx_results.get("records", []))
                        
                        # Run altdns
                        altdns_results = await self._run_altdns(target)
                        if altdns_results and isinstance(altdns_results, dict):
                            results["dns_records"].extend(altdns_results.get("records", []))
                        
                        # Run dnsgen
                        dnsgen_results = await self._run_dnsgen(target)
                        if dnsgen_results and isinstance(dnsgen_results, dict):
                            results["dns_records"].extend(dnsgen_results.get("records", []))
                        
                        # Run massdns
                        massdns_results = await self._run_massdns(target)
                        if massdns_results and isinstance(massdns_results, dict):
                            results["dns_records"].extend(massdns_results.get("records", []))
                        
                    except Exception as e:
                        error_msg = f"Error analyzing {target}: {str(e)}"
                        self.logger.error(error_msg)
                        results["errors"].append(error_msg)
                
                # Remove duplicates while preserving order
                results["dns_records"] = list(dict.fromkeys(results["dns_records"]))
                
                return results
            except Exception as e:
                error_msg = f"Error in DNS analysis: {str(e)}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                return results
            
        except Exception as e:
            self.logger.error(f"Error in DNS analysis module: {str(e)}")
            return {"dns_records": [], "errors": [str(e)]}

    async def _get_targets(self) -> List[str]:
        try:
            results = await self.framework.session_manager.get_results("discovery")
            if not results:
                self.logger.warning("No discovery results found, using target domain")
                return [self.framework.target]
            
            targets = []
            for result in results:
                if isinstance(result, dict) and "subdomains" in result:
                    targets.extend(result["subdomains"])
                elif isinstance(result, str):
                    targets.append(result)
            
            if not targets:
                self.logger.warning("No valid targets found in discovery results, using target domain")
                targets = [self.framework.target]
            
            return targets
        except Exception as e:
            self.logger.error(f"Error getting targets: {str(e)}")
            return [self.framework.target]

    async def _run_dnsx(self, target: str) -> Dict[str, Any]:
        try:
            # Use a default wordlist if available
            wordlist = "/usr/share/wordlists/dns.txt"
            if not os.path.exists(wordlist):
                wordlist = "/usr/share/wordlists/subdomains.txt"
            if not os.path.exists(wordlist):
                self.logger.error("No suitable wordlist found for dnsx")
                return {"records": [], "errors": ["No suitable wordlist found"]}

            result = await self.execute_tool([
                "dnsx",
                "-d", target,
                "-w", wordlist,
                "-silent",
                "-a",
                "-aaaa",
                "-cname",
                "-mx",
                "-ns",
                "-txt",
                "-json"
            ])

            if not result.success:
                self.logger.error(f"Dnsx failed: {result.error}")
                return {"records": [], "errors": [result.error]}
            
            records = []
            if result.output:
                for line in result.output.split("\n"):
                    if line.strip():
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError:
                            continue
                        
            return {"records": records}
        except Exception as e:
            self.logger.error(f"Error in dnsx: {str(e)}")
            return {"records": [], "errors": [str(e)]}

    async def _run_altdns(self, target: str) -> Dict[str, Any]:
        try:
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as input_file:
                input_file.write(target + "\n")
                input_file_path = input_file.name
            
            output_file_path = input_file_path + ".out"
            
            # Use a default wordlist if available
            wordlist = "/usr/share/wordlists/altdns.txt"
            if not os.path.exists(wordlist):
                wordlist = "/usr/share/wordlists/words.txt"
            if not os.path.exists(wordlist):
                # Create a minimal wordlist if none exists
                wordlist = input_file_path + ".words"
                with open(wordlist, 'w') as f:
                    f.write("dev\nstaging\ntest\nprod\napi\nadmin\n")
            
            result = await self.execute_tool([
                "altdns",
                "-i", input_file_path,
                "-w", wordlist,
                "-o", output_file_path
            ])

            if not result.success:
                self.logger.error(f"Altdns failed: {result.error}")
                return {"records": [], "errors": [result.error]}
            
            records = []
            try:
                with open(output_file_path) as f:
                    for line in f:
                        if line.strip():
                            records.append({"domain": line.strip(), "type": "altdns"})
            except Exception as e:
                self.logger.error(f"Error reading altdns output: {str(e)}")
            finally:
                # Clean up temporary files
                try:
                    os.unlink(input_file_path)
                    os.unlink(output_file_path)
                    os.unlink(wordlist)
                except:
                    pass
                
            return {"records": records}
        except Exception as e:
            self.logger.error(f"Error in altdns: {str(e)}")
            return {"records": [], "errors": [str(e)]}

    async def _run_dnsgen(self, target: str) -> Dict[str, Any]:
        try:
            # Create temporary file for input
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as input_file:
                input_file.write(target + "\n")
                input_file_path = input_file.name
            
            result = await self.execute_tool(["dnsgen", input_file_path])
            if not result.success:
                self.logger.error(f"Dnsgen failed: {result.error}")
                return {"records": [], "errors": [result.error]}
            
            records = []
            if result.output:
                for line in result.output.split("\n"):
                    if line.strip():
                        records.append({"domain": line.strip(), "type": "dnsgen"})
                    
            try:
                os.unlink(input_file_path)
            except:
                pass
                    
            return {"records": records}
        except Exception as e:
            self.logger.error(f"Error in dnsgen: {str(e)}")
            return {"records": [], "errors": [str(e)]}

    async def _run_massdns(self, target: str) -> Dict[str, Any]:
        try:
            # Create temporary file for input
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as input_file:
                input_file.write(target + "\n")
                input_file_path = input_file.name
            
            # Use a default resolver list if available
            resolver_list = "/usr/share/wordlists/resolvers.txt"
            if not os.path.exists(resolver_list):
                # Create a minimal resolver list if none exists
                resolver_list = input_file_path + ".resolvers"
                with open(resolver_list, 'w') as f:
                    f.write("8.8.8.8\n8.8.4.4\n1.1.1.1\n1.0.0.1\n")
            
            result = await self.execute_tool([
                "massdns",
                "-r", resolver_list,
                "-t", "A",
                "-o", "J",
                input_file_path
            ])

            if not result.success:
                self.logger.error(f"Massdns failed: {result.error}")
                return {"records": [], "errors": [result.error]}
            
            records = []
            if result.output:
                for line in result.output.split("\n"):
                    if line.strip():
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError:
                            continue
                        
            try:
                os.unlink(input_file_path)
                if resolver_list.endswith(".resolvers"):
                    os.unlink(resolver_list)
            except:
                pass
                    
            return {"records": records}
        except Exception as e:
            self.logger.error(f"Error in massdns: {str(e)}")
            return {"records": [], "errors": [str(e)]}
