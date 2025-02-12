import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import BaseModule
from ..utils.tools import check_tool_exists, run_tool
from datetime import datetime

class WebProbeModule(BaseModule):
    def __init__(self, framework):
        super().__init__(framework)
        self.config = self._load_config()
        
        # Define tools for web probing
        self.tools = {
            'httpx': self._run_httpx,
            '403-bypass': self._run_403_bypass
        }
        
        self.session = framework.session_manager
        self.output_structure = {
            'raw': ['httpx', '403_bypass'],
            'processed': ['live_domains.txt', 'status_codes.json', '403_bypassed.txt']
        }

    def _run_httpx(self, input_file):
        """Run httpx for web probing"""
        try:
            if not check_tool_exists('httpx'):
                return {'error': 'httpx not installed'}

            output_file = self.session.get_raw_path('web_probe', 'httpx_output.json')
            
            cmd = [
                'httpx',
                '-l', input_file,
                '-silent',
                '-status-code',
                '-title',
                '-tech-detect',
                '-json',
                '-o', output_file,
                '-threads', '50'
            ]
            
            run_tool(cmd)
            
            # Process results by status code
            status_results = {
                '200': [],
                '403': [],
                'other': []
            }
            
            if os.path.exists(output_file):
                with open(output_file) as f:
                    for line in f:
                        try:
                            result = json.loads(line)
                            url = result.get('url', '')
                            status_code = str(result.get('status-code', ''))
                            
                            if status_code == '200':
                                status_results['200'].append(result)
                            elif status_code == '403':
                                status_results['403'].append(result)
                            else:
                                status_results['other'].append(result)
                        except json.JSONDecodeError:
                            continue
            
            return {
                'tool': 'httpx',
                'raw_output': output_file,
                'status_results': status_results
            }
                
        except Exception as e:
            self.logger.error(f"Error in httpx: {str(e)}")
            return {'error': str(e)}

    def _run_403_bypass(self, urls):
        """Run 403-bypass on URLs returning 403 status code"""
        try:
            if not check_tool_exists('403-bypass'):
                return {'error': '403-bypass not installed'}

            # Create input file with 403 URLs
            input_file = self.session.get_raw_path('web_probe', '403_urls.txt')
            with open(input_file, 'w') as f:
                for url in urls:
                    f.write(f"{url}\n")

            output_file = self.session.get_raw_path('web_probe', '403_bypass_output.txt')
            
            cmd = [
                '403-bypass',
                '-l', input_file,
                '-o', output_file
            ]
            
            run_tool(cmd)
            
            bypassed_urls = set()
            if os.path.exists(output_file):
                with open(output_file) as f:
                    for line in f:
                        url = line.strip()
                        if url:
                            bypassed_urls.add(url)
            
            return {
                'tool': '403-bypass',
                'raw_output': output_file,
                'bypassed_urls': list(bypassed_urls)
            }
                
        except Exception as e:
            self.logger.error(f"Error in 403-bypass: {str(e)}")
            return {'error': str(e)}

    def _save_results_by_status(self, results):
        """Save results organized by status code"""
        if 'httpx' not in results or 'status_results' not in results['httpx']:
            return
            
        status_results = results['httpx']['status_results']
        
        # Save live domains (200)
        live_domains_file = self.session.get_processed_path('web_probe', 'live_domains.txt')
        with open(live_domains_file, 'w') as f:
            for result in status_results['200']:
                f.write(f"{result['url']}\n")
        
        # Save status code summary
        status_summary = {
            'live_count': len(status_results['200']),
            'forbidden_count': len(status_results['403']),
            'other_count': len(status_results['other']),
            'timestamp': datetime.now().isoformat()
        }
        
        status_file = self.session.get_processed_path('web_probe', 'status_codes.json')
        with open(status_file, 'w') as f:
            json.dump(status_summary, f, indent=4)
        
        # Save bypassed 403 URLs if available
        if '403-bypass' in results and 'bypassed_urls' in results['403-bypass']:
            bypassed_file = self.session.get_processed_path('web_probe', '403_bypassed.txt')
            with open(bypassed_file, 'w') as f:
                for url in results['403-bypass']['bypassed_urls']:
                    f.write(f"{url}\n")

    def run(self):
        """Execute web probing tools and process results"""
        if not self.session.should_run_module('web_probe'):
            self.logger.info("Skipping web probe module...")
            return None

        self.logger.info("Starting web probe phase...")
        
        # Get input file from discovery module
        input_file = self.session.get_processed_path('discovery', 'combined_targets.txt')
        if not os.path.exists(input_file):
            self.logger.error("No targets file found from discovery module")
            return None
            
        results = {}
        
        # Run httpx first
        self.logger.info("Running httpx for web probing...")
        httpx_result = self._run_httpx(input_file)
        results['httpx'] = httpx_result
        
        if 'error' not in httpx_result:
            # Extract 403 URLs for bypass attempts
            forbidden_urls = [r['url'] for r in httpx_result['status_results']['403']]
            
            if forbidden_urls:
                self.logger.info(f"Found {len(forbidden_urls)} URLs returning 403. Running 403-bypass...")
                bypass_result = self._run_403_bypass(forbidden_urls)
                results['403-bypass'] = bypass_result
        
        # Save processed results
        self._save_results_by_status(results)
        
        # Update module status
        self.session.update_module_status('web_probe', 'completed')
        
        return results 