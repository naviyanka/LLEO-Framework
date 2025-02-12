from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from pathlib import Path
import os
import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from dataclasses_json import dataclass_json
import logging
from dotenv import load_dotenv
import json
import re

@dataclass_json
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

@dataclass_json
@dataclass
class APIKeys:
	securitytrails: Optional[str] = None
	shodan: Optional[str] = None
	censys: Optional[str] = None
	virustotal: Optional[str] = None
	wpscan: Optional[str] = None

@dataclass
class WordlistConfig:
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

@dataclass_json
@dataclass
class SecureConfig:
	version: str = "1.0.0"
	tools: ToolConfig = field(default_factory=ToolConfig)
	api_keys: Dict[str, str] = field(default_factory=dict)
	wordlists: WordlistConfig = field(default_factory=WordlistConfig)
	output: OutputConfig = field(default_factory=OutputConfig)
	security: SecurityConfig = field(default_factory=SecurityConfig)
	performance: PerformanceConfig = field(default_factory=PerformanceConfig)
	modules: Dict[str, Dict[str, Any]] = field(default_factory=dict)

class ConfigManager:
	def __init__(self, config_file: Optional[str] = None):
		self.config_file = config_file or "config/config.yml"
		self.config = self._load_config()
		self._validate_config()

	def __getattr__(self, name: str) -> Any:
		"""Allow direct access to config attributes"""
		if hasattr(self.config, name):
			return getattr(self.config, name)
		raise AttributeError(f"'ConfigManager' object has no attribute '{name}'")

	def _load_config(self) -> SecureConfig:
		"""Load configuration from file"""
		try:
			with open(self.config_file) as f:
				yaml_config = yaml.safe_load(f)
			return SecureConfig.from_dict(yaml_config)
		except Exception as e:
			logging.error(f"Error loading config: {e}")
			raise

	def _validate_config(self) -> None:
		"""Validate configuration settings"""
		# Validate wordlist paths
		for path_attr in ['dns', 'content']:
			path = getattr(self.config.wordlists, path_attr)
			if not os.path.exists(path):
				logging.warning(f"Wordlist not found: {path}")

		# Validate output directory
		output_dir = Path(self.config.output.directory)
		output_dir.mkdir(parents=True, exist_ok=True)

		# Validate API keys from environment
		for key_name, key_value in self.config.api_keys.items():
			env_key = f"LLEO_{key_name.upper()}_KEY"
			if os.getenv(env_key):
				self.config.api_keys[key_name] = os.getenv(env_key)

	def get(self, key: str, default: Any = None) -> Any:
		"""Get configuration value with default"""
		try:
			return getattr(self.config, key)
		except AttributeError:
			return default

	def reload(self) -> bool:
		"""Reload configuration from file"""
		try:
			old_config = self.config
			self.config = self._load_config()
			self._validate_config()
			return True
		except Exception as e:
			self.config = old_config
			logging.error(f"Failed to reload config: {e}")
			return False

	def _init_encryption(self) -> None:
		"""Initialize encryption with PBKDF2"""
		try:
			key = os.getenv('LLEO_ENCRYPTION_KEY')
			salt = os.getenv('LLEO_SALT', os.urandom(16))
			
			if not key:
				key = base64.b64encode(os.urandom(32)).decode()
				salt = base64.b64encode(os.urandom(16)).decode()
				with open('.env', 'a') as f:
					f.write(f'LLEO_ENCRYPTION_KEY={key}\n')
					f.write(f'LLEO_SALT={salt}\n')
			
			kdf = PBKDF2HMAC(
				algorithm=hashes.SHA256(),
				length=32,
				salt=base64.b64decode(salt) if isinstance(salt, str) else salt,
				iterations=100000,
			)
			
			key_bytes = base64.b64decode(key) if isinstance(key, str) else key
			derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
			self.fernet = Fernet(derived_key)
			
		except Exception as e:
			logging.error(f"Encryption initialization failed: {e}")
			raise

	def get_api_key(self, service: str) -> Optional[str]:
		"""Get decrypted API key"""
		env_key = f'LLEO_{service.upper()}_KEY'
		key = os.getenv(env_key) or getattr(self.config.api_keys, service.lower())
		if key:
			try:
				return self.fernet.decrypt(key.encode()).decode()
			except:
				return key
		return None

	def set_api_key(self, service: str, key: str) -> None:
		"""Set and encrypt API key"""
		encrypted_key = self.fernet.encrypt(key.encode()).decode()
		setattr(self.config.api_keys, service.lower(), encrypted_key)

	def save_config(self, path: Path) -> None:
		"""Save configuration securely"""
		path.parent.mkdir(parents=True, exist_ok=True)
		with open(path, 'w') as f:
			yaml.dump(self.config.to_dict(), f)

	@property
	def tools(self) -> ToolConfig:
		return self.config.tools

	@property
	def wordlists(self) -> WordlistConfig:
		return self.config.wordlists

	@property
	def output(self) -> OutputConfig:
		return self.config.output