"""Tests for executor.py: PerfExecutor path validation and subprocess execution.

Covers the security boundary (blocked paths, symlink resolution), perf binary
detection, subprocess lifecycle (timeout, truncation, exit codes, stderr),
and the async run() method. Requires a real perf binary for most tests.
"""

from __future__ import annotations

import pytest

from perf_mcp.executor import PerfExecutor, PerfInputError, PerfNotFoundError, PerfTimeoutError


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
