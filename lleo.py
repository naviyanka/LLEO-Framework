#!/usr/bin/env python3

import sys
import signal
import argparse
import os
from datetime import datetime
from colorama import Fore, Style, init
from core.banner import print_banner
from core.utils.logger import setup_logger
from core.utils.config import load_config
from core.framework import LLEOFramework

# Initialize colorama
init()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    try:
        sys.stdout.write(f"\n{Fore.YELLOW}[*] Interrupt received{Style.RESET_ALL}\n")
        sys.stdout.flush()
        
        while True:
            sys.stdout.write("\nDo you want to:\n[1] Skip current tool\n[2] Skip current module\n[3] Quit\nChoice (1-3): ")
            sys.stdout.flush()
            
            try:
                choice = sys.stdin.readline().strip()
                if choice in ['1', '2', '3']:
                    if choice == '3':
                        print(f"\n{Fore.RED}[!] Exiting LLEO Framework{Style.RESET_ALL}")
                        sys.exit(0)
                    return choice
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{Fore.RED}[!] Forced exit{Style.RESET_ALL}")
                sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}[!] Error in signal handler: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='LLEO Framework - Security Reconnaissance Suite')
    parser.add_argument('-d', '--domain', help='Target domain', required=False)
    parser.add_argument('-x', '--exclude', help='Exclude domains list file', required=False)
    parser.add_argument('-s', '--silent', action='store_true', help='Hide terminal output')
    parser.add_argument('-j', '--json', action='store_true', help='Store output in JSON format')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose mode')
    parser.add_argument('--version', action='version', version='LLEO Framework v1.0.0')
    
    return parser.parse_args()

def main():
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse arguments
    args = parse_arguments()
    
    # If no arguments provided, print banner and help
    if len(sys.argv) == 1:
        print_banner()
        sys.exit(0)
    
    # Load configuration
    config = load_config()
    if not config:
        print(f"{Fore.RED}[!] Failed to load configuration{Style.RESET_ALL}")
        sys.exit(1)
    
    # Setup logger
    logger = setup_logger(args.silent)
    
    try:
        # Initialize framework
        framework = LLEOFramework(args, config, logger)
        
        # Run framework
        framework.run()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}[!] Framework error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main() 