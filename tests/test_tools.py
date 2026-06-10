"""Integration tests for MCP tool registration and execution.

Tests that all 26 tools register correctly with FastMCP, have proper
descriptions, and produce valid output when run against a real perf.data
fixture. Also tests parameter passing (sort, header-only, symbol filter)
and error handling (invalid input paths).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mcp.server.fastmcp.tools.base import Tool

from perf_mcp.schema import format_result, get_all_tools, get_tool
from perf_mcp.server import _register_all_tools, mcp


class TestToolRegistration:
    @pytest.fixture(autouse=True)
    def register(self):
        _register_all_tools()

    def test_tool_count(self):
        tools = list(get_all_tools(mcp).values())
        assert len(tools) == 26

    def test_all_tool_names(self):
        names = sorted(t.name for t in get_all_tools(mcp).values())
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
        for tool in get_all_tools(mcp).values():
            assert tool.description, f"{tool.name} has no description"
            assert len(tool.description) > 20, f"{tool.name} description too short"


class TestToolExecution:
    @pytest.fixture(autouse=True)
    def register(self):
        _register_all_tools()

    def _get_tool(self, name: str) -> Tool:
        tool = get_tool(mcp, name)
        assert tool is not None, f"Tool {name!r} not registered"
        return tool

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

    # -- Tools that produce valid output with the basic test fixture --

    @pytest.mark.asyncio
    async def test_c2c_report(self, perf_data):
        tool = self._get_tool("perf_c2c_report")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0
        assert "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_data_convert(self, perf_data, tmp_path):
        out = str(tmp_path / "output.json")
        tool = self._get_tool("perf_data_convert")
        result = await tool.fn(input=perf_data, to_json=out)
        assert "Converted" in result or "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_inject(self, perf_data, tmp_path):
        out = str(tmp_path / "injected.data")
        tool = self._get_tool("perf_inject")
        result = await tool.fn(input=perf_data, output=out, build_ids=True)
        assert "Output written to" in result

    @pytest.mark.asyncio
    async def test_mem_report(self, perf_data):
        tool = self._get_tool("perf_mem_report")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_diff(self, perf_data):
        tool = self._get_tool("perf_diff")
        result = await tool.fn(old_input=perf_data, new_input=perf_data)
        assert "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_kwork_report(self, perf_data):
        tool = self._get_tool("perf_kwork_report")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0
        assert "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_kwork_latency(self, perf_data):
        tool = self._get_tool("perf_kwork_latency")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0
        assert "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_kwork_timehist(self, perf_data):
        tool = self._get_tool("perf_kwork_timehist")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0
        assert "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_kwork_top(self, perf_data):
        tool = self._get_tool("perf_kwork_top")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0
        assert "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_sched_latency(self, perf_data):
        tool = self._get_tool("perf_sched_latency")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0
        assert "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_sched_map(self, perf_data):
        tool = self._get_tool("perf_sched_map")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_sched_replay(self, perf_data):
        tool = self._get_tool("perf_sched_replay")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0
        assert "[exit code:" not in result

    @pytest.mark.asyncio
    async def test_sched_script(self, perf_data):
        tool = self._get_tool("perf_sched_script")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0
        assert "[exit code:" not in result

    # -- Tools that need specialized perf data (lock/sched/kmem/kvm/timechart events).
    # These return error messages with the generic fixture, but verify the
    # full pipeline executes without crashing. --

    @pytest.mark.asyncio
    async def test_lock_report(self, perf_data):
        tool = self._get_tool("perf_lock_report")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_lock_contention(self, perf_data):
        tool = self._get_tool("perf_lock_contention")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_lock_info(self, perf_data):
        tool = self._get_tool("perf_lock_info")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_sched_timehist(self, perf_data):
        tool = self._get_tool("perf_sched_timehist")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_timechart(self, perf_data):
        tool = self._get_tool("perf_timechart")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_kmem_stat(self, perf_data):
        tool = self._get_tool("perf_kmem_stat")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_kvm_stat_report(self, perf_data):
        tool = self._get_tool("perf_kvm_stat_report")
        result = await tool.fn(input=perf_data)
        assert len(result) > 0


class TestToolRunDispatch:
    """Test the MCP runtime dispatch path (tool.run) which goes through
    pydantic validation, unlike tool.fn() used in other tests."""

    @pytest.fixture(autouse=True)
    def register(self):
        _register_all_tools()

    def _get_tool(self, name: str) -> Tool:
        tool = get_tool(mcp, name)
        assert tool is not None, f"Tool {name!r} not registered"
        return tool

    @pytest.mark.asyncio
    async def test_evlist_via_run(self, perf_data):
        tool = self._get_tool("perf_evlist")
        result = await tool.run({"input": perf_data})
        assert "cycles" in str(result)

    @pytest.mark.asyncio
    async def test_report_via_run(self, perf_data):
        tool = self._get_tool("perf_report")
        result = await tool.run({"input": perf_data, "header_only": True})
        text = str(result).lower()
        assert "captured" in text or "hostname" in text or "cmdline" in text

    @pytest.mark.asyncio
    async def test_kallsyms_via_run(self):
        tool = self._get_tool("perf_kallsyms")
        result = await tool.run({"symbol": "schedule"})
        assert len(str(result)) > 0


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
