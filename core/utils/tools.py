from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import asyncio
import logging
from dataclasses import dataclass
import json
from .rate_limiter import RateLimiter

@dataclass
class ToolResult:
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    runtime: Optional[float] = None
    exit_code: Optional[int] = None

class ToolExecutor:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('ToolExecutor')
        self.rate_limiter = RateLimiter()

    async def run_tool(
        self,
        cmd: Union[str, List[str]],
        output_file: Optional[Path] = None,
        input_data: Optional[str] = None,
        timeout: Optional[int] = None,
        shell: bool = False
    ) -> ToolResult:
        """Run an external tool safely and handle its output"""
        try:
            async with self.rate_limiter:
                if isinstance(cmd, list):
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                else:
                    if not shell:
                        self.logger.warning("Converting string command to shell=True")
                        shell = True
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(input_data.encode() if input_data else None),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return ToolResult(
                        success=False,
                        error="Command timed out",
                        exit_code=-1
                    )

                if output_file and stdout:
                    try:
                        output_file = Path(output_file)
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        output_file.write_bytes(stdout)
                    except Exception as e:
                        self.logger.error(f"Error writing output to file: {e}")

                return ToolResult(
                    success=process.returncode == 0,
                    output=stdout.decode() if stdout else None,
                    error=stderr.decode() if stderr else None,
                    exit_code=process.returncode
                )

        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                exit_code=-1
            )

    async def check_tool_exists(self, tool_name: str) -> bool:
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
            self.logger.error(f"Error checking tool existence: {e}")
            return False

    async def run_with_retry(
        self,
        cmd: Union[str, List[str]],
        max_retries: int = 3,
        retry_delay: int = 5,
        **kwargs
    ) -> ToolResult:
        """Run a tool with retry logic"""
        for attempt in range(max_retries):
            result = await self.run_tool(cmd, **kwargs)
            if result.success:
                return result
            if attempt < max_retries - 1:
                self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
        return result