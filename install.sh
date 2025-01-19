#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Paths
TOOLS_DIR="$HOME/.lleo/tools"
VENV_DIR="$HOME/.lleo/venv"
LOG_FILE="$HOME/.lleo/install.log"

# Banner
print_banner() {
    echo -e "${BLUE}"
    cat << "EOF"
    ██╗     ██╗     ███████╗ ██████╗ 
    ██║     ██║     ██╔════╝██╔═══██╗
    ██║     ██║     █████╗  ██║   ██║
    ██║     ██║     ██╔══╝  ██║   ██║
    ███████╗███████╗███████╗╚██████╔╝
    ╚══════╝╚══════╝╚══════╝ ╚═════╝ 
                              
Comprehensive Security Reconnaissance Suite For Bug Bounty
EOF
    echo -e "${NC}"
}

# Error logging
log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Setup virtual environment
setup_venv() {
    echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
    python3 -m venv "$VENV_DIR" 2>/dev/null || {
        log_error "Failed to create virtual environment"
        echo -e "${RED}Failed to create virtual environment. See $LOG_FILE for details${NC}"
        exit 1
    }
    source "$VENV_DIR/bin/activate"
}

# Required tools with installation methods
declare -A tools=(
    # Discovery Tools
    ["subfinder"]="go:projectdiscovery/subfinder"
    ["amass"]="snap:OWASP/Amass"
    ["assetfinder"]="go:tomnomnom/assetfinder"
    ["findomain"]="binary:findomain/findomain"
    ["waybackurls"]="go:tomnomnom/waybackurls"
    ["gauplus"]="go:bp0lr/gauplus"
    ["gospider"]="go:jaeles-project/gospider"
    ["haktrails"]="go:hakluke/haktrails"
    ["whatweb"]="git:urbanadventurer/WhatWeb"
    ["spiderfoot"]="git:smicallef/spiderfoot"
    ["wafw00f"]="git:EnableSecurity/wafw00f"

    # DNS Analysis Tools
    ["dnsx"]="go:projectdiscovery/dnsx"
    ["altdns"]="pip:altdns"
    ["dnsgen"]="pip:dnsgen"

    # Web Probing Tools
    ["httpx"]="go:projectdiscovery/httpx"
    ["aquatone"]="binary:michenriksen/aquatone"
    ["nmap"]="apt:nmap"
    ["naabu"]="go:projectdiscovery/naabu"
    ["403-bypass"]="git:Dheerajmadhukar/4-ZERO-3"

    # Web Fuzzing Tools
    ["dirsearch"]="git:maurosoria/dirsearch"
    ["gobuster"]="go:OJ/gobuster"
    ["ffuf"]="go:ffuf/ffuf"
    ["wfuzz"]="pip:wfuzz"
    ["katana"]="go:projectdiscovery/katana"

    # Vulnerability Scanning Tools
    ["nuclei"]="go:projectdiscovery/nuclei"
    ["wpscan"]="gem:wpscan"
    ["nikto"]="apt:nikto"
    ["sqlmap"]="git:sqlmapproject/sqlmap"
    ["dalfox"]="go:hahwul/dalfox"
    ["ghauri"]="git:r0oth3x49/ghauri"
    ["metasploit"]="custom:metasploit"
    ["kxss"]="go:tomnomnom/kxss"
    ["crlfuzz"]="go:dwisiswant0/crlfuzz"
)

# Python packages
python_packages=(
    "colorama"
    "python-nmap"
    "pyyaml"
)

# Main installation
main() {
    print_banner
    
    # Create directories
    mkdir -p "$TOOLS_DIR" "$HOME/.lleo/logs"
    
    # Setup Python environment
    if [ ! -d "$VENV_DIR" ]; then
        setup_venv
    else
        source "$VENV_DIR/bin/activate"
    fi
    
    # Install Python packages quietly
    echo -e "${YELLOW}Installing Python packages...${NC}"
    pip install -q --upgrade pip
    pip install -q ${python_packages[@]} 2>"$LOG_FILE"
    
    # Show status of all tools
    echo -e "\n${YELLOW}Checking tools status:${NC}"
    echo -e "\n${GREEN}Installed tools:${NC}"
    installed_count=0
    missing_tools=()
    
    for tool in "${!tools[@]}"; do
        if check_tool "$tool"; then
            echo -e "${GREEN}✓${NC} $tool"
            ((installed_count++))
        else
            missing_tools+=("$tool")
        fi
    done
    
    if [ $installed_count -eq 0 ]; then
        echo "None"
    fi
    
    echo -e "\n${RED}Missing tools:${NC}"
    if [ ${#missing_tools[@]} -eq 0 ]; then
        echo "None"
    else
        printf '%s\n' "${missing_tools[@]}"
    fi
    
    # Ask once for all missing tools
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo -e "\n${YELLOW}The following tools are missing:${NC}"
        printf '%s\n' "${missing_tools[@]}"
        read -p "Do you want to install these tools? [Y/n] " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            for tool in "${missing_tools[@]}"; do
                install_tool "$tool" &
            done
            wait
        fi
    fi
    
    echo -e "\n${GREEN}Installation completed!${NC}"
    echo -e "${YELLOW}Please configure your API keys in config/config.yaml${NC}"
    
    if [ -s "$LOG_FILE" ]; then
        echo -e "${YELLOW}Some errors occurred during installation. Check $LOG_FILE for details${NC}"
    fi
}

install_tool() {
    local tool=$1
    local tool_info=${tools[$tool]}
    local install_type=${tool_info%%:*}
    local repo=${tool_info#*:}
    
    echo -e "${YELLOW}Installing $tool...${NC}"
    
    case $install_type in
        "go")
            go install "github.com/$repo@latest" &>/dev/null || {
                log_error "Failed to install $tool"
                return 1
            }
            ;;
        "snap")
            snap install "$tool" &>/dev/null || {
                log_error "Failed to install $tool"
                return 1
            }
            ;;
        "binary")
            install_binary "$tool" "$repo" || {
                log_error "Failed to install $tool"
                return 1
            }
            ;;
        "pip")
            pip install -q "$tool" 2>/dev/null || {
                log_error "Failed to install $tool"
                return 1
            }
            ;;
        "gem")
            gem install -q "$tool" 2>/dev/null || {
                log_error "Failed to install $tool"
                return 1
            }
            ;;
        "apt")
            apt-get install -qq -y "$tool" 2>/dev/null || {
                log_error "Failed to install $tool"
                return 1
            }
            ;;
        "git")
            install_from_source "$tool" "$repo" || {
                log_error "Failed to install $tool"
                return 1
            }
            ;;
        "custom")
            if [ "$tool" = "metasploit" ]; then
                install_metasploit || {
                    log_error "Failed to install metasploit"
                    return 1
                }
            fi
            ;;
        *)
            install_from_source "$tool" "$repo" || {
                log_error "Failed to install $tool"
                return 1
            }
            ;;
    esac
    
    if check_tool "$tool"; then
        echo -e "${GREEN}✓${NC} $tool"
    else
        echo -e "${RED}✗${NC} $tool"
    fi
}

install_binary() {
    local tool=$1
    local repo=$2
    
    cd "$TOOLS_DIR" &>/dev/null
    curl -sLO "https://github.com/$repo/releases/latest/download/$tool-linux" || return 1
    chmod +x "$tool-linux"
    mv "$tool-linux" "/usr/local/bin/$tool"
}

install_from_source() {
    local tool=$1
    local repo=$2
    
    cd "$TOOLS_DIR" &>/dev/null
    # Special handling for 403-bypass
    if [ "$tool" = "403-bypass" ]; then
        if [ -d "$tool" ]; then
            rm -rf "$tool"
        fi
        git clone -q "https://github.com/$repo" "$tool" || return 1
        cd "$tool" &>/dev/null
        chmod +x 403-bypass.sh
        ln -sf "$(pwd)/403-bypass.sh" "/usr/local/bin/403-bypass"
        return 0
    fi
    
    # Default handling for other tools
    git clone -q "https://github.com/$repo" "$tool" || return 1
    cd "$tool" &>/dev/null
    
    if [ -f "setup.py" ]; then
        python3 setup.py install -q || return 1
    elif [ -f "Makefile" ]; then
        make -s && make install -s || return 1
    else
        go build -o "$tool" &>/dev/null && \
        ln -sf "$(pwd)/$tool" "/usr/local/bin/$tool" || return 1
    fi
}

# Add new custom installation function for metasploit
install_metasploit() {
    echo -e "${YELLOW}Installing Metasploit Framework...${NC}"
    # First try using package manager
    if command -v apt-get &>/dev/null; then
        apt-get update -qq
        apt-get install -qq -y metasploit-framework && return 0
    fi
    
    # If package manager fails, use the official installer
    echo -e "${YELLOW}Package manager installation failed, using official installer...${NC}"
    cd "$TOOLS_DIR" &>/dev/null
    curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall
    chmod +x msfinstall
    ./msfinstall
}

# Update tool check function
check_tool() {
    local tool=$1
    if [ "$tool" = "metasploit" ]; then
        command -v msfconsole &>/dev/null
        return $?
    fi
    command -v "$tool" &>/dev/null
}

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root${NC}"
    exit 1
fi

# Run main installation
main 