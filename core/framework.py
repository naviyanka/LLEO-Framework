import asyncio
from typing import Dict, Any, Optional, Type, List, Set
from pathlib import Path
import signal
import sys
from datetime import datetime
import networkx as nx
from tqdm.asyncio import tqdm
from .utils.secure_config import ConfigManager
from .utils.logger import Logger
from .utils.session_manager import SessionManager
from .utils.monitor import PerformanceMonitor
from .utils.tool_manager import ToolManager
from .modules.base import ModuleContainer, EventBus, ModuleEvent, BaseModule
from .modules.discovery import DiscoveryModule
from .modules.dns_analysis import DNSAnalysisModule
from .modules.web_fuzzing import WebFuzzingModule
from .modules.web_probing import WebProbingModule
from .modules.vulnerability_scan import VulnerabilityScanModule
import logging
from .utils.tool_checker import ToolChecker

class ModuleDependencyError(Exception):
    """Raised when module dependencies cannot be resolved"""
    pass

class Framework:
    """Main framework class that orchestrates all modules"""
    
    def __init__(self, args):
        self.args = args
        self.target = args.domain
        self.config = ConfigManager()
        self.logger = logging.getLogger(__name__)
        
        # Create domain-specific output directory
        self.output_dir = Path(args.output or self.config.output.directory) / self.target
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create standard subdirectories
        for subdir in ['raw', 'processed', 'temp', 'logs']:
            (self.output_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.session_manager = SessionManager(self.output_dir)
        self.tool_checker = ToolChecker(self.logger)
        self.event_bus = EventBus()
        self.performance_monitor = PerformanceMonitor(self.output_dir)
        
        # Initialize state
        self.running = False
        self.start_time = None
        self.modules = {}
        self.module_graph = nx.DiGraph()
        self.module_states = {}
        
        # Register signal handlers
        self._register_signal_handlers()

    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle signals for graceful shutdown"""
        self.logger.info("\nReceived shutdown signal, cleaning up...")
        asyncio.create_task(self.cleanup())
        sys.exit(0)

    def _build_module_graph(self) -> None:
        """Build module dependency graph"""
        # Add nodes for each module
        for name, module in self.modules.items():
            self.module_graph.add_node(name)
            
        # Add edges for dependencies
        for name, module in self.modules.items():
            for dep in module.get_dependencies():
                if isinstance(dep, str):
                    self.module_graph.add_edge(dep, name)
        
        # Verify no cycles
        try:
            nx.find_cycle(self.module_graph)
            raise ModuleDependencyError("Circular dependencies detected in modules")
        except nx.NetworkXNoCycle:
            pass

    def _get_module_order(self) -> List[str]:
        """Get module execution order based on dependencies"""
        try:
            return list(nx.topological_sort(self.module_graph))
        except nx.NetworkXUnfeasible:
            raise ModuleDependencyError("Could not resolve module dependencies")

    async def verify_tools(self) -> bool:
        """Verify all required tools before starting"""
        self.logger.info("\nVerifying required tools...")
        results = {}
        has_issues = False
        
        # Get all required tools from modules
        required_tools = {}
        for module in self.modules.values():
            required_tools.update(module.get_required_tools())
        
        # Check each tool
        for tool, min_version in required_tools.items():
            self.logger.info(f"\nChecking {tool}...")
            
            # Check if tool exists
            exists = await self.tool_checker.check_tool(tool)
            if not exists:
                self.logger.error(f"❌ {tool} not found")
                results[tool] = {
                    'installed': False,
                    'version': None,
                    'min_version': min_version,
                    'status': 'missing'
                }
                has_issues = True
                continue
            
            # Get tool version
            current_version = await self.tool_checker.get_tool_version(tool)
            if current_version:
                self.logger.info(f"Found {tool} version {current_version}")
                
                # Compare versions if minimum version is specified
                if min_version:
                    is_outdated = not self.tool_checker._compare_versions(current_version, min_version)
                    if is_outdated:
                        self.logger.warning(f"⚠️  {tool} is outdated (Current: {current_version}, Required: {min_version})")
                        has_issues = True
                        results[tool] = {
                            'installed': True,
                            'version': current_version,
                            'min_version': min_version,
                            'status': 'outdated'
                        }
                        continue
                
                results[tool] = {
                    'installed': True,
                    'version': current_version,
                    'min_version': min_version,
                    'status': 'ok'
                }
            else:
                self.logger.warning(f"⚠️  Could not determine {tool} version")
                results[tool] = {
                    'installed': True,
                    'version': None,
                    'min_version': min_version,
                    'status': 'unknown'
                }
                has_issues = True
        
        if has_issues:
            self.logger.warning("\nTool verification found issues.")
            response = input("\nDo you want to (1) Continue with current versions (2) Update tools (3) Exit? [1/2/3]: ")
            
            if response == "2":
                self.logger.info("\nUpdating tools...")
                await self._update_tools(results)
                # Verify again after update
                return await self.verify_tools()
            elif response == "3":
                self.logger.info("\nExiting framework. Please update the tools and try again.")
                return False
            else:
                self.logger.info("\nContinuing with available tools...")
        else:
            self.logger.info("\n✅ All tools are installed and up to date!")
        
        return True

    async def _update_tools(self, tool_status: Dict[str, Dict[str, Any]]) -> None:
        """Update outdated or missing tools"""
        for tool, status in tool_status.items():
            if status['status'] in ['missing', 'outdated']:
                if tool in self.tool_checker.install_commands:
                    self.logger.info(f"\nUpdating {tool}...")
                    cmd = self.tool_checker.install_commands[tool]
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        self.logger.info(f"Successfully updated {tool}")
                    else:
                        self.logger.error(f"Failed to update {tool}: {stderr.decode()}")

    def _initialize_modules(self) -> None:
        """Initialize modules with dependency checking"""
        try:
            self.modules = {
                "discovery": DiscoveryModule(self),
                "dns_analysis": DNSAnalysisModule(self),
                "web_probing": WebProbingModule(self),
                "web_fuzzing": WebFuzzingModule(self),
                "vulnerability_scan": VulnerabilityScanModule(self)
            }
            
            # Build dependency graph
            self._build_module_graph()
            
            # Initialize module states
            for name in self.modules:
                self.module_states[name] = {
                    'status': 'pending',
                    'start_time': None,
                    'end_time': None,
                    'error': None
                }
            
            for module_name, module in self.modules.items():
                self.logger.debug(f"Initialized {module_name} module")
                
        except Exception as e:
            self.logger.error(f"Error initializing modules: {str(e)}")
            raise

    async def start(self) -> None:
        """Start the framework with improved flow control"""
        try:
            # Verify tools first
            if not await self.verify_tools():
                return
            
            self.logger.info(f"\nStarting LLEO framework scan for {self.target}")
            self.logger.info(f"Output directory: {self.output_dir}")
            self.running = True
            self.start_time = datetime.now()
            
            # Initialize modules
            self._initialize_modules()
            
            # Get module execution order
            module_order = self._get_module_order()
            total_modules = len(module_order)
            
            # Start performance monitoring
            await self.performance_monitor.start_monitoring()
            
            # Run modules in dependency order
            with tqdm(total=total_modules, desc="Overall Progress") as pbar:
                for i, name in enumerate(module_order, 1):
                    module = self.modules[name]
                    self.logger.info(f"\n{'='*50}")
                    self.logger.info(f"Starting {name} module ({i}/{total_modules})...")
                    
                    try:
                        # Update module state
                        self.module_states[name]['status'] = 'running'
                        self.module_states[name]['start_time'] = datetime.now()
                        
                        # Run module setup and verify tools
                        await module.setup()
                        
                        # Start module performance monitoring
                        await self.performance_monitor.start_monitoring_module(name)
                        
                        # Run the module
                        results = await module.run()
                        if results:
                            await self.session_manager.save_results(name, results)
                            
                            # Update module state
                            self.module_states[name]['status'] = 'completed'
                            self.module_states[name]['end_time'] = datetime.now()
                            
                            # Print module performance summary
                            self.performance_monitor.print_module_summary(name)
                            
                            # Ask user to continue to next module
                            if i < total_modules:
                                response = input(f"\n{name} module completed. Continue to next module? (y/n): ").lower()
                                if response != 'y':
                                    self.logger.info("Exiting framework as per user request")
                                    break
                        
                    except Exception as e:
                        self.logger.error(f"Error in {name} module: {str(e)}")
                        self.module_states[name]['status'] = 'error'
                        self.module_states[name]['error'] = str(e)
                        
                        # Ask user whether to continue despite the error
                        response = input(f"\nError in {name} module. Continue to next module? (y/n): ").lower()
                        if response != 'y':
                            break
                    finally:
                        # Stop module performance monitoring
                        await self.performance_monitor.stop_monitoring_module(name)
                        pbar.update(1)
            
            # Save final metrics
            await self.performance_monitor.save_metrics(self.output_dir)
            await self.session_manager.save_session()
            
            # Print final summaries
            self._print_final_summary()
            self.performance_monitor.print_overall_summary()
            
        except Exception as e:
            self.logger.error(f"Critical error in framework: {str(e)}")
        finally:
            self.logger.info("Cleaning up...")
            await self.cleanup()

    def _print_module_summary(self, module_name: str) -> None:
        """Print summary for a module"""
        state = self.module_states[module_name]
        status = state['status']
        duration = None
        
        if state['start_time'] and state['end_time']:
            duration = (state['end_time'] - state['start_time']).total_seconds()
        
        self.logger.info(f"\nModule Summary: {module_name}")
        self.logger.info(f"Status: {status}")
        if duration:
            self.logger.info(f"Duration: {duration:.2f}s")
        if state['error']:
            self.logger.info(f"Error: {state['error']}")

    def _print_final_summary(self) -> None:
        """Print final framework execution summary"""
        duration = datetime.now() - self.start_time
        self.logger.info("\nFramework Execution Summary:")
        self.logger.info(f"Target Domain: {self.target}")
        self.logger.info(f"Start Time: {self.start_time.isoformat()}")
        self.logger.info(f"End Time: {datetime.now().isoformat()}")
        self.logger.info(f"Total Duration: {duration.total_seconds():.2f}s")
        
        self.logger.info("\nModule Status:")
        for name, state in self.module_states.items():
            status = state['status']
            duration = None
            if state['start_time'] and state['end_time']:
                duration = (state['end_time'] - state['start_time']).total_seconds()
            
            status_str = f"{status.upper()}"
            if duration:
                status_str += f" ({duration:.2f}s)"
            if state['error']:
                status_str += f" - {state['error']}"
            
            self.logger.info(f"{name}: {status_str}")
        
        self.logger.info(f"\nResults saved in: {self.output_dir}")

    async def cleanup(self) -> None:
        """Cleanup framework resources"""
        self.logger.info("Cleaning up...")
        try:
            # Stop performance monitoring
            await self.performance_monitor.stop_monitoring()
            
            # Clean up modules
            for module in self.modules.values():
                try:
                    await module.cleanup()
                except Exception as e:
                    self.logger.error(f"Error during cleanup: {str(e)}")
            
            # Save session data
            try:
                await self.session_manager.save_session()
            except Exception as e:
                self.logger.error(f"Error saving session: {e}")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        finally:
            self.running = False
    
    async def get_module_results(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Get results from a specific module"""
        try:
            return self.session_manager.get_results(module_name)
        except Exception as e:
            self.logger.error(f"Error getting results for {module_name}: {e}")
            return None
    
    async def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Get results from all modules"""
        results = {}
        for name in self.modules:
            try:
                results[name] = await self.get_module_results(name)
            except Exception as e:
                self.logger.error(f"Error getting results for {name}: {e}")
                results[name] = None
        return results
    
    def print_summary(self):
        """Print framework execution summary"""
        duration = datetime.now() - self.start_time
        self.logger.info("\nScan Summary:")
        self.logger.info(f"Target Domain: {self.target}")
        self.logger.info(f"Output Directory: {self.output_dir}")
        self.logger.info(f"Start Time: {self.start_time.isoformat()}")
        self.logger.info(f"End Time: {datetime.now().isoformat()}")
        self.logger.info(f"Duration: {duration.total_seconds():.2f}s\n")
        
        self.logger.info("Module Status:")
        for module_name, module in self.modules.items():
            results = self.session_manager.get_results(module_name)
            if results:
                if 'error' in results:
                    status = f"Failed: {results['error']}"
                else:
                    status = "Completed"
            else:
                status = "Not run"
            self.logger.info(f"{module_name}: {status}")
        
        self.logger.info("\nResults Location:")
        self.logger.info(f"Raw data: {self.output_dir / 'raw'}")
        self.logger.info(f"Processed results: {self.output_dir / 'processed'}")
        self.logger.info(f"Logs: {self.output_dir / 'logs'}")

    def _validate_args(self) -> None:
        """Enhanced argument validation"""
        if not self.target:
            raise ValueError("Target domain is required")
        
        if not self._is_valid_domain(self.target):
            raise ValueError(f"Invalid domain: {self.target}")
        
        if hasattr(self.args, 'output_dir'):
            output_path = Path(self.args.output_dir)
            if not output_path.parent.exists():
                raise ValueError(f"Parent directory for output does not exist: {output_path.parent}")

    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain name format"""
        import re
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        return bool(re.match(pattern, domain))

# Analysis:
# - The Framework class initializes the logging, output directories, and session management.
# - Modules are loaded and executed sequentially with error checking.
# - User prompts are used to decide whether to continue on errors or after a module completes successfully.
# - Concludes by saving session information and printing a summary report.
