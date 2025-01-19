import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.modules.discovery import DiscoveryModule
from core.modules.dns_analysis import DNSAnalysisModule
from core.modules.web_fuzzing import WebFuzzingModule
from core.modules.web_probing import WebProbingModule
from core.modules.vulnerability_scan import VulnerabilityScanModule

class LLEOFramework:
    def __init__(self, args, config, logger):
        self.args = args
        self.config = config
        self.logger = logger
        self.results = {}
        self.current_module = None
        
        # Initialize output directory
        self.output_dir = self._setup_output_dir()
        
        # Initialize modules
        self.modules = {
            'discovery': DiscoveryModule(self),
            'dns_analysis': DNSAnalysisModule(self),
            'web_fuzzing': WebFuzzingModule(self),
            'web_probing': WebProbingModule(self),
            'vulnerability_scan': VulnerabilityScanModule(self)
        }
    
    def _setup_output_dir(self):
        """Setup output directory structure"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = os.path.join('output', f"{self.args.domain}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    def run(self):
        """Run the framework"""
        self.logger.info(f"Starting scan for domain: {self.args.domain}")
        
        try:
            # Run modules in sequence
            for module_name, module in self.modules.items():
                self.current_module = module_name
                self.logger.info(f"Running {module_name} module...")
                module_results = module.run()
                self.results[module_name] = module_results
                
            # Generate reports
            self._generate_reports()
            
        except Exception as e:
            self.logger.error(f"Error in framework execution: {str(e)}")
            raise
    
    def _generate_reports(self):
        """Generate various report formats"""
        if self.args.json:
            self._save_json_report()
        self._save_markdown_report()
        self._save_html_report()
    
    def _save_json_report(self):
        """Save results in JSON format"""
        json_path = os.path.join(self.output_dir, 'report.json')
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=4) 