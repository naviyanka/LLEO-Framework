#!/usr/bin/env python3
import os
import sys
import time
from colorama import Fore, Style, init
from core.utils.logger import setup_logger
from core.utils.tool_checker import ToolChecker

# Initialize colorama
init()

def print_banner():
    banner = f"""
    {Fore.CYAN}
    ██╗     ██╗     ███████╗ ██████╗ 
    ██║     ██║     ██╔════╝██╔═══██╗
    ██║     ██║     █████╗  ██║   ██║
    ██║     ██║     ██╔══╝  ██║   ██║
    ███████╗███████╗███████╗╚██████╔╝
    ╚══════╝╚══════╝╚══════╝ ╚═════╝ 
    {Style.RESET_ALL}
    {Fore.YELLOW}Comprehensive Security Reconnaissance Suite{Style.RESET_ALL}
    """
    print(banner)

def print_status(message, status, color=Fore.GREEN):
    """Print a status message with color"""
    print(f"{message:<40} [{color}{status}{Style.RESET_ALL}]")

def main():
    # Setup logger (silent mode for cleaner output)
    logger = setup_logger(silent=True)
    
    print_banner()
    
    # Initialize tool checker
    checker = ToolChecker(logger)
    
    # List of all tools
    tools = [
        'naabu', 'wafw00f', 'nuclei', 'whatweb', 'dnsx',
        'dalfox', 'dnsgen', 'sqlmap', 'haktrails', 'assetfinder',
        '403-bypass', 'aquatone', 'altdns', 'nikto', 'gospider',
        'subfinder', 'nmap', 'ghauri', 'httpx', 'ffuf',
        'dirsearch', 'wpscan', 'metasploit', 'spiderfoot',
        'findomain', 'amass', 'wfuzz', 'gobuster', 'waybackurls',
        'gauplus', 'kxss', 'katana', 'crlfuzz'
    ]
    
    print(f"\n{Fore.CYAN}[*] Checking installed tools...{Style.RESET_ALL}\n")
    
    installed = []
    missing = []
    
    # Add a loading animation
    for tool in tools:
        is_installed, _ = checker.check_tool(tool)
        if is_installed:
            installed.append(tool)
            print_status(f"Checking {tool}", "✓")
        else:
            missing.append(tool)
            print_status(f"Checking {tool}", "✗", Fore.RED)
        time.sleep(0.1)  # Small delay for visual effect
    
    print(f"\n{Fore.GREEN}[+] Found {len(installed)} installed tools{Style.RESET_ALL}")
    
    if missing:
        print(f"\n{Fore.YELLOW}[!] Missing tools:{Style.RESET_ALL}")
        for tool in missing:
            print(f"  • {tool}")
        
        print()  # Empty line
        response = input(f"{Fore.CYAN}[?] Do you want to install missing tools? [Y/n] {Style.RESET_ALL}")
        if response.lower() != 'n':
            print()  # Empty line
            for tool in missing:
                print(f"{Fore.CYAN}[*] Installing {tool}...{Style.RESET_ALL}")
                checker.install_missing_tools([tool])
    
    print(f"\n{Fore.GREEN}[+] Installation completed!{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[*] Please configure your API keys in config/config.yaml{Style.RESET_ALL}\n")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print(f"\n{Fore.RED}[!] Please run as root{Style.RESET_ALL}\n")
        sys.exit(1)
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Installation cancelled by user{Style.RESET_ALL}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}[!] Error: {str(e)}{Style.RESET_ALL}\n")
        sys.exit(1) 