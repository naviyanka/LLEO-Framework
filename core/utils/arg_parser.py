import argparse
from pathlib import Path
import sys
from core.utils.banner import print_banner

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='LLEO - Security Testing Framework',
        usage='%(prog)s [-h] -d DOMAIN [-s] [-v] [-o OUTPUT] [-c CONFIG] [--no-color] [--force-new]'
    )
    
    parser.add_argument(
        '-d', '--domain',
        required=True,
        help='Target domain'
    )
    
    parser.add_argument(
        '-s', '--silent',
        action='store_true',
        help='Silent mode'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output directory',
        default='output'
    )
    
    parser.add_argument(
        '-c', '--config',
        help='Custom config file path',
        default='config/config.yml'
    )
    
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    
    parser.add_argument(
        '--force-new',
        action='store_true',
        help='Force new session'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='LLEO v1.0'
    )
    
    # Only show help if no arguments provided
    if len(sys.argv) == 1:
        print_banner(show_usage=True)
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Validate config file
    config_file = Path(args.config)
    if not config_file.exists():
        print(f"ERROR: Config file not found: {config_file}")
        sys.exit(1)
    
    return args 