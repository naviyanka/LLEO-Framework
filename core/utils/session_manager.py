import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import aiofiles
import logging

class SessionManager:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create standard subdirectories
        for subdir in ['raw', 'processed', 'temp', 'logs']:
            (self.output_dir / subdir).mkdir(parents=True, exist_ok=True)
            
        self.session_file = self.output_dir / 'session.json'
        self.module_results = {}
        self.logger = logging.getLogger(__name__)
        self._load_session()

    def _load_session(self) -> None:
        """Load session data from file"""
        try:
            if self.session_file.exists():
                with open(self.session_file) as f:
                    self.session_data = json.load(f)
            else:
                self.session_data = {
                    'start_time': datetime.now().isoformat(),
                    'modules': {},
                    'metrics': {}
                }
        except Exception as e:
            self.logger.error(f"Error loading session: {e}")
            self.session_data = {
                'start_time': datetime.now().isoformat(),
                'modules': {},
                'metrics': {}
            }

    async def save_session(self) -> None:
        """Save session data to file"""
        try:
            async with aiofiles.open(self.session_file, 'w') as f:
                await f.write(json.dumps(self.session_data, indent=2))
        except Exception as e:
            self.logger.error(f"Error saving session: {e}")

    async def save_results(self, module_name: str, results: dict) -> None:
        """Save module results to file and update session data"""
        try:
            # Store results in memory
            self.module_results[module_name] = results
            
            # Create module-specific directories
            module_dir = self.output_dir / module_name
            for subdir in ['raw', 'processed']:
                (module_dir / subdir).mkdir(parents=True, exist_ok=True)
            
            # Save results to file
            results_file = module_dir / 'processed' / f"{module_name}_results.json"
            async with aiofiles.open(results_file, 'w') as f:
                await f.write(json.dumps(results, indent=2))
            
            # Update session data
            self.session_data['modules'][module_name] = {
                'completed_at': datetime.now().isoformat(),
                'results_file': str(results_file),
                'status': 'completed'
            }
            
            # Save updated session data
            await self.save_session()
            
            self.logger.info(f"Saved {module_name} results to {results_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving results for {module_name}: {e}")
            self.session_data['modules'][module_name] = {
                'completed_at': datetime.now().isoformat(),
                'error': str(e),
                'status': 'error'
            }
            await self.save_session()

    async def get_results(self, module_name: str) -> dict:
        """Get module results from memory or file"""
        try:
            # Check if results are in memory
            if module_name in self.module_results:
                return self.module_results[module_name]
            
            # Try to load from file
            module_dir = self.output_dir / module_name
            results_file = module_dir / 'processed' / f"{module_name}_results.json"
            
            if results_file.exists():
                async with aiofiles.open(results_file) as f:
                    content = await f.read()
                    results = json.loads(content)
                    self.module_results[module_name] = results
                    return results
                    
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting results for {module_name}: {e}")
            return {}

    async def update_metrics(self, module_name: str, metrics: dict) -> None:
        """Update session metrics for a module"""
        try:
            if module_name not in self.session_data['metrics']:
                self.session_data['metrics'][module_name] = {}
            
            self.session_data['metrics'][module_name].update(metrics)
            await self.save_session()
            
        except Exception as e:
            self.logger.error(f"Error updating metrics for {module_name}: {e}")

    async def archive_session(self) -> None:
        """Archive current session and create new output directory"""
        try:
            if self.output_dir.exists():
                # Create archive directory if it doesn't exist
                archive_dir = self.output_dir.parent / 'archive'
                archive_dir.mkdir(exist_ok=True)
                
                # Create timestamped archive directory
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                session_archive = archive_dir / f"session_{timestamp}"
                
                # Move current output directory to archive
                shutil.move(str(self.output_dir), str(session_archive))
                
                # Create new output directory
                self.output_dir.mkdir(parents=True)
                
                # Initialize new session
                self.session_data = {
                    'start_time': datetime.now().isoformat(),
                    'modules': {},
                    'metrics': {}
                }
                await self.save_session()
                
        except Exception as e:
            self.logger.error(f"Error archiving session: {e}")

    async def clear_session(self) -> None:
        """Clear current session data"""
        try:
            self.session_data = {
                'start_time': datetime.now().isoformat(),
                'modules': {},
                'metrics': {}
            }
            self.module_results = {}
            await self.save_session()
            
        except Exception as e:
            self.logger.error(f"Error clearing session: {e}")

    def get_module_dir(self, module_name: str) -> Path:
        """Get module output directory"""
        module_dir = self.output_dir / module_name
        for subdir in ['raw', 'processed', 'temp']:
            (module_dir / subdir).mkdir(parents=True, exist_ok=True)
        return module_dir

    def get_raw_path(self, module_name: str, filename: str) -> Path:
        """Get path for raw output file"""
        module_dir = self.get_module_dir(module_name)
        return module_dir / 'raw' / filename

    def get_processed_path(self, module_name: str, filename: str) -> Path:
        """Get path for processed output file"""
        module_dir = self.get_module_dir(module_name)
        return module_dir / 'processed' / filename

    def get_temp_path(self, module_name: str, filename: str) -> Path:
        """Get path for temporary file"""
        module_dir = self.get_module_dir(module_name)
        return module_dir / 'temp' / filename

    def get_metrics(self) -> dict:
        """Get all session metrics"""
        return self.session_data.get('metrics', {}) 