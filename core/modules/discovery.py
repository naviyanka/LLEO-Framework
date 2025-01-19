import subprocess
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import BaseModule

class DiscoveryModule(BaseModule):
    def __init__(self, framework):
        super().__init__(framework)
        self.tools = {
            'subfinder': self._run_subfinder,
            'amass': self._run_amass,
            'assetfinder': self._run_assetfinder,
            'findomain': self._run_findomain,
            'waybackurls': self._run_waybackurls,
            'gauplus': self._run_gauplus,
            'gospider': self._run_gospider,
            'haktrails': self._run_haktrails,
            'whatweb': self._run_whatweb,
            'spiderfoot': self._run_spiderfoot,
            'wafwoof': self._run_wafwoof
        }

    def run(self):
        """Execute all discovery tools"""
        self.logger.info("Starting discovery phase...")
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.config['tools']['threads']) as executor:
            future_to_tool = {executor.submit(func, self.framework.args.domain): name 
                            for name, func in self.tools.items()}
            
            for future in as_completed(future_to_tool):
                tool_name = future_to_tool[future]
                try:
                    results[tool_name] = future.result()
                except Exception as e:
                    self.logger.error(f"Error running {tool_name}: {str(e)}")
                    results[tool_name] = {'error': str(e)}
        
        self._save_results(results)
        return results

    def _save_results(self, results):
        """Save discovery results to file"""
        output_file = os.path.join(self.framework.output_dir, 'discovery_results.json')
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)

    def _run_subfinder(self, domain):
        """Run subfinder tool"""
        try:
            cmd = ['subfinder', '-d', domain, '-silent', '-json']
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {'subdomains': [line for line in process.stdout.split('\n') if line]}
        except subprocess.CalledProcessError as e:
            raise Exception(f"Subfinder error: {e.stderr}")

    def _run_amass(self, domain):
        """Run amass tool"""
        try:
            output_file = os.path.join(self.framework.output_dir, 'amass_output.txt')
            cmd = ['amass', 'enum', '-d', domain, '-o', output_file]
            subprocess.run(cmd, check=True)
            
            with open(output_file) as f:
                subdomains = f.read().splitlines()
            return {'subdomains': subdomains}
        except subprocess.CalledProcessError as e:
            raise Exception(f"Amass error: {str(e)}")

    # ... Similar implementations for other tools ... 