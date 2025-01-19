from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

class BaseModule(ABC):
    def __init__(self, framework):
        self.framework = framework
        self.logger = framework.logger
        self.config = framework.config
        self.args = framework.args
        self.results = {}
    
    @abstractmethod
    def run(self):
        """Main module execution method"""
        raise NotImplementedError("Module must implement run method")
    
    def run_parallel(self, func, items, max_workers=None):
        """Run tasks in parallel"""
        if max_workers is None:
            max_workers = self.config['tools']['threads']
            
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