from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
import json

class Banner:
    def __init__(self, no_color: bool = False):
        self.console = Console(color_system=None if no_color else 'auto')
        self._load_version()

    def _load_version(self) -> None:
        """Load version from package info"""
        try:
            package_file = Path(__file__).parent.parent.parent / 'package.json'
            if package_file.exists():
                self.version = json.loads(package_file.read_text()).get('version', '1.0.0')
            else:
                self.version = '1.0.0'
        except Exception:
            self.version = '1.0.0'

    def print_banner(self, show_usage: bool = True) -> None:
        """Print the LLEO banner with optional usage information"""
        banner_text = Text()
        banner_text.append('\n')
        banner_text.append('██╗     ██╗     ███████╗ ██████╗\n', style='blue')
        banner_text.append('██║     ██║     ██╔════╝██╔═══██╗\n', style='blue')
        banner_text.append('██║     ██║     █████╗  ██║   ██║\n', style='cyan')
        banner_text.append('██║     ██║     ██╔══╝  ██║   ██║\n', style='cyan')
        banner_text.append('███████╗███████╗███████╗╚██████╔╝\n', style='green')
        banner_text.append('╚══════╝╚══════╝╚══════╝ ╚═════╝\n', style='green')
        banner_text.append(f'\nLLEO Security Testing Framework v{self.version}\n', style='yellow')
        
        if show_usage:
            banner_text.append('\nUsage:\n', style='bold')
            banner_text.append('  lleo -d example.com [options]\n\n')
            banner_text.append('Options:\n', style='bold')
            banner_text.append('  -d, --domain    Target domain (required)\n')
            banner_text.append('  -s, --silent    Silent mode\n')
            banner_text.append('  -v, --verbose   Verbose output\n')
            banner_text.append('  -o, --output    Output directory\n')
            banner_text.append('  -c, --config    Custom config file\n')
            banner_text.append('  --no-color      Disable colored output\n')
            banner_text.append('\n')

        panel = Panel(
            banner_text,
            border_style='blue',
            padding=(1, 2),
            title='[yellow]LLEO[/yellow]'
        )
        self.console.print(panel)

def print_banner(show_usage: bool = True, no_color: bool = False) -> None:
    """Convenience function to print banner"""
    Banner(no_color=no_color).print_banner(show_usage)
