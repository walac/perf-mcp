"""Integration tests for MCP tool registration and execution.

Tests that all 26 tools register correctly with FastMCP, have proper
descriptions, and produce valid output when run against a real perf.data
fixture. Also tests parameter passing (sort, header-only, symbol filter)
and error handling (invalid input paths).
"""

from __future__ import annotations

import pytest

from perf_mcp.schema import format_result
from perf_mcp.server import _register_all_tools, mcp


class TestToolRegistration:
    @pytest.fixture(autouse=True)
    def register(self):
        _register_all_tools()

    def test_tool_count(self):
        tools = list(mcp._tool_manager._tools.values())
        assert len(tools) == 26

    def test_all_tool_names(self):
        names = sorted(t.name for t in mcp._tool_manager._tools.values())
        expected = [
            "perf_annotate",
            "perf_buildid_list",
            "perf_c2c_report",
            "perf_data_convert",
            "perf_diff",
            "perf_evlist",
            "perf_inject",
            "perf_kallsyms",
            "perf_kmem_stat",
            "perf_kvm_stat_report",
            "perf_kwork_latency",
            "perf_kwork_report",
            "perf_kwork_timehist",
            "perf_kwork_top",
            "perf_lock_contention",
            "perf_lock_info",
            "perf_lock_report",
            "perf_mem_report",
            "perf_report",
            "perf_sched_latency",
            "perf_sched_map",
            "perf_sched_replay",
            "perf_sched_script",
            "perf_sched_timehist",
            "perf_script",
            "perf_timechart",
        ]
        assert names == expected

    def test_each_tool_has_description(self):
        for tool in mcp._tool_manager._tools.values():
            assert tool.description, f"{tool.name} has no description"
            assert len(tool.description) > 20, f"{tool.name} description too short"


class TestToolExecution:
    @pytest.fixture(autouse=True)
    def register(self):
        _register_all_tools()

    def _get_tool(self, name: str):
        return mcp._tool_manager._tools[name]

    @pytest.mark.asyncio
    async def test_evlist(self, perf_data):
        tool = self._get_tool("perf_evlist")
        result = await tool.fn(input=perf_data)
        assert "cycles" in result

    @pytest.mark.asyncio
    async def test_report(self, perf_data):
        tool = self._get_tool("perf_report")
        result = await tool.fn(input=perf_data)
        assert "Samples" in result

    @pytest.mark.asyncio
    async def test_script(self, perf_data):
        tool = self._get_tool("perf_script")
        result = await tool.fn(input=perf_data)
        assert "sleep" in result

    @pytest.mark.asyncio
    async def test_buildid_list(self, perf_data):
        tool = self._get_tool("perf_buildid_list")
        result = await tool.fn(input=perf_data)
        assert len(result.strip()) > 0

    @pytest.mark.asyncio
    async def test_annotate(self, perf_data):
        tool = self._get_tool("perf_annotate")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_report_with_sort(self, perf_data):
        tool = self._get_tool("perf_report")
        result = await tool.fn(input=perf_data, sort="dso")
        assert "Samples" in result

    @pytest.mark.asyncio
    async def test_report_header_only(self, perf_data):
        tool = self._get_tool("perf_report")
        result = await tool.fn(input=perf_data, header_only=True)
        assert (
            "captured" in result.lower()
            or "hostname" in result.lower()
            or "cmdline" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_report_with_filter(self, perf_data):
        tool = self._get_tool("perf_report")
        result = await tool.fn(input=perf_data, symbols="main")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_evlist_verbose(self, perf_data):
        tool = self._get_tool("perf_evlist")
        result = await tool.fn(input=perf_data, verbose=1)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_kallsyms(self):
        tool = self._get_tool("perf_kallsyms")
        result = await tool.fn(symbol="schedule")
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_evlist_invalid_input(self):
        tool = self._get_tool("perf_evlist")
        with pytest.raises(Exception):
            await tool.fn(input="/tmp/nonexistent_xyz")


class TestFormatResult:
    def test_success(self):
        from perf_mcp.executor import PerfResult

        r = PerfResult(stdout="output", stderr="", returncode=0, truncated=False, command=["perf"])
        assert format_result(r) == "output"

    def test_with_stderr(self):
        from perf_mcp.executor import PerfResult

        r = PerfResult(
            stdout="output", stderr="warning", returncode=0, truncated=False, command=["perf"]
        )
        result = format_result(r)
        assert "output" in result
        assert "[stderr]" in result
        assert "warning" in result

    def test_nonzero_exit(self):
        from perf_mcp.executor import PerfResult

        r = PerfResult(stdout="", stderr="error", returncode=1, truncated=False, command=["perf"])
        result = format_result(r)
        assert "[exit code: 1]" in result
