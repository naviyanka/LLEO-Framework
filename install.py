#!/usr/bin/env python3
import os
import sys
import time
from typing import List, Tuple
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

def print_status(message: str, status: str, color: str = Fore.GREEN) -> None:
    """Print a formatted status message with color.
    
    Args:
        message: The message to display
        status: The status indicator
        color: ANSI color code (default: Fore.GREEN)
    """
    print(f"{message:<40} [{color}{status}{Style.RESET_ALL}]")

def check_tools(tools: List[str], checker: ToolChecker) -> Tuple[List[str], List[str]]:
    """Check which tools are installed and return results.
    
    Args:
        tools: List of tool names to check
        checker: ToolChecker instance
    
    Returns:
        Tuple containing lists of installed and missing tools
    """
    installed = []
    missing = []
    
    for tool in tools:
        try:
            if checker.check_tool(tool):
                installed.append(tool)
                print_status(f"Checking {tool}", "✓")
            else:
                missing.append(tool)
                print_status(f"Checking {tool}", "✗", Fore.RED)
        except Exception as e:
            print_status(f"Error checking {tool}", "!", Fore.YELLOW)
            logging.error(f"Tool check failed for {tool}: {str(e)}")
    
    return installed, missing

def main() -> None:
    """Main entry point for the installation script."""
    logger = setup_logger(silent=True)
    
    print_banner()
    
    checker = ToolChecker(logger)
    
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
    
    installed, missing = check_tools(tools, checker)
    
    # Summary
    print(f"\n{Fore.GREEN}Installed: {len(installed)}/{len(tools)}{Style.RESET_ALL}")
    if missing:
        print(f"{Fore.RED}Missing tools: {', '.join(missing)}{Style.RESET_ALL}")

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