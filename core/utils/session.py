from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime
import asyncio
import logging
from dataclasses import dataclass, asdict
from dataclasses_json import dataclass_json

@dataclass_json
@dataclass
class ToolStatus:
    name: str
    status: str = 'pending'
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    output: Optional[str] = None

@dataclass_json
@dataclass
class ModuleStatus:
    name: str
    status: str = 'pending'
    tools: Dict[str, ToolStatus] = None
    start_time: Optional[str] = None
    completion_time: Optional[str] = None
    tools_completed: int = 0
    tools_total: int = 0

class SessionManager:
    def __init__(self, domain: str, output_dir: str = "output"):
        self.domain = domain
        self.base_dir = Path(output_dir)
        self.domain_dir = self.base_dir / domain
        self.session_file = self.domain_dir / "session.json"
        self.logger = logging.getLogger('SessionManager')
        self._setup_directories()
        self.session = self.load_or_create_session()

    def _setup_directories(self) -> None:
        """Setup the directory structure for the domain"""
        try:
            self.domain_dir.mkdir(parents=True, exist_ok=True)
            for subdir in ['raw', 'processed', 'reports']:
                (self.domain_dir / subdir).mkdir(exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creating directories: {e}")
            raise

    def load_or_create_session(self) -> Dict[str, Any]:
        """Load existing session or create new one"""
        try:
            if self.session_file.exists():
                return json.loads(self.session_file.read_text())
        except Exception as e:
            self.logger.error(f"Error loading session: {e}")

        return {
            'domain': self.domain,
            'start_time': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'modules': {}
        }

    def save_session(self) -> None:
        """Save current session state"""
        try:
            self.session['last_updated'] = datetime.now().isoformat()
            self.session_file.write_text(json.dumps(self.session, indent=4))
        except Exception as e:
            self.logger.error(f"Error saving session: {e}")
            raise

    def get_module_status(self, module_name: str) -> Optional[ModuleStatus]:
        """Get the status of a specific module"""
        try:
            if module_name in self.session['modules']:
                data = self.session['modules'][module_name]
                return ModuleStatus.from_dict(data)
            return None
        except Exception as e:
            self.logger.error(f"Error getting module status: {e}")
            return None

    def update_tool_status(self, module_name: str, tool_name: str, status: str, output: Optional[str] = None) -> None:
        """Update the status of a specific tool"""
        try:
            if module_name not in self.session['modules']:
                self.session['modules'][module_name] = asdict(ModuleStatus(name=module_name))

            module = self.session['modules'][module_name]
            if 'tools' not in module:
                module['tools'] = {}

            if tool_name not in module['tools']:
                module['tools'][tool_name] = asdict(ToolStatus(name=tool_name))

            tool = module['tools'][tool_name]
            tool['status'] = status
            if status == 'running' and not tool.get('start_time'):
                tool['start_time'] = datetime.now().isoformat()
            elif status in ['completed', 'error', 'skipped']:
                tool['completion_time'] = datetime.now().isoformat()
                if output:
                    tool['output'] = output

            self.save_session()
        except Exception as e:
            self.logger.error(f"Error updating tool status: {e}")

    def update_module_status(self, module_name: str, status: str) -> None:
        """Update the status of a specific module"""
        try:
            if module_name not in self.session['modules']:
                self.session['modules'][module_name] = asdict(ModuleStatus(name=module_name))

            module = self.session['modules'][module_name]
            module['status'] = status
            if status == 'running' and not module.get('start_time'):
                module['start_time'] = datetime.now().isoformat()
            elif status in ['completed', 'error', 'skipped']:
                module['completion_time'] = datetime.now().isoformat()

            self.save_session()
        except Exception as e:
            self.logger.error(f"Error updating module status: {e}")

    def should_run_module(self, module_name: str) -> bool:
        """Check if a module should be run based on its status"""
        try:
            if module_name not in self.session['modules']:
                return True
            status = self.session['modules'][module_name].get('status', 'pending')
            return status in ['pending', 'error']
        except Exception as e:
            self.logger.error(f"Error checking module status: {e}")
            return True

    def get_module_dir(self, module_name: str) -> Path:
        """Get the directory for a specific module"""
        return self.domain_dir / module_name

    def get_raw_path(self, module_name: str, filename: str) -> Path:
        """Get path for raw tool output"""
        module_dir = self.get_module_dir(module_name)
        module_dir.mkdir(parents=True, exist_ok=True)
        return module_dir / 'raw' / filename

    def get_processed_path(self, module_name: str, filename: str) -> Path:
        """Get path for processed results"""
        module_dir = self.get_module_dir(module_name)
        module_dir.mkdir(parents=True, exist_ok=True)
        return module_dir / 'processed' / filename

    def has_previous_session(self) -> bool:
        """Check if there is a previous session"""
        return self.session_file.exists()

    def archive_session(self) -> None:
        """Archive the current session"""
        if self.session_file.exists():
            archive_dir = self.domain_dir / 'archive'
            archive_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_file = archive_dir / f"session_{timestamp}.json"
            try:
                archive_file.write_text(self.session_file.read_text())
                self.session_file.unlink()  # Remove the current session file
                self.session = self.load_or_create_session()  # Create new session
            except Exception as e:
                self.logger.error(f"Error archiving session: {e}")
                raise

    def restore_session(self) -> None:
        """Restore session from file"""
        try:
            if self.session_file.exists():
                self.session = json.loads(self.session_file.read_text())
        except Exception as e:
            self.logger.error(f"Error restoring session: {e}")
            raise

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the current session"""
        return self.session
