#!/usr/bin/env python3

import sys
import signal
import argparse
from colorama import init, Fore, Style
from core.banner import print_banner
from core.logger import setup_logger
from core.config import load_config
from core.framework import LLEOFramework

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print(f"\n{Fore.YELLOW}[*] Interrupt received{Style.RESET_ALL}")
    choice = input("\nDo you want to: \n[1] Skip current tool\n[2] Skip current function\n[3] Quit\nChoice (1-3): ")
    
    if choice == '1':
        return
    elif choice == '2':
        return
    else:
        print(f"\n{Fore.RED}[!] Exiting LLEO Framework{Style.RESET_ALL}")
        sys.exit(0)

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
    """Main function"""
    # Initialize colorama
    init()
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse arguments
    args = parse_arguments()
    
    # If no arguments provided, print banner and help
    if len(sys.argv) == 1:
        print_banner()
        sys.exit(0)
    
    # Load configuration
    config = load_config()
    
    # Setup logger
    logger = setup_logger(args.silent)
    
    # Initialize framework
    framework = LLEOFramework(args, config, logger)
    
    # Start framework
    framework.run()

if __name__ == "__main__":
    main() 