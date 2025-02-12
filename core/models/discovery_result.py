from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from .base_result import BaseResult

@dataclass
class DiscoveryResult(BaseResult):
    """Result from discovery tools"""
    subdomains: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list) 