from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_result import BaseResult

@dataclass
class DNSResult(BaseResult):
    """Result from DNS analysis tools"""
    records: List[Dict[str, Any]] = field(default_factory=list)
    success_rate: float = 0.0 