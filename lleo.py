#!/usr/bin/env python3

import os
import sys
import logging
import argparse
from pathlib import Path
from core.framework import Framework

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] %(levelname)-8s %(message)s',
        datefmt='%y/%m/%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='LLEO Security Testing Framework')
    parser.add_argument('-d', '--domain', required=True, help='Target domain')
    parser.add_argument('-s', '--silent', action='store_true', help='Silent mode')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-o', '--output', help='Output directory')
    parser.add_argument('-c', '--config', help='Custom config file')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    return parser.parse_args()

async def run_framework(framework: Framework) -> None:
    """Run the framework"""
    try:
        await framework.start()
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, cleaning up...")
        await framework.cleanup()
    except Exception as e:
        print(f"Critical error: {e}")
        await framework.cleanup()

def main() -> None:
    """Main entry point"""
    try:
        # Parse arguments
        args = parse_args()
        
        # Setup logging
        logger = setup_logging(args.verbose)
        
        # Create framework instance
        framework = Framework(args)
        
        # Run framework
        import asyncio
        asyncio.run(run_framework(framework))
        
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    # Print banner
    print("""╭───────────────────────────────────────── LLEO ──────────────────────────────────────────╮
│                                                                                         │
│                                                                                         │
│  ██╗     ██╗     ███████╗ ██████╗                                                       │
│  ██║     ██║     ██╔════╝██╔═══██╗                                                      │
│  ██║     ██║     █████╗  ██║   ██║                                                      │
│  ██║     ██║     ██╔══╝  ██║   ██║                                                      │
│  ███████╗███████╗███████╗╚██████╔╝                                                      │
│  ╚══════╝╚══════╝╚══════╝ ╚═════╝                                                       │
│                                                                                         │
│  LLEO Security Testing Framework v1.0.0                                                 │
│                                                                                         │
│  Usage:                                                                                 │
│    lleo -d example.com [options]                                                        │
│                                                                                         │
│  Options:                                                                               │
│    -d, --domain    Target domain (required)                                             │
│    -s, --silent    Silent mode                                                          │
│    -v, --verbose   Verbose output                                                       │
│    -o, --output    Output directory                                                     │
│    -c, --config    Custom config file                                                   │
│    --no-color      Disable colored output                                               │
│                                                                                         │
│                                                                                         │
│                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────╯""")
    main()
