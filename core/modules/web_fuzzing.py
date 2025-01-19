import subprocess
import json
import os
from .base import BaseModule

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

    def run(self):
        """Execute web fuzzing tools"""
        self.logger.info("Starting web fuzzing...")
        results = {}
        
        # Get live hosts from web probing phase
        live_hosts = self._get_live_hosts()
        
        for host in live_hosts:
            host_results = {}
            for tool_name, tool_func in self.tools.items():
                try:
                    host_results[tool_name] = tool_func(host)
                except Exception as e:
                    self.logger.error(f"Error running {tool_name} on {host}: {str(e)}")
                    host_results[tool_name] = {'error': str(e)}
            results[host] = host_results
        
        self._save_results(results)
        return results

    def _run_ffuf(self, target):
        """Run ffuf tool"""
        try:
            wordlist = '/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt'
            output_file = os.path.join(self.framework.output_dir, f'ffuf_{target.replace("://", "_")}.json')
            
            cmd = [
                'ffuf', '-u', f'{target}/FUZZ',
                '-w', wordlist,
                '-o', output_file,
                '-of', 'json'
            ]
            subprocess.run(cmd, check=True)
            
            with open(output_file) as f:
                return json.load(f)
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFUF error: {str(e)}")

    # ... Implementations for other fuzzing tools ... 