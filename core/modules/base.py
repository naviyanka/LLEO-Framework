from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
import os
import json
import subprocess
from core.utils.rate_limiter import RateLimiter

class BaseModule(ABC):
    def __init__(self, framework):
        self.framework = framework
        self.logger = framework.logger
        self.config = framework.config
        self.output_dir = framework.output_dir
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            calls_per_second=self.config.get('tools', {}).get('rate_limit', 10)
        )
        
        self.args = framework.args
        self.results = {}
    
    @abstractmethod
    def run(self):
        """Main module execution method"""
        raise NotImplementedError("Module must implement run method")
    
    def run_parallel(self, func, items, max_workers=None):
        """Run tasks in parallel"""
        if max_workers is None:
            max_workers = self.config.get('tools', {}).get('threads', 10)
            
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(func, item) for item in items]
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error in parallel execution: {str(e)}")
        
        return results 

    def _check_tool_exists(self, tool_name):
        """Check if a tool is installed and executable"""
        try:
            # Check common tool locations
            paths = [
                f"/usr/local/bin/{tool_name}",
                f"/usr/bin/{tool_name}",
                f"/opt/lleo-tools/{tool_name}",
                f"{os.path.expanduser('~/go/bin/')}{tool_name}"
            ]
            
            for path in paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    return True
            
            # Try which command as fallback
            subprocess.run(['which', tool_name], 
                         check=True, 
                         capture_output=True)
            return True
            
        except subprocess.CalledProcessError:
            self.logger.warning(f"Tool not found: {tool_name}")
            self.logger.info(f"Run 'sudo ./install.sh' to install missing tools")
            return False
        except Exception as e:
            self.logger.error(f"Error checking tool {tool_name}: {str(e)}")
            return False

    def _save_results(self, results, module_name=None):
        """Save module results to file"""
        if module_name is None:
            module_name = self.__class__.__name__.lower()
        
        output_file = os.path.join(
            self.output_dir, 
            f'{module_name}_results.json'
        )
        
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}") 