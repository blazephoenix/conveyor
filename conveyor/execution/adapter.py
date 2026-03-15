from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from conveyor.tracking.models import AgentResult


class ClaudeCodeAdapter:
    def __init__(self, permission_mode: str = "bypassPermissions"):
        self.permission_mode = permission_mode

    def execute(self, prompt: str, workdir: str, timeout: int = 300) -> AgentResult:
        start = time.monotonic()
        try:
            result = subprocess.run(
                [
                    "claude", "--print", "-p", prompt,
                    "--permission-mode", self.permission_mode,
                ],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = time.monotonic() - start
            return AgentResult(
                output=result.stdout,
                exit_code=result.returncode,
                duration_seconds=duration,
            )
        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            return AgentResult(
                output=f"Timeout after {timeout}s",
                exit_code=1,
                duration_seconds=duration,
            )
        except FileNotFoundError:
            duration = time.monotonic() - start
            return AgentResult(
                output="Claude Code CLI not found. Is it installed?",
                exit_code=1,
                duration_seconds=duration,
            )
