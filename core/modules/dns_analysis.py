import subprocess
import json
import os
from .base import BaseModule

class DNSAnalysisModule(BaseModule):
    def __init__(self, framework):
        super().__init__(framework)
        self.tools = {
            'dnsx': self._run_dnsx,
            'altdns': self._run_altdns,
            'dnsgen': self._run_dnsgen
        }

    def run(self):
        """Execute DNS analysis tools"""
        self.logger.info("Starting DNS analysis...")
        results = {}
        
        # Get subdomains from discovery phase
        subdomains = self._get_subdomains()
        
        for tool_name, tool_func in self.tools.items():
            try:
                results[tool_name] = tool_func(subdomains)
            except Exception as e:
                self.logger.error(f"Error running {tool_name}: {str(e)}")
                results[tool_name] = {'error': str(e)}
        
        self._save_results(results)
        return results

    def _get_subdomains(self):
        """Get subdomains from discovery results"""
        discovery_file = os.path.join(self.framework.output_dir, 'discovery_results.json')
        if os.path.exists(discovery_file):
            with open(discovery_file) as f:
                data = json.load(f)
                subdomains = []
                for tool_results in data.values():
                    if 'subdomains' in tool_results:
                        subdomains.extend(tool_results['subdomains'])
                return list(set(subdomains))
        return []

    def _run_dnsx(self, subdomains):
        """Run dnsx tool"""
        try:
            input_file = os.path.join(self.framework.output_dir, 'subdomains.txt')
            with open(input_file, 'w') as f:
                f.write('\n'.join(subdomains))
            
            cmd = ['dnsx', '-l', input_file, '-json', '-a', '-aaaa', '-cname', '-mx', '-ns']
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {'dns_records': [json.loads(line) for line in process.stdout.splitlines() if line]}
        except subprocess.CalledProcessError as e:
            raise Exception(f"DNSx error: {e.stderr}")

    # ... Implementations for other DNS tools ... 