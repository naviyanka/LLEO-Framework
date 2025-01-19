import os
import yaml
from pathlib import Path

DEFAULT_CONFIG = {
    'api_keys': {
        'securitytrails': '',
        'chaos': '',
        'wayback': '',
        'github': '',
    },
    'tools': {
        'timeout': 300,
        'threads': 10,
        'max_retries': 3,
    },
    'output': {
        'directory': 'output',
        'formats': ['json', 'markdown', 'html'],
    }
}

def load_config():
    """Load configuration from config.yaml"""
    config_path = Path('config/config.yaml')
    
    if not config_path.exists():
        os.makedirs(config_path.parent, exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG
    
    with open(config_path) as f:
        return yaml.safe_load(f) 