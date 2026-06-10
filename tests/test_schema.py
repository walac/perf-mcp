"""Unit tests for schema.py: PerfOption, options_to_cli_args, build_params,
enrich_tool_schema, and _build_handler_signature.
"""

from __future__ import annotations

import pytest

from perf_mcp.schema import (
    COMMON_OPTIONS,
    PerfOption,
    _build_handler_signature,
    build_params,
    enrich_tool_schema,
    options_to_cli_args,
)


class TestPerfOption:
    def test_param_name_converts_hyphens(self):
        opt = PerfOption("call-graph", "g", "string", "desc")
        assert opt.param_name == "call_graph"

    def test_param_name_no_hyphens(self):
        opt = PerfOption("verbose", "v", "integer", "desc")
        assert opt.param_name == "verbose"


class TestOptionsToCLIArgs:
    def test_boolean_true(self):
        opts = [PerfOption("force", "f", "boolean", "desc")]
        assert options_to_cli_args(opts, {"force": True}) == ["--force"]

    def test_boolean_false_non_negatable(self):
        opts = [PerfOption("force", "f", "boolean", "desc")]
        assert options_to_cli_args(opts, {"force": False}) == []

    def test_boolean_false_negatable(self):
        opts = [PerfOption("children", None, "boolean", "desc", negatable=True)]
        assert options_to_cli_args(opts, {"children": False}) == ["--no-children"]

    def test_boolean_true_negatable(self):
        opts = [PerfOption("children", None, "boolean", "desc", negatable=True)]
        assert options_to_cli_args(opts, {"children": True}) == ["--children"]

    def test_string(self):
        opts = [PerfOption("sort", "s", "string", "desc")]
        assert options_to_cli_args(opts, {"sort": "comm,dso"}) == ["--sort", "comm,dso"]

    def test_integer(self):
        opts = [PerfOption("max-stack", None, "integer", "desc")]
        assert options_to_cli_args(opts, {"max_stack": 5}) == ["--max-stack", "5"]

    def test_float(self):
        opts = [PerfOption("percent-limit", None, "float", "desc")]
        assert options_to_cli_args(opts, {"percent_limit": 0.5}) == ["--percent-limit", "0.5"]

    def test_none_value_skipped(self):
        opts = [PerfOption("sort", "s", "string", "desc")]
        assert options_to_cli_args(opts, {"sort": None}) == []

    def test_missing_key_skipped(self):
        opts = [PerfOption("sort", "s", "string", "desc")]
        assert options_to_cli_args(opts, {}) == []

    def test_multiple_options(self):
        opts = [
            PerfOption("input", "i", "string", "input file"),
            PerfOption("force", "f", "boolean", "force"),
            PerfOption("max-stack", None, "integer", "stack depth"),
        ]
        args = options_to_cli_args(
            opts,
            {
                "input": "/tmp/perf.data",
                "force": True,
                "max_stack": 10,
            },
        )
        assert args == ["--input", "/tmp/perf.data", "--force", "--max-stack", "10"]

    def test_hyphenated_option_name(self):
        opts = [PerfOption("call-graph", "g", "string", "desc")]
        assert options_to_cli_args(opts, {"call_graph": "fp,0.5"}) == ["--call-graph", "fp,0.5"]

    def test_incr_repeats_flag(self):
        opts = [PerfOption("verbose", "v", "incr", "desc")]
        assert options_to_cli_args(opts, {"verbose": 2}) == ["--verbose", "--verbose"]

    def test_incr_zero_no_flags(self):
        opts = [PerfOption("verbose", "v", "incr", "desc")]
        assert options_to_cli_args(opts, {"verbose": 0}) == []

    def test_incr_one_flag(self):
        opts = [PerfOption("verbose", "v", "incr", "desc")]
        assert options_to_cli_args(opts, {"verbose": 1}) == ["--verbose"]

    def test_order_preserved(self):
        opts = [
            PerfOption("aaa", None, "boolean", "first"),
            PerfOption("bbb", None, "boolean", "second"),
            PerfOption("ccc", None, "boolean", "third"),
        ]
        args = options_to_cli_args(opts, {"aaa": True, "bbb": True, "ccc": True})
        assert args == ["--aaa", "--bbb", "--ccc"]


class TestBuildParams:
    def test_filters_none(self):
        params = build_params({"input": "/tmp/x", "sort": None, "force": True})
        assert "sort" not in params
        assert params["input"] == "/tmp/x"
        assert params["force"] is True

    def test_keeps_false_booleans(self):
        params = build_params({"children": False, "force": True})
        assert params["children"] is False
        assert params["force"] is True

    def test_removes_verbose_zero(self):
        params = build_params({"input": "/tmp/x", "verbose": 0})
        assert "verbose" not in params

    def test_keeps_nonzero_verbose(self):
        params = build_params({"input": "/tmp/x", "verbose": 2})
        assert params["verbose"] == 2

    def test_excludes_self(self):
        params = build_params({"self": "something", "input": "/tmp/x"})
        assert "self" not in params

    def test_exclude_set(self):
        params = build_params(
            {"old_input": "a", "new_input": "b", "sort": "comm"},
            exclude={"old_input", "new_input"},
        )
        assert "old_input" not in params
        assert "new_input" not in params
        assert params["sort"] == "comm"


class TestEnrichToolSchema:
    def _make_mock_tool(self, params):
        class MockTool:
            def __init__(self, parameters):
                self.parameters = parameters
        return MockTool(params)

    def _make_mock_mcp(self, tool_name, tool):
        class MockToolManager:
            def __init__(self):
                self._tools = {tool_name: tool}
        class MockMCP:
            def __init__(self):
                self._tool_manager = MockToolManager()
        return MockMCP()

    def test_adds_descriptions(self):
        tool = self._make_mock_tool({
            "properties": {"sort": {}, "force": {}},
        })
        mcp = self._make_mock_mcp("perf_test", tool)
        options = [
            PerfOption("sort", "s", "string", "Sort by key"),
            PerfOption("force", "f", "boolean", "Don't complain"),
        ]
        enrich_tool_schema(mcp, "perf_test", options)
        assert tool.parameters["properties"]["sort"]["description"] == "Sort by key"
        assert tool.parameters["properties"]["force"]["description"] == "Don't complain"

    def test_does_not_overwrite_existing_descriptions(self):
        tool = self._make_mock_tool({
            "properties": {"sort": {"description": "Custom desc"}},
        })
        mcp = self._make_mock_mcp("perf_test", tool)
        options = [PerfOption("sort", "s", "string", "Sort by key")]
        enrich_tool_schema(mcp, "perf_test", options)
        assert tool.parameters["properties"]["sort"]["description"] == "Custom desc"

    def test_missing_tool_is_noop(self):
        class MockMCP:
            class _tool_manager:
                _tools = {}
        enrich_tool_schema(MockMCP(), "nonexistent", [])

    def test_hyphenated_option_maps_to_param_name(self):
        tool = self._make_mock_tool({
            "properties": {"call_graph": {}},
        })
        mcp = self._make_mock_mcp("perf_test", tool)
        options = [PerfOption("call-graph", "g", "string", "Call graph options")]
        enrich_tool_schema(mcp, "perf_test", options)
        assert tool.parameters["properties"]["call_graph"]["description"] == "Call graph options"


class TestBuildHandlerSignature:
    def test_basic_signature(self):
        options = [
            PerfOption("input", "i", "string", "Path"),
            PerfOption("verbose", "v", "incr", "Verbosity", default=0),
            PerfOption("force", "f", "boolean", "Force"),
        ]
        sig = _build_handler_signature(options)
        assert "input: str" in sig
        assert "verbose: int = 0" in sig
        assert "force: bool = False" in sig

    def test_negatable_boolean_is_optional(self):
        options = [
            PerfOption("children", None, "boolean", "desc", negatable=True, default=True),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "children: bool | None = None" in sig

    def test_boolean_with_default_is_optional(self):
        options = [
            PerfOption("skip-empty", None, "boolean", "desc", default=True),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "skip_empty: bool | None = None" in sig

    def test_required_options_come_first(self):
        options = [
            PerfOption("input", "i", "string", "Path"),
            PerfOption("output", "o", "string", "Output"),
            PerfOption("verbose", "v", "incr", "Verbosity", default=0),
        ]
        sig = _build_handler_signature(options, required_options={"output"})
        parts = sig.split(", ")
        req_indices = [i for i, p in enumerate(parts) if "= " not in p]
        opt_indices = [i for i, p in enumerate(parts) if "= " in p]
        assert max(req_indices) < min(opt_indices)

    def test_has_input_false(self):
        options = [
            PerfOption("symbol", None, "string", "Symbol name"),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "input" not in sig
        assert "symbol: str | None = None" in sig

    def test_string_optional_default(self):
        options = [
            PerfOption("sort", "s", "string", "Sort key"),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "sort: str | None = None" in sig

    def test_integer_optional_default(self):
        options = [
            PerfOption("max-stack", None, "integer", "Max stack"),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "max_stack: int | None = None" in sig

    def test_float_optional_default(self):
        options = [
            PerfOption("percent-limit", None, "float", "Limit"),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "percent_limit: float | None = None" in sig

    def test_string_with_explicit_default(self):
        options = [
            PerfOption("sort", "s", "string", "Sort key", default="comm"),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "sort: str = 'comm'" in sig

    def test_integer_with_explicit_default(self):
        options = [
            PerfOption("max-stack", None, "integer", "Max depth", default=10),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "max_stack: int = 10" in sig

    def test_float_with_explicit_default(self):
        options = [
            PerfOption("percent-limit", None, "float", "Limit", default=0.5),
        ]
        sig = _build_handler_signature(options, has_input=False)
        assert "percent_limit: float = 0.5" in sig

    def test_input_auto_inserted_when_missing(self):
        options = [
            PerfOption("force", "f", "boolean", "Force"),
        ]
        sig = _build_handler_signature(options, has_input=True)
        assert sig.startswith("input: str")


class TestCommonOptions:
    def test_common_options_has_three_entries(self):
        assert len(COMMON_OPTIONS) == 3

    def test_common_options_param_names(self):
        names = [o.param_name for o in COMMON_OPTIONS]
        assert names == ["input", "verbose", "force"]

    def test_frozen_prevents_mutation(self):
        with pytest.raises(AttributeError):
            COMMON_OPTIONS[0].description = "modified"
