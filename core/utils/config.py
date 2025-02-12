import os
import json
import yaml
import re
from pathlib import Path
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class ConfigVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def from_string(cls, version_str: str) -> 'ConfigVersion':
        try:
            major, minor, patch = map(int, version_str.split('.'))
            return cls(major, minor, patch)
        except:
            return cls(1, 0, 0)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

@dataclass
class ToolConfig:
    threads: int = 10
    rate_limit: int = 150
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 5
    burst_size: int = 10
    max_memory_percent: int = 80
    max_disk_percent: int = 90

@dataclass
class ApiKeys:
    securitytrails: str = ""
    shodan: str = ""
    censys: str = ""
    virustotal: str = ""
    wpscan: str = ""

@dataclass
class Wordlists:
    dns: str = "/usr/share/wordlists/dns.txt"
    content: str = "/usr/share/wordlists/dirb/common.txt"

@dataclass
class OutputConfig:
    format: str = "json"
    directory: str = "output"
    compress_older_than: str = "7d"

@dataclass
class SecurityConfig:
    encrypt_results: bool = False
    encryption_key: str = ""
    sandbox_external_tools: bool = True
    max_file_size_mb: int = 100

@dataclass
class PerformanceConfig:
    cache_results: bool = True
    cache_ttl: int = 3600
    max_memory_percent: int = 80

@dataclass
class ModuleConfig:
    enabled: bool = True
    tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)

@dataclass
class Config:
    version: str = "1.0.0"
    tools: ToolConfig = field(default_factory=ToolConfig)
    api_keys: ApiKeys = field(default_factory=ApiKeys)
    wordlists: Wordlists = field(default_factory=Wordlists)
    output: OutputConfig = field(default_factory=OutputConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    modules: Dict[str, ModuleConfig] = field(default_factory=dict)

    def __init__(self, env_prefix: str = 'LLEO_'):
        self.env_prefix = env_prefix
        self.version = ConfigVersion(1, 0, 0)
        self.config: Dict[str, Any] = {}
        self.config_file: Optional[Path] = None
        self.load_config()
        if not self.config:
            raise Exception("Failed to load configuration")
        self.validate_config()

    def __getitem__(self, key):
        return self.config[key]

    def get(self, key, default=None):
        return self.config.get(key, default)

    def reload(self) -> bool:
        """Reload configuration from file"""
        try:
            old_config = self.config.copy()
            self.load_config()
            self.validate_config()
            return True
        except Exception as e:
            self.config = old_config
            logging.error(f"Failed to reload config: {e}")
            return False

    def load_config(self) -> None:
        """Load configuration from config files with version control"""
        try:
            # Default config with version
            self.config = {
                'version': str(self.version),
                'tools': {
                    'threads': 10,
                    'rate_limit': 150,
                    'timeout': 30,
                    'retry_count': 3,
                    'retry_delay': 5
                },
                'api_keys': {
                    'securitytrails': self._get_env_var('SECURITYTRAILS_KEY'),
                    'shodan': self._get_env_var('SHODAN_KEY'),
                    'censys': self._get_env_var('CENSYS_KEY'),
                    'virustotal': self._get_env_var('VIRUSTOTAL_KEY'),
                    'wpscan': self._get_env_var('WPSCAN_KEY')
                },
                'wordlists': {
                    'dns': '/usr/share/wordlists/dns.txt',
                    'content': '/usr/share/wordlists/dirb/common.txt'
                },
                'output': {
                    'format': 'json',
                    'directory': 'output',
                    'compress_older_than': '7d'
                },
                'security': {
                    'encrypt_results': False,
                    'encryption_key': self._get_env_var('ENCRYPTION_KEY', ''),
                    'sandbox_external_tools': True,
                    'max_file_size_mb': 100
                },
                'performance': {
                    'cache_results': True,
                    'cache_ttl': 3600,
                    'max_memory_percent': 80
                }
            }
            
            # Look for config files in multiple locations
            config_locations = [
                os.path.expanduser('~/.config/lleo/config.yml'),
                'config/config.yml'
            ]
            
            # Try to load config from file
            for config_file in config_locations:
                if os.path.exists(config_file):
                    self.config_file = Path(config_file)
                    with open(config_file, 'r') as f:
                        file_config = yaml.safe_load(f)
                        
                        if file_config:
                            # Check version compatibility
                            if 'version' in file_config:
                                file_version = ConfigVersion.from_string(file_config['version'])
                                if file_version.major > self.version.major:
                                    raise ValueError(f"Config version {file_version} is not compatible with current version {self.version}")
                            
                            # Update default config with file config
                            self._deep_update(self.config, file_config)
                        break
            
        except Exception as e:
            logging.error(f"Error loading config: {str(e)}")
            raise

    def _get_env_var(self, name: str, default: str = '') -> str:
        """Get environment variable with prefix"""
        return os.getenv(f"{self.env_prefix}{name}", default)

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> Dict:
        """Recursively update a dictionary"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                self._deep_update(base_dict[key], value)
            else:
                # Don't override environment variables for API keys
                if key == 'api_keys' and isinstance(value, dict):
                    for api_key, api_value in value.items():
                        env_var = f'{self.env_prefix}{api_key.upper()}_KEY'
                        if not os.getenv(env_var):
                            base_dict[key][api_key] = api_value
                else:
                    base_dict[key] = value
        return base_dict

    def validate_config(self) -> None:
        """Validate configuration settings with enhanced checks"""
        required_fields = ['tools', 'api_keys', 'output', 'security', 'performance']
        
        # Check required fields
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
        
        # Validate tool settings
        tools = self.config['tools']
        if tools.get('threads', 0) < 1:
            raise ValueError("Thread count must be positive")
        if tools.get('rate_limit', 0) < 0:
            raise ValueError("Rate limit cannot be negative")
        if tools.get('timeout', 0) < 1:
            raise ValueError("Timeout must be positive")
        
        # Validate API keys format
        for key, value in self.config['api_keys'].items():
            if value and not self._validate_api_key_format(key, value):
                logging.warning(f"API key for {key} may be invalid")
        
        # Validate security settings
        security = self.config['security']
        if security.get('encrypt_results') and not security.get('encryption_key'):
            raise ValueError("Encryption key required when encryption is enabled")
        
        # Validate performance settings
        perf = self.config['performance']
        if not (0 < perf.get('max_memory_percent', 0) <= 100):
            raise ValueError("max_memory_percent must be between 0 and 100")

    def _validate_api_key_format(self, provider: str, key: str) -> bool:
        """Validate API key format for different providers"""
        patterns = {
            'securitytrails': r'^[a-zA-Z0-9]{32}$',
            'shodan': r'^[a-zA-Z0-9]{32}$',
            'censys': r'^[a-zA-Z0-9]{32}$',
            'virustotal': r'^[a-zA-Z0-9]{64}$',
            'wpscan': r'^[a-zA-Z0-9]{32}$'
        }
        
        if provider in patterns:
            return bool(re.match(patterns[provider], key))
        return True  # Return True for unknown providers

    def save(self) -> None:
        """Save current configuration to file"""
        if not self.config_file:
            return
            
        try:
            # Create backup
            if self.config_file.exists():
                backup_path = self.config_file.with_suffix('.yml.bak')
                self.config_file.rename(backup_path)
            
            # Save new config
            with open(self.config_file, 'w') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
                
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            # Restore backup if exists
            if backup_path.exists():
                backup_path.rename(self.config_file)
            raise