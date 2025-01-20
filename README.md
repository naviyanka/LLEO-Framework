<h1 align="center">🦁 LLEO Framework</h1>
<p align="center">
  <img src="assets/banner.png" alt="LLEO Framework Banner" width="800">
</p>

<h3 align="center">Because manually running 30+ tools is so last season! 🎭</h3>

<p align="center">
  <a href="https://github.com/naviyanka/LLEO-Framework/stargazers">
    <img src="https://img.shields.io/github/stars/naviyanka/LLEO-Framework?style=flat-square" alt="Stars">
  </a>
  <a href="https://github.com/naviyanka/LLEO-Framework/network/members">
    <img src="https://img.shields.io/github/forks/naviyanka/LLEO-Framework?style=flat-square" alt="Forks">
  </a>
  <a href="https://github.com/naviyanka/LLEO-Framework/issues">
    <img src="https://img.shields.io/github/issues/naviyanka/LLEO-Framework?style=flat-square" alt="Issues">
  </a>
  <a href="https://github.com/naviyanka/LLEO-Framework/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/naviyanka/LLEO-Framework?style=flat-square" alt="License">
  </a>
</p>

## 🎯 Overview

Ever felt like you're juggling chainsaws while performing recon? Say hello to LLEO - a name we pulled out of a hat because, let's face it, coming up with meaningful acronyms is harder than finding P1 bugs! 

Some say LLEO stands for "Live Linux Enumeration & Observation", others think it's "Lazy Lion Eating Oreos", and a few believe it's just what happens when you fall asleep on your keyboard while typing "HELLO". We'll let you pick your favorite explanation! 🦁

Think of LLEO as that incredibly organized friend who somehow manages to keep track of everything while you're still trying to remember where you put your coffee (and what LLEO actually stands for). ☕


## ✨ Features (or as we like to call them, "Happy Accidents")

- **🏗️ Modular Architecture**: Like LEGO for hackers! Add your own tools, break things creatively, 
  and blame it on "modular design" when something goes wrong

- **🔍 Comprehensive Scanning**: From finding subdomains you didn't know existed to discovering 
  vulnerabilities your client wishes didn't exist. We scan everything except your browser history!

- **🚦 Smart Rate Limiting**: Because getting IP-banned is so 2022. We keep your tools on a 
  digital leash tighter than your project deadlines

- **⚡ Parallel Execution**: Runs multiple tools faster than you can say "why is my CPU fan 
  screaming?" Multi-threading so good, your computer might start questioning its life choices

- **🧩 Result Correlation**: Combines tool outputs like a matchmaker on steroids. Finally, 
  your reconnaissance tools can stop ghosting each other and start sharing results

- **🎛️ Configurable Workflow**: Customize everything! It's like your favorite coffee order - 
  complex, precise, and slightly concerning to others

Bonus Feature: Works 60% of the time, every time! 😉


## 🛠️ Modules (or "Ways to Make Security Teams Panic")

### 1. 🔍 Discovery Module (AKA "Finding Things People Tried to Hide")
- Subdomain enumeration (Because developers think *.dev.* is sneaky)
- Technology detection (Exposing your client's WordPress from 2012)
- WAF identification (Playing "Guess Who?" with security appliances)
- Email harvesting (Finding whose inbox to flood with bug reports)
- Asset discovery (Like treasure hunting, but for forgotten dev servers)
- Historical data collection (Because everyone forgets to clean up git commits)

### 2. 🌐 DNS Analysis Module (The "DNS and Drive Me Crazy" Suite)
- DNS record enumeration (Reading DNS records like tea leaves)
- Zone transfer attempts (The "Pretty Please?" approach to DNS)
- Wildcard detection (Finding the lazy admin's * entries)
- Subdomain bruteforcing (Making DNS resolvers question their existence)
- DNS security checks (Finding out who skipped the security meeting)

### 3. 🎯 Web Fuzzing Module (The "Let's Break Things" Department)
- Directory bruteforcing (Finding /admin faster than actual admins)
- Parameter discovery (Because ?debug=true is always worth a try)
- Virtual host discovery (Playing hide and seek with web servers)
- Custom wordlist support (For when rockyou.txt isn't enough)
- Smart fuzzing strategies (Smarter than your average pentester)

### 4. 🔬 Web Probing Module (The "Digital Stalker" Suite)
- Service identification (Playing "Name That Port!")
- Screenshot capture (For when reports need pretty pictures)
- Technology fingerprinting (Exposing your tech stack's dirty laundry)
- Status code analysis (Finding all those juicy 403s)
- Response analysis (Reading between the lines of your HTTP headers)

### 5. 🎪 Vulnerability Scan Module (The "Make DevOps Cry" Collection)
- Common vulnerability checks (Finding bugs older than your interns)
- CMS scanning (WordPress sites, we're looking at you)
- SSL/TLS analysis (Hunting for certificates older than Bitcoin)
- Injection testing (SQLi: Because input validation is overrated)
- Security misconfigurations (Finding out who copy-pasted from StackOverflow)


## 🔧 Installation (The "Trust Me, It Works" Guide)

Clone the repo (and pray it works)
git clone https://github.com/naviyanka/LLEO-Framework.git
cd LLEO-Framework # Point of no return
Install dependencies and surrender your system to the security gods
sudo python3 install.py # Watch your CPU have an existential crisis


## 📋 Requirements (Things You'll Probably Need to Update)

- Python 3.8+ (Because we're too lazy to support legacy versions)
- Go 1.16+ (Yes, we're making you install Go. Deal with it.)
- Ruby 2.7+ (For that one tool we might use someday)
- Linux/Unix-based OS (Windows users, we'll pray for you 🙏)
- A sense of humor (Critical dependency)
- Patience (Lots of it)
- Coffee ☕ (Non-negotiable)


## 🚦 Usage (Or "How to Pretend You Know What You're Doing")

### Basic Usage (For Normal People):


./lleo.py -d example.com   # Sit back and question your life choices

### Advanced Usage (For People Who Read Documentation):

./lleo.py -d example.com -v -o output_dir --exclude exclude.txt   # Unleash chaos with style


### Command Line Arguments (The "What Does This Button Do?" Section)

| Argument | What It Actually Does |
|----------|----------------------|
| -d, --domain | Your target (who hurt you?) |
| -v, --verbose | For when you want to see EVERYTHING (and regret it) |
| -o, --output | Where to dump the chaos (default: output) |
| --exclude | The domains your client begged you not to scan |
| --config | For people who don't trust our defaults |
| -s, --silent | Ninja mode (or "I don't want to see the errors") |


### Hidden Features:
- Automatic coffee maker (coming soon™)
- Bug bounty auto-submitter (in your dreams)
- Excuse generator for when things break
- CPU temperature monitoring (just kidding, we'll max it out anyway)


## 🛠️ Integrated Tools & Functions

### Subdomain Enumeration Tools
| Tool | Description | Function |
|------|-------------|----------|
| [Subfinder](https://github.com/projectdiscovery/subfinder) | Fast passive subdomain discovery tool | Uses various public APIs and sources to find subdomains |
| [Amass](https://github.com/OWASP/Amass) | In-depth Attack Surface Mapping and Asset Discovery | Performs network mapping of attack surfaces and external asset discovery |
| [Findomain](https://github.com/Findomain/Findomain) | Cross-platform subdomain enumerator | Uses multiple sources including certificate transparency logs |
| [Assetfinder](https://github.com/tomnomnom/assetfinder) | Domain reconnaissance tool | Finds domains and subdomains related to a given domain |
| [Haktrails](https://github.com/hakluke/haktrails) | SecurityTrails API client | Queries SecurityTrails API for historical and current domain data |

### Content Discovery Tools
| Tool | Description | Function |
|------|-------------|----------|
| [Dirsearch](https://github.com/maurosoria/dirsearch) | Web path scanner | Brute forces directories and files in websites |
| [Gobuster](https://github.com/OJ/gobuster) | Directory/File, DNS and VHost busting tool | Multi-threaded tool to brute force URIs, DNS subdomains and virtual host names |
| [Ffuf](https://github.com/ffuf/ffuf) | Fast web fuzzer | Identifies hidden elements, directories, subdomains, and parameters |
| [Wfuzz](https://github.com/xmendez/wfuzz) | Web application fuzzer | Brute forces web applications to find resources not linked directly |
| [Katana](https://github.com/projectdiscovery/katana) | Crawling and spidering framework | Advanced crawler to automatically discover endpoints and assets |

### DNS Analysis Tools
| Tool | Description | Function |
|------|-------------|----------|
| [DNSx](https://github.com/projectdiscovery/dnsx) | Fast and multi-purpose DNS toolkit | Performs multiple DNS queries and validates results |
| [AltDNS](https://github.com/infosec-au/altdns) | Subdomain discovery through alterations | Generates permutations of subdomains and validates them |
| [DNSGen](https://github.com/ProjectAnte/dnsgen) | Domain list generator | Creates domain permutations for brute forcing |
| [MassDNS](https://github.com/blechschmidt/massdns) | High-performance DNS stub resolver | Performs parallel DNS resolutions |

### Web Technology Detection
| Tool | Description | Function |
|------|-------------|----------|
| [WhatWeb](https://github.com/urbanadventurer/WhatWeb) | Next generation web scanner | Identifies web technologies, CMS, blogging platforms, analytics packages, etc. |
| [Wappalyzer](https://github.com/wappalyzer/wappalyzer) | Technology profiler | Uncovers technologies used on websites |
| [Aquatone](https://github.com/michenriksen/aquatone) | Visual inspection tool | Takes screenshots of websites and generates visual reports |
| [Wafw00f](https://github.com/EnableSecurity/wafw00f) | Web Application Firewall fingerprinting tool | Identifies and fingerprints Web Application Firewall products |

### Vulnerability Scanners
| Tool | Description | Function |
|------|-------------|----------|
| [Nuclei](https://github.com/projectdiscovery/nuclei) | Fast and customizable vulnerability scanner | Scans for security vulnerabilities using templates |
| [WPScan](https://github.com/wpscanteam/wpscan) | WordPress security scanner | Identifies security issues in WordPress sites and their plugins |
| [Nikto](https://github.com/sullo/nikto) | Web server scanner | Performs comprehensive tests against web servers |
| [SQLMap](https://github.com/sqlmapproject/sqlmap) | Automatic SQL injection tool | Detects and exploits SQL injection vulnerabilities |
| [Metasploit](https://github.com/rapid7/metasploit-framework) | Penetration testing framework | Provides vulnerability verification and exploitation capabilities |

### Special Purpose Tools
| Tool | Description | Function |
|------|-------------|----------|
| [Dalfox](https://github.com/hahwul/dalfox) | Parameter Analysis and XSS Scanner | Finds XSS vulnerabilities in web applications |
| [CRLFuzz](https://github.com/dwisiswant0/crlfuzz) | Fast CRLF injection scanner | Detects CRLF injection vulnerabilities |
| [Ghauri](https://github.com/r0oth3x49/ghauri) | SQL injection detector and crawler | Automatically detects and validates SQL injection points |
| [GauPlus](https://github.com/bp0lr/gauplus) | Fetch known URLs | Fetches known URLs from AlienVault's Open Threat Exchange |
| [Waybackurls](https://github.com/tomnomnom/waybackurls) | Fetch URLs from Wayback Machine | Retrieves historical URL data from the Internet Archive |
| [KXSS](https://github.com/Emoe/kxss) | Advanced XSS scanner | Finds blind XSS vulnerabilities |

### Web Probing Tools
| Tool | Description | Function |
|------|-------------|----------|
| [HTTPx](https://github.com/projectdiscovery/httpx) | Fast HTTP probe | Checks for valid HTTP/HTTPS services |
| [403-Bypass](https://github.com/iamj0ker/bypass-403) | Authentication bypass tool | Tests various bypass techniques for 403 Forbidden responses |
| [Naabu](https://github.com/projectdiscovery/naabu) | Port scanning tool | Fast port scanner written in Go |
| [Gospider](https://github.com/jaeles-project/gospider) | Fast web spider | Crawls websites and extracts endpoints, subdomains, and URLs |

### Reporting Tools
| Tool | Description | Function |
|------|-------------|----------|
| [SpiderFoot](https://github.com/smicallef/spiderfoot) | OSINT automation tool | Gathers intelligence about targets |
| [Nmap](https://github.com/nmap/nmap) | Network mapper | Performs comprehensive network scanning and service detection |


## 🙏 The Hall of Fame (or "People Who Made LLEO Less Useless")

Let's be honest - without these legendary humans, LLEO would just be a fancy terminal screensaver. Time to give credit where credit is due (and maybe beg for GitHub stars)!


### 🎭 The Cast of Characters

#### 🚀 ProjectDiscovery Team (The "We Write Everything in Go" Squad)
These folks wake up and choose ~~violence~~ productivity:
- [Subfinder](https://github.com/projectdiscovery/subfinder) - @pdiscoveryio (Finding subdomains like your ex finding reasons to text)
- [Nuclei](https://github.com/projectdiscovery/nuclei) - @pdiscoveryio (The template king that makes vulnerability scanners jealous)
- [HTTPx](https://github.com/projectdiscovery/httpx) - @pdiscoveryio (Because regular HTTP clients weren't fancy enough)
- [DNSx](https://github.com/projectdiscovery/dnsx) - @pdiscoveryio (DNS resolution at speed of "why is my CPU melting?")
- [Naabu](https://github.com/projectdiscovery/naabu) - @pdiscoveryio (Port scanning with attitude)
- [Katana](https://github.com/projectdiscovery/katana) - @pdiscoveryio (Slicing web apps and dev's expectations)

#### 🦸‍♂️ Solo Superheroes (The "I Made This Instead of Sleeping" Club)
- [Amass](https://github.com/OWASP/Amass) - Jeff Foley (@caffix) - Making your RAM question its life choices
- [Findomain](https://github.com/Findomain/Findomain) - Eduard Tolosa (@edu4rdshl) - The domain whisperer
- [Assetfinder](https://github.com/tomnomnom/assetfinder) - Tom Hudson (@tomnomnom) - Finding assets faster than developers can hide them
- [SQLMap](https://github.com/sqlmapproject/sqlmap) - Bernardo & Miroslav - Making DBAs cry since 2006
- [Metasploit](https://github.com/rapid7/metasploit-framework) - Rapid7 & Community - The OG "I know what I'm doing" framework


### ⚠️ Disclaimer (The "Please Don't Sue Us" Section)
If we forgot to credit you, blame it on:
- Sleep deprivation (72 hours and counting!)
- Energy drink overdose
- The fact that we're still trying to pronounce "LLEO"
- Mercury being in retrograde
- Our last brain cell going on vacation


### 🤝 How to Support These Legends (Because They Need More Than Just Thoughts and Prayers)
- ⭐ Star their repos (Cheaper than therapy, more effective than LinkedIn endorsements)
- 🐛 Report bugs (Not the ones you're saving for your next bug bounty)
- 💻 Contribute code (We all know you'll just fork and forget)
- 🎓 Share knowledge (Except those juicy zero-days, we see you 👀)
- ☕ Buy them coffee (Or whatever keeps them debugging at 3 AM)
- 🍕 Send pizza (Because code runs on carbs)


### 🎪 The Brutal Truth
We're just the cover band playing security tools' greatest hits. Think of us as the "Now That's What I Call Hacking!" compilation album.

Remember: Behind every security tool is:
- A developer questioning their life choices
- A broken regex that somehow works
- 47 StackOverflow tabs
- An energy drink addiction
- A GitHub repo full of "TODO: Fix later" comments

*P.S. Several CPUs were mildly traumatized during development. We're sending them to therapy.*


## 🤝 Contributing (The "Make It Better or Break It Trying" Section)
Contributions are welcome! Just:
1. Read our guidelines (We know you won't)
2. Fork the repo (The easy part)
3. Make changes (The fun part)
4. Submit PR (The scary part)
5. Wait for review (The eternal part)


## 📝 License (The Legal Stuff™)
MIT License - Because we're too lazy to write our own and it sounds professional.
TL;DR: Do whatever you want, just don't blame us when things go wrong.

## ⚠️ The "Cover Your Assets" Disclaimer
LLEO Framework is for:
- Security research ✅
- Bug bounty hunting ✅
- Making your CPU feel alive ✅

Not for:
- Testing your ex's website ❌
- "Just checking" your competitor's security ❌
- Explaining to the FBI why you're scanning .gov domains ❌


## 📞 Contact (If You Must)
- Twitter: [@naviyanka](https://twitter.com/naviyanka) (For professional rants)
- Email: naviyanka@gmail.com (For formal complaints)
- Blog: https://naviyanka.github.io (Where we pretend to be organized)
- Carrier pigeon: Available upon request

---
<p align="center">Made with ❤️, 🍕, and questionable amounts of caffeine for the Bug Bounty Community</p>
<p align="center">No developers were harmed in the making of this framework*</p>
<p align="center"><small>*Results may vary</small></p>