from typing import Dict, List, Optional, Set, Any, Union
from pathlib import Path
import asyncio
import logging
from dataclasses import dataclass
import json
from datetime import datetime
from dataclasses import asdict
import re

@dataclass
class ToolInfo:
    name: str
    path: Optional[str] = None
    version: Optional[str] = None
    installed: bool = False
    error: Optional[str] = None

class ToolChecker:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.tool_status: Dict[str, Dict[str, Union[bool, str, None]]] = {}
        self.go_paths = [
            Path.home() / 'go' / 'bin',
            Path('/usr/local/go/bin'),
            Path('/usr/local/bin'),
            Path('/usr/bin')
        ]
        self.tool_cache: Dict[str, ToolInfo] = {}
        
        # Tool aliases mapping
        self.tool_aliases = {
            'nuclei': ['nuclei'],
            'subfinder': ['subfinder'],
            'httpx': ['httpx'],
            'naabu': ['naabu'],
            'ffuf': ['ffuf'],
            'gobuster': ['gobuster'],
            'wpscan': ['wpscan', 'wp-scan'],
            'nikto': ['nikto'],
            'sqlmap': ['sqlmap'],
            'amass': ['amass'],
            'waybackurls': ['waybackurls'],
            'gau': ['gau', 'getallurls']
        }

        # Required tools and their minimum versions
        self.required_tools = {
            'subfinder': '2.6.0',
            'amass': '3.23.3',
            'findomain': '8.2.1',
            'naabu': '2.1.6',
            'httpx': '1.3.5',
            'nuclei': '3.0.0',
            'katana': '1.0.4',
            'ffuf': '2.1.0',
            'gobuster': '3.6.0',
            'wpscan': '3.8.24',
            'nikto': '2.5.0',
            'sqlmap': '1.7.10',
            'dalfox': '2.9.1',
            'ghauri': '1.0.0',
            'kxss': '1.0.0',
            'crlfuzz': '1.5.0'
        }
        
        # Tool installation commands
        self.install_commands = {
            'subfinder': 'go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest',
            'amass': 'go install -v github.com/owasp-amass/amass/v4/...@master',
            'findomain': 'go install -v github.com/Findomain/Findomain@latest',
            'naabu': 'go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest',
            'httpx': 'go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest',
            'nuclei': 'go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest',
            'katana': 'go install -v github.com/projectdiscovery/katana/cmd/katana@latest',
            'ffuf': 'go install -v github.com/ffuf/ffuf/v2@latest',
            'gobuster': 'go install -v github.com/OJ/gobuster/v3@latest',
            'dalfox': 'go install -v github.com/hahwul/dalfox/v2@latest',
            'ghauri': 'go install -v github.com/r0oth3x49/ghauri@latest',
            'kxss': 'go install -v github.com/Emoe/kxss@latest',
            'crlfuzz': 'go install -v github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest'
        }

    async def check_tool(self, tool_name: str) -> bool:
        """Check if a tool is installed and update status"""
        try:
            process = await asyncio.create_subprocess_exec(
                'which',
                tool_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            status = {
                'installed': process.returncode == 0,
                'path': stdout.decode().strip() if stdout else None,
                'error': stderr.decode().strip() if stderr else None,
                'last_check': datetime.now().isoformat()
            }
            
            self.tool_status[tool_name] = status
            return status['installed']
            
        except Exception as e:
            self.logger.error(f"Error checking tool {tool_name}: {e}")
            status = {
                'installed': False,
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
            self.tool_status[tool_name] = status
            return False

    async def check_tools(self, tools: List[str]) -> Dict[str, bool]:
        """Check multiple tools and return their status"""
        results = {}
        for tool in tools:
            results[tool] = await self.check_tool(tool)
        return results

    async def get_tool_version(self, tool_name: str, version_flag: str = '--version') -> Optional[str]:
        """Get the version of an installed tool"""
        try:
            process = await asyncio.create_subprocess_exec(
                tool_name,
                version_flag,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                version_output = stdout.decode().strip() or stderr.decode().strip()
                if version_output:
                    return version_output
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting version for {tool_name}: {e}")
            return None

    async def verify_tool_version(self, tool_name: str, min_version: str) -> bool:
        """Verify if a tool meets the minimum version requirement"""
        try:
            version = await self.get_tool_version(tool_name)
            if not version:
                return False
                
            # Extract version number from string (basic implementation)
            import re
            version_match = re.search(r'(\d+\.\d+\.\d+)', version)
            if not version_match:
                return False
                
            tool_version = version_match.group(1)
            
            # Compare versions (basic implementation)
            tool_parts = [int(x) for x in tool_version.split('.')]
            min_parts = [int(x) for x in min_version.split('.')]
            
            return tool_parts >= min_parts
            
        except Exception as e:
            self.logger.error(f"Error verifying version for {tool_name}: {e}")
            return False

    async def export_tool_status(self, output_file: Optional[Path] = None) -> Dict[str, Union[str, Dict[str, Union[bool, str, None]]]]:
        """Export tool status to file and return the data"""
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'tools': self.tool_status
        }
        
        if output_file:
            try:
                output_file = Path(output_file)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w') as f:
                    json.dump(status_data, f, indent=4)
            except Exception as e:
                self.logger.error(f"Error exporting tool status: {e}")
        
        return status_data

    async def check_all_tools(self) -> Dict[str, Dict[str, Union[bool, str, None]]]:
        """Check all known tools"""
        tasks = [self.check_tool(tool) for tool in self.tool_aliases.keys()]
        results = await asyncio.gather(*tasks)
        return {tool: self.tool_status[tool] for tool in self.tool_status if self.tool_status[tool]['installed']}

    async def install_missing_tools(self, tools: List[str]) -> None:
        """Attempt to install missing tools"""
        missing_tools = []
        for tool in tools:
            if not await self.check_tool(tool):
                missing_tools.append(tool)

        for tool in missing_tools:
            try:
                self.logger.info(f"Installing {tool}...")
                process = await asyncio.create_subprocess_exec(
                    'go',
                    'install',
                    f'github.com/projectdiscovery/{tool}@latest',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                # Clear cache for this tool
                self.tool_cache.pop(tool, None)
                
            except Exception as e:
                self.logger.error(f"Error installing {tool}: {e}")

    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """Get the path of an installed tool"""
        tool_info = self.tool_cache.get(tool_name)
        return tool_info.path if tool_info and tool_info.installed else None

    async def verify_all_tools(self) -> Dict[str, Dict[str, Any]]:
        """Verify all required tools and their versions"""
        self.logger.info("\n=== Verifying Required Tools ===")
        results = {}
        missing_tools = []
        outdated_tools = []
        
        for tool, min_version in self.required_tools.items():
            self.logger.info(f"\nChecking {tool}...")
            
            # Check if tool exists
            exists = await self.check_tool(tool)
            if not exists:
                self.logger.error(f"❌ {tool} not found")
                missing_tools.append(tool)
                results[tool] = {
                    'installed': False,
                    'version': None,
                    'min_version': min_version,
                    'status': 'missing'
                }
                continue
            
            # Get tool version
            current_version = await self.get_tool_version(tool)
            is_outdated = False
            
            if current_version and min_version:
                try:
                    is_outdated = self._compare_versions(current_version, min_version)
                    if is_outdated:
                        self.logger.warning(f"⚠️  {tool} is outdated (Current: {current_version}, Required: {min_version})")
                        outdated_tools.append((tool, current_version, min_version))
                    else:
                        self.logger.info(f"✅ {tool} version {current_version} is up to date")
                except:
                    self.logger.warning(f"⚠️  Could not compare versions for {tool}")
            else:
                if current_version:
                    self.logger.info(f"✅ {tool} version {current_version} found")
                else:
                    self.logger.warning(f"⚠️  Could not determine {tool} version")
            
            results[tool] = {
                'installed': True,
                'version': current_version,
                'min_version': min_version,
                'status': 'outdated' if is_outdated else 'ok'
            }
        
        # Print summary if there are issues
        if missing_tools or outdated_tools:
            self.logger.warning("\n=== Tool Status Summary ===")
            if missing_tools:
                self.logger.warning("\nMissing Tools:")
                for tool in missing_tools:
                    self.logger.warning(f"❌ {tool} (Required)")
            
            if outdated_tools:
                self.logger.warning("\nOutdated Tools:")
                for tool, current, required in outdated_tools:
                    self.logger.warning(f"⚠️  {tool} (Current: {current}, Required: {required})")
            
            self.logger.warning("\nRecommendations:")
            if missing_tools:
                self.logger.warning("- Install missing tools:")
                for tool in missing_tools:
                    if tool in self.install_commands:
                        self.logger.warning(f"  {self.install_commands[tool]}")
            if outdated_tools:
                self.logger.warning("- Update outdated tools:")
                for tool, _, _ in outdated_tools:
                    if tool in self.install_commands:
                        self.logger.warning(f"  {self.install_commands[tool]}")
            
            return results, bool(missing_tools or outdated_tools)
        else:
            self.logger.info("\n✅ All tools are installed and up to date!")
        
        return results, False

    def _compare_versions(self, current: str, minimum: str) -> bool:
        """Compare version strings, return True if current is older than minimum"""
        try:
            current_parts = [int(x) for x in current.split('.')]
            min_parts = [int(x) for x in minimum.split('.')]
            
            # Pad with zeros if needed
            while len(current_parts) < len(min_parts):
                current_parts.append(0)
            while len(min_parts) < len(current_parts):
                min_parts.append(0)
            
            return current_parts < min_parts
        except:
            return False

    async def get_tool_version(self, tool: str) -> Optional[str]:
        """Get tool version using appropriate command"""
        version_commands = {
            'subfinder': ['subfinder', '-version'],
            'amass': ['amass', 'version'],
            'findomain': ['findomain', '--version'],
            'naabu': ['naabu', '-version'],
            'httpx': ['httpx', '-version'],
            'nuclei': ['nuclei', '-version'],
            'katana': ['katana', '-version'],
            'ffuf': ['ffuf', '-V'],
            'gobuster': ['gobuster', 'version'],
            'wpscan': ['wpscan', '--version'],
            'nikto': ['nikto', '-Version'],
            'sqlmap': ['sqlmap', '--version'],
            'dalfox': ['dalfox', 'version'],
            'ghauri': ['ghauri', '--version'],
            'kxss': ['kxss', '--version'],
            'crlfuzz': ['crlfuzz', '--version']
        }
        
        try:
            if tool not in version_commands:
                return None
                
            cmd = version_commands[tool]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = ''
            if stdout:
                output += stdout.decode()
            if stderr:
                output += stderr.decode()
            
            if output:
                # Try to extract version using common patterns
                patterns = [
                    r'(?i)version\s*[:]?\s*v?(\d+\.\d+\.\d+)',
                    r'(?i)v?(\d+\.\d+\.\d+)',
                    r'(?i)(\d+\.\d+\.\d+(?:-\w+)?)',
                    r'(?i)(\d+\.\d+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, output)
                    if match:
                        return match.group(1)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting {tool} version: {e}")
            return None

async def check_tool_exists(tool_name: str, logger: Optional[logging.Logger] = None) -> bool:
    """Check if a tool is installed"""
    try:
        process = await asyncio.create_subprocess_exec(
            'which',
            tool_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    except Exception as e:
        if logger:
            logger.error(f"Error checking tool existence: {e}")
        return False

async def run_tool(cmd: str, **kwargs) -> bool:
    """Run a tool and return its success status"""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **kwargs
        )
        await process.communicate()
        return process.returncode == 0
    except Exception:
        return False