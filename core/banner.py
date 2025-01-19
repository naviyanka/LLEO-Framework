from colorama import Fore, Style

def print_banner():
    """Print LLEO Framework banner"""
    banner = f"""{Fore.CYAN}
    ██╗     ██╗     ███████╗ ██████╗ 
    ██║     ██║     ██╔════╝██╔═══██╗
    ██║     ██║     █████╗  ██║   ██║
    ██║     ██║     ██╔══╝  ██║   ██║
    ███████╗███████╗███████╗╚██████╔╝
    ╚══════╝╚══════╝╚══════╝ ╚═════╝ 
    {Style.RESET_ALL}
    {Fore.GREEN}[ LLEO Framework v1.0.0 ]{Style.RESET_ALL}
    {Fore.YELLOW}Comprehensive Security Reconnaissance Suite For Bug Bounty{Style.RESET_ALL}
    
Example Usage:
    lleo [-d target.tld] [-x exclude domains] [--json] [-s]

Flags:
    -d, --domain                 string     Add your target                         -d target.tld
    -x, --exclude                string     Exclude out of scope domains            -x /home/domains.list

Optional Flags:
    -s, --silent                            Hide output in the terminal             Default: False
    -j, --json                              Store output in a single json file      Default: False
    -v, --verbose                           Verbose Mode                            Default: False
    --version                               Print current version of LLEO Framework
    -h, --help                              Print detailed Help menu
    """
    print(banner) 