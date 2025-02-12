from typing import Dict, Any, List, Optional, Set, Type
from pathlib import Path
import json
import yaml
from datetime import datetime
from .base_module import BaseModule, ToolResult
import asyncio
from dataclasses import dataclass
from ..utils.secure_config import ConfigManager
from ..utils.tool_checker import check_tool_exists, run_tool
import os
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..utils.rate_limiter import RateLimiter
from ..utils.cache_manager import CacheManager

@dataclass
class DiscoveryResult:
    tool: str
    raw_output: Optional[Path] = None
    subdomains: List[str] = None
    urls: List[str] = None
    error: Optional[str] = None
    duration: float = 0.0

class DiscoveryModule(BaseModule):
    def __init__(self, framework):
        super().__init__(framework)
        self.tools = {
            'subfinder': self._run_subfinder,
            'amass': self._run_amass,
            'findomain': self._run_findomain
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
        self.session = None

    def _load_config(self):
        """Load configuration from config.yml"""
        try:
            with open("config/config.yml", 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return {}

    async def setup(self) -> None:
        """Setup module resources"""
        await super().setup()
        self.logger.info("Setting up discovery module...")
        
        # Verify tool versions
        for tool, min_version in self.get_required_tools().items():
            try:
                result = await self.execute_tool([tool, '-version'])
                if result['success']:
                    version = result['output']
                    if version:
                        self.logger.info(f"Found {tool} version {version}")
                    else:
                        self.logger.warning(f"Could not determine {tool} version")
                else:
                    self.logger.error(f"Error checking {tool} version: {result['error']}")
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
                shutil.rmtree(temp_dir)
            
            await super().cleanup()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def get_required_tools(self) -> Dict[str, Optional[str]]:
        """Return required tools and their minimum versions"""
        return {
            'subfinder': '2.5.0',
            'amass': '3.19.0',
            'findomain': '8.2.0'
        }

    def get_dependencies(self) -> List[Type]:
        """Get module dependencies"""
        return []

    def get_event_handlers(self) -> Dict[str, callable]:
        """Get event handlers"""
        return {}

    async def run(self) -> Dict[str, Any]:
        try:
            self.logger.info("\n=== Starting Discovery Module ===")
            
            # Initialize results
            results = {
                "subdomains": [],
                "errors": []
            }
            
            # Run all tools in parallel
            tool_tasks = []
            for tool_name, tool_func in self.tools.items():
                if tool_name in self.tool_status and self.tool_status[tool_name]['installed']:
                    self.logger.info(f"Starting {tool_name}...")
                    task = asyncio.create_task(tool_func(self.framework.target))
                    tool_tasks.append((tool_name, task))
            
            # Wait for all tools to complete
            for tool_name, task in tool_tasks:
                try:
                    tool_result = await task
                    if 'subdomains' in tool_result:
                        results['subdomains'].extend(tool_result['subdomains'])
                    if 'errors' in tool_result:
                        results['errors'].extend(tool_result['errors'])
                except Exception as e:
                    self.logger.error(f"Error in {tool_name}: {str(e)}")
                    results['errors'].append(f"{tool_name} error: {str(e)}")
            
            # Remove duplicates while preserving order
            results["subdomains"] = list(dict.fromkeys(results["subdomains"]))
            
            if not results["subdomains"]:
                self.logger.warning("No subdomains found")
                results["subdomains"].append(self.framework.target)
            else:
                self.logger.info(f"Total unique subdomains found: {len(results['subdomains'])}")
            
            # Save results
            output_file = self.output_dir / 'processed' / 'subdomains.txt'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                for subdomain in results['subdomains']:
                    f.write(f"{subdomain}\n")
            self.logger.info(f"Results saved to {output_file}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in discovery module: {str(e)}")
            return {"subdomains": [self.framework.target], "errors": [str(e)]}

    async def _run_subfinder(self, target: str) -> Dict[str, Any]:
        """Run subfinder for subdomain discovery"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / 'raw' / f'subfinder_{timestamp}.txt'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            timeout = getattr(self.config.tools, 'timeout', 600)  # Default 10 minutes
            self.logger.info(f"Running subfinder with {timeout}s timeout")
            
            cmd = [
                'subfinder',
                '-d', target,
                '-silent',
                '-o', str(output_file)
            ]
            
            result = await self.execute_tool(cmd, timeout=timeout)
            if not result.success:
                self.logger.error(f"Subfinder failed: {result.error}")
                return {"subdomains": [], "errors": [result.error]}
            
            subdomains = []
            if output_file.exists():
                with open(output_file) as f:
                    subdomains = [line.strip() for line in f if line.strip()]
                self.logger.info(f"Subfinder found {len(subdomains)} subdomains")
            
            return {"subdomains": subdomains}
        except Exception as e:
            self.logger.error(f"Error in subfinder: {str(e)}")
            return {"subdomains": [], "errors": [str(e)]}

    async def _run_amass(self, target: str) -> Dict[str, Any]:
        """Run amass for subdomain discovery"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / 'raw' / f'amass_{timestamp}.txt'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            timeout = getattr(self.config.tools, 'timeout', 1800)  # Default 30 minutes
            self.logger.info(f"Running amass with {timeout}s timeout")
            
            cmd = [
                'amass',
                'enum',
                '-passive',
                '-d', target,
                '-o', str(output_file)
            ]
            
            result = await self.execute_tool(cmd, timeout=timeout)
            if not result.success:
                self.logger.error(f"Amass failed: {result.error}")
                return {"subdomains": [], "errors": [result.error]}
            
            subdomains = []
            if output_file.exists():
                with open(output_file) as f:
                    subdomains = [line.strip() for line in f if line.strip()]
                self.logger.info(f"Amass found {len(subdomains)} subdomains")
            
            return {"subdomains": subdomains}
        except Exception as e:
            self.logger.error(f"Error in amass: {str(e)}")
            return {"subdomains": [], "errors": [str(e)]}

    async def _run_findomain(self, target: str) -> Dict[str, Any]:
        """Run findomain for subdomain discovery"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / 'raw' / f'findomain_{timestamp}.txt'
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            timeout = getattr(self.config.tools, 'timeout', 600)  # Default 10 minutes
            self.logger.info(f"Running findomain with {timeout}s timeout")
            
            cmd = [
                'findomain',
                '-t', target,
                '-q',
                '-o', str(output_file)
            ]
            
            result = await self.execute_tool(cmd, timeout=timeout)
            if not result.success:
                self.logger.error(f"Findomain failed: {result.error}")
                return {"subdomains": [], "errors": [result.error]}
            
            subdomains = []
            if output_file.exists():
                with open(output_file) as f:
                    subdomains = [line.strip() for line in f if line.strip()]
                self.logger.info(f"Findomain found {len(subdomains)} subdomains")
            
            return {"subdomains": subdomains}
        except Exception as e:
            self.logger.error(f"Error in findomain: {str(e)}")
            return {"subdomains": [], "errors": [str(e)]}

    def create_output_directory(self, domain):
        """Create a timestamped output directory for the domain"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"output/{domain}_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def run_findomain(self, domain, output_dir):
        """Run findomain and save output in domain-specific directory"""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Run findomain
            findomain_cmd = f"findomain --output --quiet --target {domain}"
            subprocess.run(findomain_cmd, shell=True, check=True)
            
            # Move output to domain directory
            if os.path.exists(f"{domain}.txt"):
                output_file = f"{output_dir}/findomain_results.txt"
                shutil.move(f"{domain}.txt", output_file)
                print(f"[+] Findomain results saved to: {output_file}")
                return output_file
                
        except subprocess.CalledProcessError as e:
            print(f"ERROR Findomain execution failed: {str(e)}")
        except Exception as e:
            print(f"ERROR Error in findomain: {str(e)}")
        return None

    def run_discovery(self, domain):
        """Main function to run all discovery tools"""
        # Create output directory for this scan
        output_dir = self.create_output_directory(domain)
        print(f"[+] Created output directory: {output_dir}")
        
        # Run tools and save results
        findomain_results = self.run_findomain(domain, output_dir)
        
        # Add other tools here...
        
        return output_dir

    def _merge_subdomain_results(self):
        """Merge all tool results into one main file and process the paths"""
        try:
            # Main output file for all unique subdomains
            main_output = os.path.join(self.framework.output_dir, 'enumerated_subdomains.txt')
            all_subdomains = set()  # Using set to avoid duplicates

            # Process each tool's output file
            for tool_name in self.tools.keys():
                tool_file = os.path.join(self.framework.output_dir, f'{tool_name}_{self.framework.args.domain}.txt')
                if os.path.exists(tool_file):
                    with open(tool_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                # Handle cases where line contains paths
                                if '/' in line:
                                    # Extract subdomain and path
                                    parts = line.split('/', 1)
                                    subdomain = parts[0]
                                    path = parts[1] if len(parts) > 1 else ''
                                    
                                    # Add both full path and subdomain
                                    all_subdomains.add(line)  # Full entry with path
                                    all_subdomains.add(subdomain)  # Just the subdomain
                                else:
                                    all_subdomains.add(line)

            # Write all unique results to main file
            with open(main_output, 'w') as f:
                for subdomain in sorted(all_subdomains):
                    f.write(f"{subdomain}\n")

            self.logger.info(f"Merged {len(all_subdomains)} unique subdomains into {main_output}")
            return main_output

        except Exception as e:
            self.logger.error(f"Error merging subdomain results: {str(e)}")
            return None

    def run_tools_in_category(self, category, domain):
        """Run all tools in a category in parallel"""
        if category not in self.tools:
            self.logger.error(f"Category {category} not found")
            return {}

        tools = {category: self.tools[category]}
        results = {}

        with ThreadPoolExecutor(max_workers=len(tools)) as executor:
            future_to_tool = {
                executor.submit(tool_func, domain): tool_name
                for tool_name, tool_func in tools.items()
            }

            for future in as_completed(future_to_tool):
                tool_name = future_to_tool[future]
                try:
                    results[tool_name] = future.result()
                except Exception as e:
                    self.logger.error(f"Error in {tool_name}: {str(e)}")
                    results[tool_name] = {'error': str(e)}

        return results

    def merge_and_filter_results(self):
        """Merge and filter results into subdomains and URLs"""
        output_dir = self.framework.output_dir
        merged_subdomains = os.path.join(output_dir, 'merged_subdomains.txt')
        merged_urls = os.path.join(output_dir, 'merged_urls.txt')

        subdomains = set()
        urls = set()

        # Process each tool's output file
        for tool_name in self.tools.keys():
            output_file = os.path.join(output_dir, f'{tool_name}_{self.framework.args.domain}.txt')
            if os.path.exists(output_file):
                with open(output_file, 'r') as f:
                    for line in f.readlines():
                        line = line.strip()
                        if line:
                            if '://' in line or '/' in line:
                                urls.add(line)
                            else:
                                subdomains.add(line)

        # Write merged results
        with open(merged_subdomains, 'w') as f:
            f.write('\n'.join(sorted(subdomains)))

        with open(merged_urls, 'w') as f:
            f.write('\n'.join(sorted(urls)))

        return {
            'subdomains_file': merged_subdomains,
            'urls_file': merged_urls,
            'subdomain_count': len(subdomains),
            'url_count': len(urls)
        }

    async def _run_tools_in_category(self, category: str, tools: Dict[str, Any]) -> Dict[str, Any]:
        """Run all tools in a category in parallel"""
        results = {}
        tasks = []

        for tool_name, tool_func in tools.items():
            tasks.append(self._run_tool(tool_name, tool_func))

        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for tool_name, result in zip(tools.keys(), completed_tasks):
            if isinstance(result, Exception):
                self.logger.error(f"Error in {tool_name}: {str(result)}")
                results[tool_name] = {'error': str(result)}
            else:
                results[tool_name] = result

        return results

    async def _run_tool(self, tool_name: str, tool_func) -> Dict[str, Any]:
        """Run a single tool with proper error handling"""
        try:
            self.logger.info(f"Running {tool_name}...")
            return await tool_func(self.framework.args.domain)
        except Exception as e:
            self.logger.error(f"Error in {tool_name}: {str(e)}")
            return {'error': str(e)}

    async def _run_subfinder(self, domain: str) -> DiscoveryResult:
        """Run subfinder with improved error handling"""
        output_file = self.output_dir / f'subfinder_{domain}.txt'
        
        cmd = [
            'subfinder',
            '-d', domain,
            '-all',
            '-silent',
            '-o', str(output_file)
        ]
        
        result = await self.execute_tool(cmd)
        if not result.success:
            return DiscoveryResult(tool='subfinder', error=result.error)

        try:
            subdomains = output_file.read_text().splitlines() if output_file.exists() else []
            return DiscoveryResult(
                tool='subfinder',
                raw_output=output_file,
                subdomains=[s.strip() for s in subdomains if s.strip()]
            )
        except Exception as e:
            return DiscoveryResult(tool='subfinder', error=str(e))

    async def _merge_and_filter_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Merge and filter results with improved error handling"""
        merged = {
            'subdomains': set(),
            'urls': set(),
            'timestamp': datetime.now().isoformat()
        }

        try:
            for category_results in results.values():
                for tool_results in category_results.values():
                    if isinstance(tool_results, dict):
                        if 'subdomains' in tool_results:
                            merged['subdomains'].update(tool_results['subdomains'])
                        if 'urls' in tool_results:
                            merged['urls'].update(tool_results['urls'])

            # Save merged results to files
            subdomains_file = self.output_dir / 'merged_subdomains.txt'
            urls_file = self.output_dir / 'merged_urls.txt'

            subdomains_file.write_text('\n'.join(sorted(merged['subdomains'])))
            urls_file.write_text('\n'.join(sorted(merged['urls'])))

            return {
                'subdomains_file': str(subdomains_file),
                'urls_file': str(urls_file),
                'subdomain_count': len(merged['subdomains']),
                'url_count': len(merged['urls']),
                'timestamp': merged['timestamp']
            }

        except Exception as e:
            self.logger.error(f"Error merging results: {e}")
            return {
                'error': str(e),
                'subdomain_count': 0,
                'url_count': 0,
                'timestamp': datetime.now().isoformat()
            }

    def _create_web_probing_input(self, processed_results):
        """Create input files for web probing module"""
        # Create a combined file with all unique targets (subdomains and URLs)
        combined_targets = self.session.get_processed_path('discovery', 'combined_targets.txt')
        with open(combined_targets, 'w') as f:
            # Write all subdomains with http/https prefix
            for subdomain in sorted(processed_results['subdomains']):
                f.write(f"http://{subdomain}\n")
                f.write(f"https://{subdomain}\n")
            
            # Write all URLs that were discovered
            for url in sorted(processed_results['urls']):
                if not url.startswith('http'):
                    url = f"https://{url}"
                f.write(f"{url}\n")
        
        self.logger.info(f"Created combined targets file for web probing: {combined_targets}")
        return combined_targets

    def _process_results(self, results):
        """Process and merge results from all tools"""
        processed = {
            'subdomains': set(),
            'urls': set(),  # Full URLs with paths
            'technologies': {},
            'waf': {},
            'timestamp': datetime.now().isoformat(),
            'target_domain': self.framework.args.domain
        }

        # Process results from all tools
        for tool_name, result in results.items():
            if 'error' in result:
                continue

            # Process raw output files to extract both subdomains and full URLs
            raw_output = result.get('raw_output')
            if raw_output and os.path.exists(raw_output):
                with open(raw_output) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        # Handle URLs with paths
                        if '/' in line:
                            processed['urls'].add(line)
                            # Also extract subdomain from URL
                            domain_part = line.split('/')[0]
                            if domain_part.endswith(self.framework.args.domain):
                                processed['subdomains'].add(domain_part)
                        else:
                            # Handle pure subdomains
                            if line.endswith(self.framework.args.domain):
                                processed['subdomains'].add(line)

            # Process tool-specific outputs
            if tool_name == 'whatweb' and 'technologies' in result:
                processed['technologies'].update(result['technologies'])
            elif tool_name == 'wafw00f' and 'waf' in result:
                processed['waf'].update(result['waf'])

        return processed

    def _save_processed_results(self, processed):
        """Save processed results in organized structure"""
        # Save subdomains
        subdomains_file = self.session.get_processed_path('discovery', 'subdomains.txt')
        with open(subdomains_file, 'w') as f:
            for subdomain in sorted(processed['subdomains']):
                f.write(f"{subdomain}\n")

        # Save URLs with paths
        urls_file = self.session.get_processed_path('discovery', 'urls.txt')
        with open(urls_file, 'w') as f:
            for url in sorted(processed['urls']):
                f.write(f"{url}\n")

        # Save technologies
        tech_file = self.session.get_processed_path('discovery', 'technologies.json')
        with open(tech_file, 'w') as f:
            json.dump(processed['technologies'], f, indent=4)

        # Save WAF information
        waf_file = self.session.get_processed_path('discovery', 'waf.json')
        with open(waf_file, 'w') as f:
            json.dump(processed['waf'], f, indent=4)

        # Save summary
        summary = {
            'timestamp': processed['timestamp'],
            'target_domain': processed['target_domain'],
            'counts': {
                'subdomains': len(processed['subdomains']),
                'urls': len(processed['urls']),
                'technologies': len(processed['technologies']),
                'waf_detected': bool(processed['waf'])
            }
        }
        summary_file = self.session.get_processed_path('discovery', 'summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=4)

        self.logger.info(f"Found {len(processed['subdomains'])} unique subdomains")
        self.logger.info(f"Found {len(processed['urls'])} unique URLs with paths")

def load_api_keys():
    """Load API keys from config file"""
    try:
        config_path = "config/keys.json"
        with open(config_path, 'r') as f:
            keys = json.load(f)
            return keys.get('securitytrails_key')
    except Exception as e:
        print(f"ERROR Loading API keys: {str(e)}")
        return None

def load_haktrails_config():
    """Load HakTrails configuration from local config.yml"""
    try:
        # Use config.yml from project directory
        config_path = "config/config.yml"
        
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config.get('securitytrails', {}).get('key')
    except Exception as e:
        print(f"ERROR Loading HakTrails config: {str(e)}")
        return None

def run_haktrails(domain, output_dir):
    """Run haktrails with API from local config"""
    try:
        # Check for API key
        api_key = load_haktrails_config()
        if not api_key:
            print("WARNING Skipping haktrails: SecurityTrails API key not configured in config/config.yml")
            return None
            
        # Set API key as environment variable
        os.environ['SECURITYTRAILS_KEY'] = api_key
            
        # Prepare output file
        output_file = f"{output_dir}/haktrails_results.txt"
        
        # Run haktrails command
        haktrails_cmd = f"haktrails subdomains {domain} > {output_file}"
        subprocess.run(haktrails_cmd, shell=True, check=True)
        
        print(f"[+] HakTrails results saved to: {output_file}")
        return output_file
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR HakTrails execution failed: {str(e)}")
    except Exception as e:
        print(f"ERROR Error in haktrails: {str(e)}")
    return None 