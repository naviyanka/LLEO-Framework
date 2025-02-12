import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import asyncio
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console
import json

class AsyncRotatingFileHandler(RotatingFileHandler):
    """Async-compatible rotating file handler"""
    async def aemit(self, record):
        try:
            await asyncio.to_thread(self.emit, record)
        except Exception:
            self.handleError(record)

class Logger:
    def __init__(self, name: str = "LLEO", log_dir: Optional[Path] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create formatters
        console_formatter = logging.Formatter(
            '%(asctime)s %(levelname)-8s %(message)s',
            datefmt='[%y/%m/%d %H:%M:%S]'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if log_dir is provided)
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_dir / "lleo.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def addHandler(self, handler: logging.Handler) -> None:
        """Add a new handler to the logger"""
        self.logger.addHandler(handler)
    
    def removeHandler(self, handler: logging.Handler) -> None:
        """Remove a handler from the logger"""
        self.logger.removeHandler(handler)
    
    def debug(self, msg: str) -> None:
        """Log debug message"""
        self.logger.debug(msg)
    
    def info(self, msg: str) -> None:
        """Log info message"""
        self.logger.info(msg)
    
    def warning(self, msg: str) -> None:
        """Log warning message"""
        self.logger.warning(msg)
    
    def error(self, msg: str) -> None:
        """Log error message"""
        self.logger.error(msg)
    
    def critical(self, msg: str) -> None:
        """Log critical message"""
        self.logger.critical(msg)
    
    def setLevel(self, level: int) -> None:
        """Set logger level"""
        self.logger.setLevel(level)
    
    def getLogger(self) -> logging.Logger:
        """Get the underlying logger instance"""
        return self.logger

    def _setup_console_handler(self, verbose: bool, no_color: bool) -> None:
        """Setup console handler with rich output"""
        console = Console(color_system=None if no_color else 'auto')
        console_handler = RichHandler(
            console=console,
            show_path=verbose,
            enable_link_path=verbose,
            markup=True
        )
        console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
        self.logger.addHandler(console_handler)

    def _setup_file_handler(self) -> None:
        """Setup rotating file handler for all logs"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        file_handler = AsyncRotatingFileHandler(
            filename=log_dir / f'lleo_{datetime.now():%Y%m%d}.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    async def alog(self, level: int, msg: str, *args, **kwargs) -> None:
        """Async logging method"""
        if self.logger.isEnabledFor(level):
            record = self.logger.makeRecord(
                self.logger.name, level, "(unknown file)", 0, msg, args, None
            )
            for handler in self.logger.handlers:
                if isinstance(handler, AsyncRotatingFileHandler):
                    await handler.aemit(record)
                else:
                    handler.emit(record)

    async def adebug(self, msg: str, *args, **kwargs) -> None:
        """Async debug logging"""
        await self.alog(logging.DEBUG, msg, *args, **kwargs)

    async def ainfo(self, msg: str, *args, **kwargs) -> None:
        """Async info logging"""
        await self.alog(logging.INFO, msg, *args, **kwargs)

    async def awarning(self, msg: str, *args, **kwargs) -> None:
        """Async warning logging"""
        await self.alog(logging.WARNING, msg, *args, **kwargs)

    async def aerror(self, msg: str, *args, **kwargs) -> None:
        """Async error logging"""
        await self.alog(logging.ERROR, msg, *args, **kwargs)

    async def acritical(self, msg: str, *args, **kwargs) -> None:
        """Async critical logging"""
        await self.alog(logging.CRITICAL, msg, *args, **kwargs)

    def log_dict(self, data: dict, level: str = 'info') -> None:
        """Log dictionary data with proper formatting"""
        log_func = getattr(self.logger, level.lower())
        log_func(json.dumps(data, indent=2))