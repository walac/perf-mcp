"""Unit tests for schema.py: PerfOption, options_to_cli_args, build_params.

Tests the core option-to-CLI-argument pipeline that all tool modules depend on.
Covers every param_type (boolean, string, integer, float, incr), negatable
booleans, None/missing value handling, hyphenated names, and the build_params
filtering logic.
"""

from __future__ import annotations

from perf_mcp.schema import PerfOption, build_params, options_to_cli_args


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
