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

    def _run_assetfinder(self, domain):
        """Run assetfinder tool"""
        try:
            if not self._check_tool_exists('assetfinder'):
                raise Exception("assetfinder not found. Please install it first.")
            
            cmd = ['assetfinder', '--subs-only', domain]
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not process.stdout.strip():
                self.logger.warning("assetfinder returned no results")
                return {'subdomains': []}
                
            subdomains = [line.strip() for line in process.stdout.splitlines() if line.strip()]
            return {'subdomains': subdomains}
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Assetfinder error: {e.stderr}")
            return {'error': str(e.stderr)}
        except Exception as e:
            self.logger.error(f"Unexpected error in assetfinder: {str(e)}")
            return {'error': str(e)}

    def _run_findomain(self, domain):
        """Run findomain tool"""
        try:
            if not self._check_tool_exists('findomain'):
                self.logger.warning("findomain not found. Skipping...")
                return {'subdomains': []}
            
            output_file = os.path.join(self.framework.output_dir, f'findomain_{domain}.txt')
            
            # Use direct command without shell=True
            cmd = [
                'findomain',
                '--target', domain,
                '--quiet',
                '--output', output_file
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Findomain execution failed: {e.stderr}")
                return {'subdomains': []}
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    subdomains = [line.strip() for line in f if line.strip()]
                return {'subdomains': subdomains}
            return {'subdomains': []}
        except Exception as e:
            self.logger.error(f"Error in findomain: {str(e)}")
            return {'subdomains': []}

    def _run_waybackurls(self, domain):
        """Run waybackurls tool"""
        try:
            if not self._check_tool_exists('waybackurls'):
                self.logger.warning("waybackurls not found. Skipping...")
                return {'urls': []}
            
            cmd = ['waybackurls', domain]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.stdout:
                urls = [url.strip() for url in process.stdout.splitlines() if url.strip()]
                return {'urls': urls}
            return {'urls': []}
        except Exception as e:
            self.logger.error(f"Error in waybackurls: {str(e)}")
            return {'urls': []}

    def _run_gauplus(self, domain):
        """Run gauplus tool"""
        try:
            if not self._check_tool_exists('gau'):
                self.logger.warning("gau not found. Skipping...")
                return {'urls': []}
            
            # Create config directory if it doesn't exist
            gau_config_dir = os.path.expanduser('~/.config/gau')
            os.makedirs(gau_config_dir, exist_ok=True)
            
            cmd = ['gau', '--threads', '10', domain]
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.stdout:
                urls = [url.strip() for url in process.stdout.splitlines() if url.strip()]
                return {'urls': urls}
            return {'urls': []}
        except Exception as e:
            self.logger.error(f"Error in gauplus: {str(e)}")
            return {'urls': []}

    def _run_gospider(self, domain):
        """Run gospider tool"""
        try:
            if not self._check_tool_exists('gospider'):
                raise Exception("gospider not found. Please install it first.")
            
            # Add protocol if not present
            if not domain.startswith(('http://', 'https://')):
                target = f'http://{domain}'
            else:
                target = domain
            
            cmd = [
                'gospider',
                '-s', target,
                '-d', '3',  # Depth
                '-t', '50',  # Threads
                '-c', '10',  # Concurrent requests
                '--other-source',  # Include other sources
                '--include-subs',  # Include subdomains
                '--include-other-source'  # Include other source results
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            urls = []
            if process.stdout:
                for line in process.stdout.splitlines():
                    if line.startswith('[') and ']' in line:
                        url = line.split(']')[1].strip()
                        if url:
                            urls.append(url)
            
            return {'urls': list(set(urls))}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Gospider error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'urls': []}
        except Exception as e:
            self.logger.error(f"Error in gospider: {str(e)}")
            return {'urls': []}

    def _run_haktrails(self, domain):
        """Run haktrails tool"""
        try:
            if not self._check_tool_exists('haktrails'):
                raise Exception("haktrails not found. Please install it first.")
            
            # Skip if no API key instead of error
            if 'securitytrails' not in self.config.get('api_keys', {}) or not self.config['api_keys'].get('securitytrails'):
                self.logger.warning("Skipping haktrails: SecurityTrails API key not configured")
                return {'subdomains': []}
            
            cmd = [
                'haktrails', 'subdomains',
                '-d', domain,
                '-k', self.config['api_keys']['securitytrails']
            ]
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not process.stdout.strip():
                return {'subdomains': []}
                
            subdomains = [line.strip() for line in process.stdout.splitlines() if line.strip()]
            return {'subdomains': subdomains}
        except Exception as e:
            self.logger.error(f"Error in haktrails: {str(e)}")
            return {'subdomains': []}

    def _run_whatweb(self, domain):
        """Run whatweb tool"""
        try:
            if not self._check_tool_exists('whatweb'):
                raise Exception("whatweb not found. Please install it first.")
            
            # Add protocol if not present
            if not domain.startswith(('http://', 'https://')):
                target = f'http://{domain}'
            else:
                target = domain
            
            cmd = [
                'whatweb',
                '--color=never',
                '--log-brief=-',  # Output to stdout in brief format
                target
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not process.stdout.strip():
                return {'technologies': []}
            
            # Parse the brief output format
            technologies = []
            output_lines = process.stdout.splitlines()
            for line in output_lines:
                if '[' in line and ']' in line:
                    techs = line.split('[')[1:]
                    for tech in techs:
                        tech_name = tech.split(']')[0].strip()
                        if tech_name:
                            technologies.append(tech_name)
            
            return {'technologies': list(set(technologies))}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Whatweb error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'technologies': []}
        except Exception as e:
            self.logger.error(f"Error in whatweb: {str(e)}")
            return {'technologies': []}

    def _run_spiderfoot(self, domain):
        """Run spiderfoot tool"""
        try:
            if not self._check_tool_exists('sf'):
                self.logger.warning("spiderfoot not found. Skipping...")
                return {'results': []}
            
            # Skip if not properly configured
            return {'results': [], 'status': 'skipped'}
        except Exception as e:
            self.logger.error(f"Error in spiderfoot: {str(e)}")
            return {'results': []}

    def _process_spiderfoot_results(self, data):
        """Process spiderfoot results"""
        processed = {
            'subdomains': [],
            'emails': [],
            'ips': []
        }
        
        for item in data.get('results', []):
            if 'SUBDOMAIN' in item.get('type', ''):
                processed['subdomains'].append(item.get('data', ''))
            elif 'EMAIL' in item.get('type', ''):
                processed['emails'].append(item.get('data', ''))
            elif 'IP_ADDRESS' in item.get('type', ''):
                processed['ips'].append(item.get('data', ''))
        
        return processed

    def _run_wafwoof(self, domain):
        """Run wafw00f tool"""
        try:
            if not self._check_tool_exists('wafw00f'):
                raise Exception("wafw00f not found. Please install it first.")
            
            # Add protocol if not present
            if not domain.startswith(('http://', 'https://')):
                target = f'http://{domain}'
            else:
                target = domain
            
            cmd = ['wafw00f', target]
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not process.stdout.strip():
                return {'waf': None}
                
            # Parse the output manually since JSON is not supported
            output_lines = process.stdout.splitlines()
            waf_results = {
                'detected': False,
                'firewall': None,
                'manufacturer': None
            }
            
            for line in output_lines:
                if 'is behind' in line.lower():
                    waf_results['detected'] = True
                    waf_info = line.split('is behind')[-1].strip()
                    waf_results['firewall'] = waf_info
            
            return {'waf': waf_results}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Wafw00f error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'waf': None}
        except Exception as e:
            self.logger.error(f"Error in wafw00f: {str(e)}")
            return {'waf': None}

    def _merge_results(self, results):
        """Merge results from all tools"""
        merged = {
            'subdomains': set(),
            'urls': set(),
            'technologies': [],
            'emails': set(),
            'ips': set(),
            'waf': None
        }
        
        for tool_results in results.values():
            if isinstance(tool_results, dict):
                if 'subdomains' in tool_results:
                    merged['subdomains'].update(tool_results['subdomains'])
                if 'urls' in tool_results:
                    merged['urls'].update(tool_results['urls'])
                if 'technologies' in tool_results:
                    merged['technologies'].extend(tool_results['technologies'])
                if 'emails' in tool_results:
                    merged['emails'].update(tool_results['emails'])
                if 'ips' in tool_results:
                    merged['ips'].update(tool_results['ips'])
                if 'waf' in tool_results and tool_results['waf']:
                    merged['waf'] = tool_results['waf']
        
        # Convert sets to lists for JSON serialization
        return {
            'subdomains': list(merged['subdomains']),
            'urls': list(merged['urls']),
            'technologies': merged['technologies'],
            'emails': list(merged['emails']),
            'ips': list(merged['ips']),
            'waf': merged['waf']
        } 