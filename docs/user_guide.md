# LLEO Framework User Guide

## Installation

### Prerequisites
- Python 3.8+
- Go 1.16+
- Git

### Quick Start
```bash
# Clone repository
git clone https://github.com/naviyanka/LLEO-Framework.git
cd LLEO-Framework

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install required tools
python install.py
```

## Basic Usage

### Command Line Interface
```bash
# Basic scan
python lleo.py -d example.com

# Verbose output
python lleo.py -d example.com -v

# Save output to specific directory
python lleo.py -d example.com -o /path/to/output

# Exclude specific subdomains
python lleo.py -d example.com --exclude exclude.txt
```

### Configuration

#### API Keys
Add your API keys to `.env` file:
```env
SECURITYTRAILS_KEY=your_key_here
SHODAN_KEY=your_key_here
CENSYS_KEY=your_key_here
```

#### Tool Configuration
Edit `config/config.yml`:
```yaml
tools:
	threads: 10
	rate_limit: 150
	timeout: 30
	
wordlists:
	dns: /path/to/dns/wordlist.txt
	content: /path/to/content/wordlist.txt
```

## Module Usage

### Discovery Module
```bash
# Run only discovery
python lleo.py -d example.com --module discovery

# Custom wordlist
python lleo.py -d example.com --wordlist custom_words.txt
```

### DNS Analysis
```bash
# Run DNS analysis
python lleo.py -d example.com --module dns_analysis

# Custom resolvers
python lleo.py -d example.com --resolvers resolvers.txt
```

### Web Fuzzing
```bash
# Run web fuzzing
python lleo.py -d example.com --module web_fuzzing

# Custom parameters
python lleo.py -d example.com --params params.txt
```

### Vulnerability Scanning
```bash
# Run vulnerability scan
python lleo.py -d example.com --module vuln_scan

# Custom templates
python lleo.py -d example.com --templates custom_templates/
```

## Output Management

### Results Structure
```
output/
├── example.com/
│   ├── discovery/
│   │   ├── raw/
│   │   └── processed/
│   ├── dns_analysis/
│   ├── web_fuzzing/
│   └── vulnerability_scan/
```

### Report Formats
- JSON (default)
- HTML report
- CSV export
- Markdown summary

## Resource Management

### Memory Usage
- Set maximum memory usage in config
- Monitor resource consumption
- Automatic cleanup

### Rate Limiting
- Configure per-tool limits
- Global rate limiting
- Burst handling

## Troubleshooting

### Common Issues
1. Tool Installation
	 ```bash
	 # Verify tool installation
	 python lleo.py --check-tools
	 
	 # Reinstall tools
	 python install.py --force
	 ```

2. Permission Issues
	 ```bash
	 # Check tool permissions
	 python lleo.py --fix-permissions
	 ```

3. Resource Issues
	 ```bash
	 # Check resource usage
	 python lleo.py --check-resources
	 ```

### Debug Mode
```bash
# Enable debug output
python lleo.py -d example.com --debug

# Save debug logs
python lleo.py -d example.com --debug --log-file debug.log
```

## Best Practices

### Scanning
1. Start with small scope
2. Use appropriate rate limits
3. Monitor resource usage
4. Save results regularly

### Configuration
1. Use secure API storage
2. Configure tool timeouts
3. Set appropriate threads
4. Use custom wordlists

### Output Management
1. Regular backups
2. Clean old results
3. Monitor disk usage
4. Export important findings

## Advanced Usage

### Custom Modules
```python
from core.modules.base import BaseModule

class CustomModule(BaseModule):
		async def run(self):
				# Implementation
```

### API Integration
```python
from lleo import Framework

framework = Framework()
results = await framework.run_scan("example.com")
```

### Automation
```python
# Batch scanning
python lleo.py --batch domains.txt

# Continuous monitoring
python lleo.py --monitor example.com --interval 24h
```

## Security Considerations

### Rate Limiting
- Respect target limits
- Use appropriate delays
- Monitor response codes

### Authentication
- Secure API keys
- Rotate credentials
- Monitor usage

### Output Security
- Secure storage
- Clean sensitive data
- Regular cleanup