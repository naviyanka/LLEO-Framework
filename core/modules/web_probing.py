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

    def _run_aquatone(self, targets):
        """Run aquatone tool"""
        try:
            if not self._check_tool_exists('aquatone'):
                raise Exception("aquatone not found. Please install it first.")
            
            input_file = os.path.join(self.framework.output_dir, 'aquatone_targets.txt')
            output_dir = os.path.join(self.framework.output_dir, 'aquatone')
            
            # Write targets to input file
            with open(input_file, 'w') as f:
                f.write('\n'.join(targets))
            
            cmd = [
                'aquatone',
                '-out', output_dir,
                '-silent',
                '-scan-timeout', '3000',
                '-screenshot-timeout', '3000',
                '-ports', 'small',
                '-input', input_file
            ]
            
            subprocess.run(cmd, check=True)
            
            # Process results
            results = {
                'screenshots': [],
                'html_report': None
            }
            
            # Check for screenshots
            screenshots_dir = os.path.join(output_dir, 'screenshots')
            if os.path.exists(screenshots_dir):
                results['screenshots'] = [
                    os.path.join('screenshots', f) 
                    for f in os.listdir(screenshots_dir) 
                    if f.endswith('.png')
                ]
            
            # Check for HTML report
            html_report = os.path.join(output_dir, 'aquatone_report.html')
            if os.path.exists(html_report):
                results['html_report'] = 'aquatone_report.html'
            
            return results
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Aquatone error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in aquatone: {str(e)}")
            return {'error': str(e)}

    def _run_403_bypass(self, targets):
        """Run 403 bypass tool"""
        try:
            if not self._check_tool_exists('403-bypass'):
                raise Exception("403-bypass not found. Please install it first.")
            
            results = {}
            for target in targets:
                output_file = os.path.join(
                    self.framework.output_dir, 
                    f'403bypass_{target.replace("://", "_")}.txt'
                )
                
                cmd = [
                    '403-bypass',
                    '-u', target,
                    '-o', output_file,
                    '--skip-default-ports'
                ]
                
                subprocess.run(cmd, check=True)
                
                if os.path.exists(output_file):
                    with open(output_file) as f:
                        results[target] = [line.strip() for line in f if line.strip()]
                else:
                    results[target] = []
            
            return results
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"403-bypass error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in 403-bypass: {str(e)}")
            return {'error': str(e)}

    def _get_targets(self):
        """Get targets from previous phases"""
        discovery_file = os.path.join(self.framework.output_dir, 'discovery_results.json')
        targets = []
        
        if os.path.exists(discovery_file):
            try:
                with open(discovery_file) as f:
                    data = json.load(f)
                    for tool_results in data.values():
                        if isinstance(tool_results, dict):
                            if 'subdomains' in tool_results:
                                targets.extend(tool_results['subdomains'])
            except Exception as e:
                self.logger.error(f"Error reading discovery results: {str(e)}")
        
        if not targets:
            targets = [self.framework.args.domain]
        
        # Add http/https if not present
        formatted_targets = []
        for target in targets:
            if not target.startswith(('http://', 'https://')):
                formatted_targets.extend([f'http://{target}', f'https://{target}'])
            else:
                formatted_targets.append(target)
        
        return list(set(formatted_targets)) 