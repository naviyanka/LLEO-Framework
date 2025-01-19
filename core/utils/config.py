import os
import json
import yaml
from pathlib import Path

def load_config():
    """Load configuration from config files"""
    try:
        # Default config
        config = {
            'tools': {
                'threads': 10,
                'rate_limit': 150,
                'timeout': 30
            },
            'api_keys': {},
            'wordlists': {
                'dns': '/usr/share/wordlists/dns.txt',
                'content': '/usr/share/wordlists/dirb/common.txt'
            },
            'output': {
                'format': 'json',
                'directory': 'output'
            }
        }
        
        # Look for config files in multiple locations
        config_locations = [
            os.path.expanduser('~/.config/lleo/config.yml'),
            os.path.expanduser('~/.lleo.yml'),
            'config.yml',
            'config.yaml',
            'config.json'
        ]
        
        # Try to load config from file
        for config_file in config_locations:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    if config_file.endswith('.json'):
                        file_config = json.load(f)
                    else:
                        file_config = yaml.safe_load(f)
                    
                    if file_config:
                        # Update default config with file config
                        _deep_update(config, file_config)
                    break
        
        # Create default config if none exists
        if not any(os.path.exists(f) for f in config_locations):
            default_config_dir = os.path.expanduser('~/.config/lleo')
            os.makedirs(default_config_dir, exist_ok=True)
            
            default_config_file = os.path.join(default_config_dir, 'config.yml')
            with open(default_config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        
        # Ensure output directory exists
        os.makedirs(config['output']['directory'], exist_ok=True)
        
        return config
        
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        return None

def _deep_update(base_dict, update_dict):
    """Recursively update a dictionary"""
    for key, value in update_dict.items():
        if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
            _deep_update(base_dict[key], value)
        else:
            base_dict[key] = value 