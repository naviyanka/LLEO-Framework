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
        
        # Get live hosts from web probing phase or use target domain
        targets = self._get_live_hosts()
        
        for target in targets:
            results[target] = {}
            for tool_name, tool_func in self.tools.items():
                try:
                    self.logger.info(f"Running {tool_name} on {target}...")
                    results[target][tool_name] = tool_func(target)
                except Exception as e:
                    self.logger.error(f"Error running {tool_name} on {target}: {str(e)}")
                    results[target][tool_name] = {'error': str(e)}
        
        self._save_results(results)
        return results

    def _run_dirsearch(self, target):
        """Run dirsearch tool"""
        try:
            if not self._check_tool_exists('dirsearch'):
                raise Exception("dirsearch not found. Please install it first.")
            
            output_file = os.path.join(self.framework.output_dir, f'dirsearch_{target.replace("://", "_")}.json')
            
            cmd = [
                'dirsearch',
                '-u', target,
                '--format=json',
                '-o', output_file,
                '--random-agent',
                '--exclude-status=404'
            ]
            
            subprocess.run(cmd, check=True)
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    return json.load(f)
            return {'directories': []}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Dirsearch error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in dirsearch: {str(e)}")
            return {'error': str(e)}

    def _run_gobuster(self, target):
        """Run gobuster tool"""
        try:
            if not self._check_tool_exists('gobuster'):
                raise Exception("gobuster not found. Please install it first.")
            
            output_file = os.path.join(self.framework.output_dir, f'gobuster_{target.replace("://", "_")}.json')
            wordlist = '/usr/share/wordlists/dirb/common.txt'  # Default wordlist
            
            cmd = [
                'gobuster', 'dir',
                '-u', target,
                '-w', wordlist,
                '-o', output_file,
                '-q',  # Quiet mode
                '--no-error'
            ]
            
            subprocess.run(cmd, check=True)
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    return {'directories': [line.strip() for line in f if line.strip()]}
            return {'directories': []}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Gobuster error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in gobuster: {str(e)}")
            return {'error': str(e)}

    def _run_ffuf(self, target):
        """Run ffuf tool"""
        try:
            if not self._check_tool_exists('ffuf'):
                raise Exception("ffuf not found. Please install it first.")
            
            output_file = os.path.join(self.framework.output_dir, f'ffuf_{target.replace("://", "_")}.json')
            wordlist = '/usr/share/wordlists/dirb/common.txt'  # Default wordlist
            
            cmd = [
                'ffuf',
                '-u', f'{target}/FUZZ',
                '-w', wordlist,
                '-o', output_file,
                '-of', 'json'
            ]
            
            subprocess.run(cmd, check=True)
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    return json.load(f)
            return {'directories': []}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFUF error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in ffuf: {str(e)}")
            return {'error': str(e)}

    def _run_wfuzz(self, target):
        """Run wfuzz tool"""
        try:
            if not self._check_tool_exists('wfuzz'):
                raise Exception("wfuzz not found. Please install it first.")
            
            output_file = os.path.join(self.framework.output_dir, f'wfuzz_{target.replace("://", "_")}.json')
            wordlist = '/usr/share/wordlists/dirb/common.txt'  # Default wordlist
            
            cmd = [
                'wfuzz',
                '-f', output_file,
                '-o', 'json',
                '-w', wordlist,
                '--hc', '404',
                f'{target}/FUZZ'
            ]
            
            subprocess.run(cmd, check=True)
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    return json.load(f)
            return {'directories': []}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Wfuzz error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in wfuzz: {str(e)}")
            return {'error': str(e)}

    def _run_katana(self, target):
        """Run katana tool"""
        try:
            if not self._check_tool_exists('katana'):
                raise Exception("katana not found. Please install it first.")
            
            output_file = os.path.join(self.framework.output_dir, f'katana_{target.replace("://", "_")}.json')
            
            cmd = [
                'katana',
                '-u', target,
                '-jc',  # JSON output
                '-o', output_file,
                '-silent'
            ]
            
            subprocess.run(cmd, check=True)
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    return json.load(f)
            return {'endpoints': []}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Katana error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in katana: {str(e)}")
            return {'error': str(e)}

    def _get_live_hosts(self):
        """Get live hosts from web probing results"""
        probing_file = os.path.join(self.framework.output_dir, 'web_probing_results.json')
        if os.path.exists(probing_file):
            try:
                with open(probing_file) as f:
                    data = json.load(f)
                    hosts = []
                    for tool_results in data.values():
                        if isinstance(tool_results, dict) and 'live_hosts' in tool_results:
                            hosts.extend(tool_results['live_hosts'])
                    return list(set(hosts))
            except Exception as e:
                self.logger.error(f"Error reading web probing results: {str(e)}")
        return [f"http://{self.framework.args.domain}"]  # Return http URL of target domain if no probing results

    def _check_tool_exists(self, tool_name):
        """Check if a tool is installed"""
        try:
            subprocess.run(['which', tool_name], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _save_results(self, results):
        """Save web fuzzing results"""
        output_file = os.path.join(self.framework.output_dir, 'web_fuzzing_results.json')
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4) 