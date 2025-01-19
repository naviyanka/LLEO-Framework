import subprocess
import json
import os
import nmap
from .base import BaseModule

class WebProbingModule(BaseModule):
    def __init__(self, framework):
        super().__init__(framework)
        self.tools = {
            'httpx': self._run_httpx,
            'aquatone': self._run_aquatone,
            'nmap': self._run_nmap,
            'naabu': self._run_naabu,
            '403-bypass': self._run_403_bypass
        }

    def run(self):
        """Execute web probing tools"""
        self.logger.info("Starting web probing phase...")
        results = {}
        
        # Get targets from previous phases
        targets = self._get_targets()
        
        for tool_name, tool_func in self.tools.items():
            try:
                self.logger.info(f"Running {tool_name}...")
                results[tool_name] = tool_func(targets)
            except Exception as e:
                self.logger.error(f"Error running {tool_name}: {str(e)}")
                results[tool_name] = {'error': str(e)}
        
        self._save_results(results)
        return results

    def _run_httpx(self, targets):
        """Run httpx tool"""
        try:
            input_file = os.path.join(self.framework.output_dir, 'probe_targets.txt')
            output_file = os.path.join(self.framework.output_dir, 'httpx_results.json')
            
            with open(input_file, 'w') as f:
                f.write('\n'.join(targets))
            
            cmd = [
                'httpx',
                '-l', input_file,
                '-json',
                '-tech-detect',
                '-title',
                '-status-code',
                '-follow-redirects',
                '-o', output_file
            ]
            
            subprocess.run(cmd, check=True)
            
            with open(output_file) as f:
                return [json.loads(line) for line in f if line.strip()]
        except subprocess.CalledProcessError as e:
            raise Exception(f"httpx error: {e.stderr}")

    def _run_nmap(self, targets):
        """Run nmap scan"""
        try:
            nm = nmap.PortScanner()
            results = {}
            
            for target in targets:
                self.logger.info(f"Scanning {target} with nmap...")
                scan_result = nm.scan(
                    target,
                    arguments='-sV -sC -p- --min-rate=1000'
                )
                results[target] = scan_result
            
            return results
        except Exception as e:
            raise Exception(f"Nmap error: {str(e)}")

    def _run_naabu(self, targets):
        """Run naabu port scanner"""
        try:
            input_file = os.path.join(self.framework.output_dir, 'naabu_targets.txt')
            output_file = os.path.join(self.framework.output_dir, 'naabu_results.json')
            
            with open(input_file, 'w') as f:
                f.write('\n'.join(targets))
            
            cmd = [
                'naabu',
                '-l', input_file,
                '-json',
                '-o', output_file
            ]
            
            subprocess.run(cmd, check=True)
            
            with open(output_file) as f:
                return [json.loads(line) for line in f if line.strip()]
        except subprocess.CalledProcessError as e:
            raise Exception(f"Naabu error: {e.stderr}")

    # ... Other tool implementations ... 