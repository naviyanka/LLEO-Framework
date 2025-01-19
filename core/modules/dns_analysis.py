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
                self.logger.info(f"Running {tool_name}...")
                results[tool_name] = tool_func(subdomains)
            except Exception as e:
                self.logger.error(f"Error running {tool_name}: {str(e)}")
                results[tool_name] = {'error': str(e)}
        
        self._save_results(results)
        return results

    def _run_dnsx(self, subdomains):
        """Run dnsx tool"""
        try:
            if not self._check_tool_exists('dnsx'):
                raise Exception("dnsx not found. Please install it first.")
            
            input_file = os.path.join(self.framework.output_dir, 'dnsx_input.txt')
            output_file = os.path.join(self.framework.output_dir, 'dnsx_results.json')
            
            # Write subdomains to input file
            with open(input_file, 'w') as f:
                f.write('\n'.join(subdomains))
            
            cmd = [
                'dnsx',
                '-l', input_file,
                '-json',
                '-a',  # A records
                '-aaaa',  # AAAA records
                '-cname',  # CNAME records
                '-mx',  # MX records
                '-ns',  # NS records
                '-o', output_file
            ]
            
            subprocess.run(cmd, check=True)
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    return {'records': [json.loads(line) for line in f if line.strip()]}
            return {'records': []}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"DNSx error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in dnsx: {str(e)}")
            return {'error': str(e)}

    def _run_altdns(self, subdomains):
        """Run altdns tool"""
        try:
            if not self._check_tool_exists('altdns'):
                raise Exception("altdns not found. Please install it first.")
            
            input_file = os.path.join(self.framework.output_dir, 'altdns_input.txt')
            output_file = os.path.join(self.framework.output_dir, 'altdns_results.txt')
            
            # Write subdomains to input file
            with open(input_file, 'w') as f:
                f.write('\n'.join(subdomains))
            
            # Use default wordlist or specify your own
            wordlist = '/usr/share/wordlists/altdns.txt'  # Ensure this exists
            if not os.path.exists(wordlist):
                # Create a basic wordlist if default doesn't exist
                wordlist = os.path.join(self.framework.output_dir, 'altdns_words.txt')
                with open(wordlist, 'w') as f:
                    f.write('\n'.join(['dev', 'staging', 'prod', 'test', 'admin']))
            
            cmd = [
                'altdns',
                '-i', input_file,
                '-w', wordlist,
                '-o', output_file
            ]
            
            subprocess.run(cmd, check=True)
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    return {'permutations': [line.strip() for line in f if line.strip()]}
            return {'permutations': []}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Altdns error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in altdns: {str(e)}")
            return {'error': str(e)}

    def _run_dnsgen(self, subdomains):
        """Run dnsgen tool"""
        try:
            if not self._check_tool_exists('dnsgen'):
                raise Exception("dnsgen not found. Please install it first.")
            
            input_file = os.path.join(self.framework.output_dir, 'dnsgen_input.txt')
            output_file = os.path.join(self.framework.output_dir, 'dnsgen_results.txt')
            
            # Write subdomains to input file
            with open(input_file, 'w') as f:
                f.write('\n'.join(subdomains))
            
            cmd = ['dnsgen', input_file]
            
            process = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Save and process results
            with open(output_file, 'w') as f:
                f.write(process.stdout)
            
            return {'permutations': [line.strip() for line in process.stdout.splitlines() if line.strip()]}
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"DNSgen error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return {'error': str(e)}
        except Exception as e:
            self.logger.error(f"Unexpected error in dnsgen: {str(e)}")
            return {'error': str(e)}

    def _get_subdomains(self):
        """Get subdomains from discovery results"""
        discovery_file = os.path.join(self.framework.output_dir, 'discovery_results.json')
        if os.path.exists(discovery_file):
            try:
                with open(discovery_file) as f:
                    data = json.load(f)
                    subdomains = []
                    for tool_results in data.values():
                        if isinstance(tool_results, dict) and 'subdomains' in tool_results:
                            subdomains.extend(tool_results['subdomains'])
                    return list(set(subdomains))
            except Exception as e:
                self.logger.error(f"Error reading discovery results: {str(e)}")
        return [self.framework.args.domain]  # Return target domain if no discovery results

    def _check_tool_exists(self, tool_name):
        """Check if a tool is installed"""
        try:
            subprocess.run(['which', tool_name], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _save_results(self, results):
        """Save DNS analysis results"""
        output_file = os.path.join(self.framework.output_dir, 'dns_analysis_results.json')
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4) 