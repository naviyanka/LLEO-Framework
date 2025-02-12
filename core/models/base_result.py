from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class BaseResult:
    """Base class for all tool results"""
    tool: str
    raw_output: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration: float = 0.0 