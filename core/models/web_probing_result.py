from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass
class WebProbingResult:
    """Result from web probing tools"""
    tool: str
    raw_output: Optional[str] = None
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    technologies: List[Dict[str, Any]] = field(default_factory=list)
    headers: Dict[str, Any] = field(default_factory=dict)
    status_codes: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration: float = 0.0 