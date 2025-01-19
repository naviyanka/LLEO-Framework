import os
import subprocess
import logging
from pathlib import Path

class ToolChecker:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('LLEO')
        self.go_paths = [
            os.path.expanduser('~/go/bin'),
            '/usr/local/go/bin',
            '/usr/local/bin',
            '/usr/bin'
        ]
        
        # Tool aliases mapping
        self.tool_aliases = {
            'metasploit': ['msfconsole', 'msfvenom'],
            'gauplus': ['gau'],
            'waybackurls': ['waybackurls'],
            'katana': ['katana'],
            'spiderfoot': ['spiderfoot'],
        }

    def check_tool(self, tool_name):
        """Check if a tool is installed and get its path"""
        try:
            # Get all possible names for the tool
            tool_names = [tool_name]
            if tool_name in self.tool_aliases:
                tool_names.extend(self.tool_aliases[tool_name])
            
            # Check each possible name
            for name in tool_names:
                # Check common locations
                tool_paths = [Path(p) / name for p in self.go_paths]
                
                # Check if tool exists in any path
                for path in tool_paths:
                    if path.exists() and os.access(path, os.X_OK):
                        self.logger.debug(f"Found {tool_name} ({name}) at {path}")
                        return True, str(path)
                
                # Try which command as fallback
                try:
                    result = subprocess.run(
                        ['which', name],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    path = result.stdout.strip()
                    self.logger.debug(f"Found {tool_name} ({name}) using which at {path}")
                    return True, path
                except subprocess.CalledProcessError:
                    continue
            
            return False, None
            
        except Exception as e:
            self.logger.error(f"Error checking tool {tool_name}: {str(e)}")
            return False, None

    def install_missing_tools(self, missing_tools):
        """Install missing tools"""
        for tool in missing_tools:
            try:
                self.logger.info(f"Installing {tool}...")
                
                if tool == 'metasploit':
                    cmd = 'apt-get install -y metasploit-framework'
                elif tool == 'waybackurls':
                    cmd = 'go install -v github.com/tomnomnom/waybackurls@latest'
                elif tool == 'gauplus':
                    cmd = 'go install -v github.com/lc/gau/v2/cmd/gau@latest'
                elif tool == 'kxss':
                    cmd = 'go install -v github.com/Emoe/kxss@latest'
                elif tool == 'katana':
                    cmd = 'go install -v github.com/projectdiscovery/katana/cmd/katana@latest'
                elif tool == 'crlfuzz':
                    cmd = 'go install -v github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest'
                else:
                    self.logger.error(f"No installation method defined for {tool}")
                    continue
                
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self.logger.info(f"Successfully installed {tool}")
                else:
                    self.logger.error(f"Failed to install {tool}: {result.stderr}")
                    
            except Exception as e:
                self.logger.error(f"Error installing {tool}: {str(e)}") 