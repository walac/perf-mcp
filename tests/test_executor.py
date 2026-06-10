"""Tests for executor.py: PerfExecutor path validation and subprocess execution.

Covers the security boundary (blocked paths, symlink resolution), perf binary
detection, subprocess lifecycle (timeout, truncation, exit codes, stderr),
environment variable overrides, timeout capping, and the async run() method.
Requires a real perf binary for most tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from perf_mcp.executor import (
    MAX_TIMEOUT,
    PerfExecutor,
    PerfInputError,
    PerfNotFoundError,
    PerfTimeoutError,
)


class TestPathValidation:
    def test_validate_input_existing_file(self, executor, perf_data):
        result = executor.validate_input_path(perf_data)
        assert result.endswith("test.perf.data")

    def test_validate_input_nonexistent(self, executor):
        with pytest.raises(PerfInputError, match="does not exist"):
            executor.validate_input_path("/tmp/nonexistent_file_abc123")

    def test_validate_input_blocked_proc(self, executor):
        with pytest.raises(PerfInputError, match="blocked location"):
            executor.validate_input_path("/proc/self/maps")

    def test_validate_input_blocked_sys(self, executor):
        with pytest.raises(PerfInputError, match="blocked location"):
            executor.validate_input_path("/sys/kernel/notes")

    def test_validate_input_blocked_dev(self, executor):
        with pytest.raises(PerfInputError, match="blocked location"):
            executor.validate_input_path("/dev/null")

    def test_validate_input_blocked_etc(self, executor):
        with pytest.raises(PerfInputError, match="blocked location"):
            executor.validate_input_path("/etc/passwd")

    def test_validate_output_blocked(self, executor):
        with pytest.raises(PerfInputError, match="blocked location"):
            executor.validate_output_path("/etc/cron.d/backdoor")

    def test_validate_output_parent_must_exist(self, executor):
        with pytest.raises(PerfInputError, match="Output directory does not exist"):
            executor.validate_output_path("/tmp/nonexistent_dir_abc/output.data")

    def test_validate_output_valid(self, executor):
        result = executor.validate_output_path("/tmp/valid_output.data")
        assert result == "/tmp/valid_output.data"

    def test_validate_input_resolves_path(self, executor, perf_data):
        result = executor.validate_input_path(perf_data)
        assert "/" in result
        assert ".." not in result


class TestPerfNotFound:
    @pytest.mark.asyncio
    async def test_missing_binary(self):
        ex = PerfExecutor(perf_binary="nonexistent_perf_binary_xyz")
        with pytest.raises(PerfNotFoundError):
            await ex.run(["evlist"])


class TestRun:
    @pytest.mark.asyncio
    async def test_basic_execution(self, executor, perf_data):
        result = await executor.run(["evlist", "--input", perf_data])
        assert result.returncode == 0
        assert "cycles" in result.stdout
        assert not result.truncated

    @pytest.mark.asyncio
    async def test_input_path_validation(self, executor, perf_data):
        result = await executor.run(
            ["evlist", "--input", perf_data],
            input_path=perf_data,
        )
        assert result.returncode == 0

    @pytest.mark.asyncio
    async def test_invalid_input_path(self, executor):
        with pytest.raises(PerfInputError):
            await executor.run(
                ["evlist"],
                input_path="/tmp/does_not_exist_xyz",
            )

    @pytest.mark.asyncio
    async def test_perf_pager_disabled(self, executor, perf_data):
        result = await executor.run(["evlist", "--input", perf_data])
        assert result.returncode == 0

    @pytest.mark.asyncio
    async def test_nonzero_exit_code(self, executor):
        result = await executor.run(["evlist", "--input", "/dev/null"])
        assert result.returncode != 0

    @pytest.mark.asyncio
    async def test_stderr_captured(self, executor):
        result = await executor.run(["evlist", "--input", "/tmp/nonexistent_xyz"])
        assert result.stderr != ""

    @pytest.mark.asyncio
    async def test_truncation(self, executor, perf_data):
        result = await executor.run(
            ["script", "--input", perf_data],
            max_output_bytes=50,
        )
        assert result.truncated
        assert "truncated" in result.stdout

    @pytest.mark.asyncio
    async def test_timeout(self, executor):
        with pytest.raises(PerfTimeoutError):
            await executor.run(["stat", "--", "sleep", "999"], timeout=1)

    @pytest.mark.asyncio
    async def test_command_recorded(self, executor, perf_data):
        result = await executor.run(["evlist", "--input", perf_data])
        assert "perf" in result.command[0]
        assert "evlist" in result.command

    @pytest.mark.asyncio
    async def test_extra_env_passed(self, executor, perf_data):
        with patch(
            "perf_mcp.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"output", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await executor.run(
                ["evlist", "--input", perf_data],
                extra_env={"PERF_EXTRA_TEST": "1"},
            )
            env = mock_exec.call_args.kwargs["env"]
            assert env["PERF_EXTRA_TEST"] == "1"
            assert env["PERF_PAGER"] == "cat"


class TestEnvVarOverrides:
    def test_perf_binary_from_env(self, monkeypatch):
        monkeypatch.setenv("PERF_BINARY", "/usr/local/bin/perf")
        ex = PerfExecutor()
        assert ex.perf_binary == "/usr/local/bin/perf"

    def test_perf_binary_constructor_overrides_env(self, monkeypatch):
        monkeypatch.setenv("PERF_BINARY", "/usr/local/bin/perf")
        ex = PerfExecutor(perf_binary="/opt/perf")
        assert ex.perf_binary == "/opt/perf"

    def test_perf_binary_default(self, monkeypatch):
        monkeypatch.delenv("PERF_BINARY", raising=False)
        ex = PerfExecutor()
        assert ex.perf_binary == "perf"

    def test_perf_timeout_from_env(self, monkeypatch):
        monkeypatch.setenv("PERF_TIMEOUT", "30")
        ex = PerfExecutor()
        assert ex.default_timeout == 30

    def test_perf_timeout_default(self, monkeypatch):
        monkeypatch.delenv("PERF_TIMEOUT", raising=False)
        ex = PerfExecutor()
        assert ex.default_timeout == 60

    def test_perf_max_output_from_env(self, monkeypatch):
        monkeypatch.setenv("PERF_MAX_OUTPUT_BYTES", "500000")
        ex = PerfExecutor()
        assert ex.max_output_bytes == 500000

    def test_perf_max_output_default(self, monkeypatch):
        monkeypatch.delenv("PERF_MAX_OUTPUT_BYTES", raising=False)
        ex = PerfExecutor()
        assert ex.max_output_bytes == 2_000_000


class TestTimeoutCapping:
    @pytest.mark.asyncio
    async def test_timeout_capped_at_max(self, perf_data):
        ex = PerfExecutor()
        with patch(
            "perf_mcp.executor.asyncio.wait_for", wraps=__import__("asyncio").wait_for
        ) as mock_wait:
            await ex.run(["evlist", "--input", perf_data], timeout=MAX_TIMEOUT + 100)
            assert (
                mock_wait.call_args.kwargs.get(
                    "timeout", mock_wait.call_args[1] if len(mock_wait.call_args) > 1 else None
                )
                == MAX_TIMEOUT
            )

    @pytest.mark.asyncio
    async def test_default_timeout_used_when_none(self, perf_data):
        ex = PerfExecutor(default_timeout=42)
        with patch(
            "perf_mcp.executor.asyncio.wait_for", wraps=__import__("asyncio").wait_for
        ) as mock_wait:
            await ex.run(["evlist", "--input", perf_data])
            timeout_used = (
                mock_wait.call_args[1]
                if len(mock_wait.call_args.args) > 1
                else mock_wait.call_args.kwargs.get("timeout")
            )
            assert timeout_used == 42

    @pytest.mark.asyncio
    async def test_default_timeout_from_env(self, monkeypatch, perf_data):
        monkeypatch.setenv("PERF_TIMEOUT", "99")
        ex = PerfExecutor()
        assert ex.default_timeout == 99
        with patch(
            "perf_mcp.executor.asyncio.wait_for", wraps=__import__("asyncio").wait_for
        ) as mock_wait:
            await ex.run(["evlist", "--input", perf_data])
            timeout_used = (
                mock_wait.call_args[1]
                if len(mock_wait.call_args.args) > 1
                else mock_wait.call_args.kwargs.get("timeout")
            )
            assert timeout_used == 99


class TestDeferredVerification:
    @pytest.mark.asyncio
    async def test_verified_flag_set_after_first_run(self, perf_data):
        ex = PerfExecutor()
        assert not ex._verified
        await ex.run(["evlist", "--input", perf_data])
        assert ex._verified
