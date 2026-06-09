"""Safe async subprocess executor for perf commands.

This module provides the security boundary between MCP tool calls and the
system's perf binary. Every perf invocation flows through PerfExecutor.run(),
which enforces:

    - Path validation: input/output paths are resolved and checked against
      BLOCKED_PREFIXES to prevent reads from /proc, /sys, /dev, /etc.
    - No shell: uses create_subprocess_exec (list form), preventing injection.
    - Timeout: SIGTERM after the deadline, SIGKILL if it doesn't exit in 5s.
    - Output truncation: caps stdout at max_output_bytes to avoid overwhelming
      the LLM's context window.
    - Process cleanup: a finally block kills any orphaned subprocess on
      cancellation or unexpected errors.
    - Pager suppression: sets PERF_PAGER=cat so perf never spawns less/more.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PerfResult:
    """The result of executing a perf command.

    Attributes:
        stdout: Decoded stdout output (may be truncated).
        stderr: Decoded stderr output.
        returncode: Process exit code (0 = success).
        truncated: True if stdout was cut at max_output_bytes.
        command: The full command list that was executed, for debugging.
    """

    stdout: str
    stderr: str
    returncode: int
    truncated: bool
    command: list[str]


class PerfError(Exception):
    """Base exception for all perf execution failures."""


class PerfNotFoundError(PerfError):
    """Raised when the perf binary is not found on PATH."""


class PerfTimeoutError(PerfError):
    """Raised when a perf command exceeds its timeout."""


class PerfInputError(PerfError):
    """Raised for invalid or unsafe file paths."""


# Paths under these directories are rejected for both input and output.
# Prevents reading sensitive system files or writing to system directories.
# Uses tuples of (dir, dir/) to catch both exact matches and children.
BLOCKED_DIRS = ("/proc", "/sys", "/dev", "/etc")

# Hard ceiling on command timeout, regardless of what the caller requests.
MAX_TIMEOUT = 300


class PerfExecutor:
    """Executes perf commands safely with timeout and output limits.

    Instantiate once and reuse across tool calls. The perf binary is
    verified on first use (not at construction time) so the MCP server
    can start even if perf is temporarily unavailable.

    Configuration is resolved from environment variables at construction,
    allowing override via the MCP server's ``env`` config:

        PERF_BINARY         -- path to perf (default: "perf")
        PERF_TIMEOUT        -- default timeout in seconds (default: 60)
        PERF_MAX_OUTPUT_BYTES -- truncation limit (default: 2,000,000)
    """

    def __init__(
        self,
        perf_binary: str | None = None,
        default_timeout: int = 60,
        max_output_bytes: int = 2_000_000,
    ):
        self.perf_binary = perf_binary or os.environ.get("PERF_BINARY", "perf")
        self.default_timeout = int(os.environ.get("PERF_TIMEOUT", str(default_timeout)))
        self.max_output_bytes = int(os.environ.get("PERF_MAX_OUTPUT_BYTES", str(max_output_bytes)))
        # Deferred to first run() call so importing the module doesn't crash.
        self._verified = False

    def _validate_path(self, path: str, *, must_exist: bool = True) -> str:
        """Resolve a path and check it against the blocked-prefix list.

        Uses Path.resolve() to follow symlinks before checking, preventing
        symlink-based traversal attacks (e.g. a symlink pointing to /etc/).

        Args:
            path: The user-provided file path string.
            must_exist: If True, raise PerfInputError when the path doesn't exist.

        Returns:
            The fully resolved absolute path as a string.

        Raises:
            PerfInputError: If the path is in a blocked location or doesn't exist.
        """
        p = Path(path).resolve()
        real = str(p)
        for blocked in BLOCKED_DIRS:
            if real == blocked or real.startswith(blocked + "/"):
                raise PerfInputError(f"Path in blocked location: {blocked}")
        if must_exist and not p.exists():
            raise PerfInputError(f"Path does not exist: {path}")
        return real

    def validate_input_path(self, path: str) -> str:
        """Validate an input file path: must exist and not be in a blocked location."""
        return self._validate_path(path, must_exist=True)

    def validate_output_path(self, path: str) -> str:
        """Validate an output file path: parent must exist, path must not be blocked.

        The file itself doesn't need to exist (it will be created), but the
        parent directory must exist to prevent confusing perf errors.
        """
        resolved = self._validate_path(path, must_exist=False)
        parent = Path(resolved).parent
        if not parent.exists():
            raise PerfInputError(f"Output directory does not exist: {parent}")
        return resolved

    async def run(
        self,
        args: list[str],
        *,
        input_path: str | None = None,
        timeout: int | None = None,
        max_output_bytes: int | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> PerfResult:
        """Execute a perf command and return its output.

        This is the single point through which all perf invocations flow.
        The method handles binary verification, path validation, subprocess
        lifecycle, timeout enforcement, and output truncation.

        Args:
            args: Arguments after ``perf``, e.g. ``["report", "--stdio", "--input", path]``.
            input_path: If provided, validated before execution (convenience for
                the common ``--input`` pattern). The path is NOT injected into args;
                the caller must include it in ``args`` via options_to_cli_args().
            timeout: Per-call timeout override (seconds). Capped at MAX_TIMEOUT.
            max_output_bytes: Per-call output truncation override (bytes).
            extra_env: Additional environment variables for the subprocess.

        Returns:
            A PerfResult with stdout, stderr, exit code, and truncation status.

        Raises:
            PerfNotFoundError: If the perf binary isn't on PATH.
            PerfInputError: If input_path fails validation.
            PerfTimeoutError: If the command exceeds the timeout.
        """
        # Verify perf exists on first call (deferred from __init__).
        if not self._verified:
            if shutil.which(self.perf_binary) is None:
                raise PerfNotFoundError(f"perf binary '{self.perf_binary}' not found on PATH")
            self._verified = True

        if input_path is not None:
            self.validate_input_path(input_path)

        cmd = [self.perf_binary] + args

        # Apply timeout: caller's value (or default), capped at MAX_TIMEOUT.
        effective_timeout = min(
            timeout if timeout is not None else self.default_timeout,
            MAX_TIMEOUT,
        )
        effective_max = max_output_bytes if max_output_bytes is not None else self.max_output_bytes

        # Suppress perf's pager to prevent blocking on interactive output.
        env = os.environ.copy()
        env["PERF_PAGER"] = "cat"
        if extra_env:
            env.update(extra_env)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        truncated = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=effective_timeout
            )
        except asyncio.TimeoutError:
            # Graceful shutdown: SIGTERM first, SIGKILL if it doesn't exit in 5s.
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
            raise PerfTimeoutError(
                f"perf command timed out after {effective_timeout}s: {' '.join(cmd)}"
            )
        finally:
            # Safety net: kill the process if it's still running after any
            # exception (including CancelledError from MCP client disconnect).
            if proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass

        # Truncate oversized output to protect the LLM's context window.
        if len(stdout_bytes) > effective_max:
            stdout_bytes = stdout_bytes[:effective_max]
            truncated = True

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if truncated:
            stdout += f"\n\n[...output truncated at {effective_max} bytes...]"

        return PerfResult(
            stdout=stdout,
            stderr=stderr,
            returncode=proc.returncode or 0,
            truncated=truncated,
            command=cmd,
        )
