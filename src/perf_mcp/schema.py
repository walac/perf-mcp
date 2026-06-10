"""Declarative option definitions, converters, and tool factory for perf CLI tools.

This module defines the mapping between perf CLI options (as declared by
OPT_* macros in the perf C source) and the MCP tool parameters exposed
to LLMs. Two registration paths exist:

**Factory path** (preferred for most tools)::

    register_perf_tool(mcp, executor,
        tool_name="perf_report", command=["report", "--stdio"],
        description="...", options=REPORT_OPTIONS)

**Manual path** (for tools with unique argument handling, e.g. diff, kallsyms)::

    PerfOption list  -->  function signature  -->  build_params(locals())
         |                                              |
         v                                              v
    options_to_cli_args(OPTIONS, params)  -->  ["--sort", "comm", ...]
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from perf_mcp.executor import PerfExecutor, PerfResult


@dataclass
class PerfOption:
    """A single perf CLI option mapped to an MCP tool parameter.

    Each instance describes one ``--flag`` that a perf subcommand accepts.
    The ``long_name`` is the canonical flag name (e.g. ``"call-graph"``),
    which is converted to a Python-safe ``param_name`` (``"call_graph"``)
    via hyphen-to-underscore replacement.

    Attributes:
        long_name: The CLI flag name without ``--`` (e.g. ``"max-stack"``).
        short_name: Single-character short flag (e.g. ``"s"``), or None.
        param_type: One of ``"boolean"``, ``"string"``, ``"integer"``,
            ``"float"``, or ``"incr"``. The ``"incr"`` type is for flags
            like ``--verbose`` that are repeated N times instead of taking
            a numeric argument (perf's OPT_INCR macro).
        description: Human-readable description shown to the LLM.
        default: Default value, used by FastMCP for the tool schema.
        negatable: If True, passing False emits ``--no-{long_name}``
            (e.g. ``--no-children``). Used for options that default to on
            in perf and must be explicitly turned off.
    """

    long_name: str
    short_name: str | None
    param_type: str
    description: str
    default: Any = None
    negatable: bool = False

    @property
    def param_name(self) -> str:
        """Convert the CLI flag name to a valid Python identifier.

        ``"call-graph"`` becomes ``"call_graph"``, matching the function
        parameter name in the tool's signature.
        """
        return self.long_name.replace("-", "_")


def options_to_cli_args(
    options: list[PerfOption],
    values: dict[str, Any],
) -> list[str]:
    """Convert user-provided parameter values to a CLI argument list.

    Iterates through ``options`` in order, looks up each option's
    ``param_name`` in ``values``, and emits the appropriate CLI flags.

    Args:
        options: The tool's PerfOption list (defines the flag names and types).
        values: A dict of ``{param_name: value}`` from ``build_params()``.

    Returns:
        A list of CLI arguments, e.g. ``["--sort", "comm", "--force"]``.

    Type-specific behavior:
        - ``"boolean"``: Emits ``--flag`` if True. If negatable and False,
          emits ``--no-flag``. Non-negatable False emits nothing.
        - ``"string"`` / ``"float"``: Emits ``--flag value``.
        - ``"integer"``: Emits ``--flag N`` (explicitly int-cast).
        - ``"incr"``: Emits ``--flag`` repeated N times (for OPT_INCR flags
          like ``--verbose`` which don't accept numeric arguments).
    """
    args: list[str] = []

    for opt in options:
        param_name = opt.param_name
        if param_name not in values:
            continue

        value = values[param_name]
        if value is None:
            continue

        flag = f"--{opt.long_name}"

        match opt.param_type:
            case "boolean":
                if value:
                    args.append(flag)
                elif opt.negatable:
                    args.append(f"--no-{opt.long_name}")
            case "string" | "float":
                args.extend([flag, str(value)])
            case "integer":
                args.extend([flag, str(int(value))])
            case "incr":
                # OPT_INCR flags (like --verbose) are repeated, not given a number.
                # verbose=2 becomes ["--verbose", "--verbose"], not ["--verbose", "2"].
                args.extend([flag] * int(value))

    return args


def build_params(
    local_vars: dict[str, Any],
    exclude: set[str] | None = None,
) -> dict[str, Any]:
    """Extract tool parameters from a function's locals() dict.

    Used by manually registered tools (diff, kallsyms) that cannot use
    ``register_perf_tool()``. Called as ``build_params(locals())`` inside
    each tool function to capture the MCP parameter values. Filters out:
    - ``"self"`` (from closures)
    - Any keys in ``exclude`` (e.g. ``{"old_input", "new_input"}`` in diff)
    - ``None`` values (parameters not provided by the caller)
    - ``verbose=0`` (the default, which would emit an unnecessary flag)

    False booleans are kept because negatable options (like ``children=False``)
    need to emit ``--no-children``.

    Args:
        local_vars: The return value of ``locals()`` inside a tool function.
        exclude: Additional parameter names to exclude from the result.

    Returns:
        A filtered dict of ``{param_name: value}`` ready for
        ``options_to_cli_args()``.
    """
    skip = {"self"} | (exclude or set())
    params = {k: v for k, v in local_vars.items() if k not in skip and v is not None}
    if params.get("verbose") == 0:
        del params["verbose"]
    return params


def enrich_tool_schema(
    mcp: Any,
    tool_name: str,
    options: list[PerfOption],
) -> None:
    """Patch a registered MCP tool's JSON Schema with PerfOption descriptions.

    FastMCP generates parameter schemas from function signatures, but plain
    Python type annotations don't carry descriptions. This function adds
    the ``description`` field to each parameter in the tool's schema by
    matching PerfOption.param_name to the schema property names. Used by
    both ``register_perf_tool()`` and manually registered tools (diff).

    Must be called AFTER the tool function is registered via @mcp.tool().

    Args:
        mcp: The FastMCP server instance.
        tool_name: The registered tool function name (e.g. ``"perf_report"``).
        options: The PerfOption list for this tool.
    """
    tool = mcp._tool_manager._tools.get(tool_name)
    if tool is None:
        return

    props = tool.parameters.get("properties", {})
    option_map = {opt.param_name: opt for opt in options}

    for param_name, prop in props.items():
        if "description" not in prop and param_name in option_map:
            prop["description"] = option_map[param_name].description


def _build_handler_signature(
    options: list[PerfOption],
    *,
    has_input: bool = True,
    required_options: set[str] | None = None,
) -> str:
    """Generate a Python function parameter string from a PerfOption list.

    Produces a signature like ``input: str, verbose: int = 0, force: bool = False``
    that FastMCP can introspect via pydantic to build a valid argument model.
    Required params (no default) must come before optional ones.
    """
    must_require = required_options or set()
    required_params: list[str] = []
    optional_params: list[str] = []
    seen_input = False

    for opt in options:
        name = opt.param_name
        if has_input and name == "input":
            required_params.append(f"{name}: str")
            seen_input = True
            continue

        is_required = name in must_require

        match opt.param_type:
            case "boolean":
                if is_required:
                    required_params.append(f"{name}: bool")
                elif opt.negatable or opt.default is not None:
                    # Negatable booleans and booleans with explicit defaults
                    # (like skip-empty default=True) use Optional so omitting
                    # the param sends None → no flag emitted. The PerfOption
                    # default is schema metadata only, not a Python default.
                    optional_params.append(f"{name}: bool | None = None")
                else:
                    optional_params.append(f"{name}: bool = False")
            case "string":
                if is_required:
                    required_params.append(f"{name}: str")
                elif opt.default is not None:
                    optional_params.append(f"{name}: str = {opt.default!r}")
                else:
                    optional_params.append(f"{name}: str | None = None")
            case "integer":
                if is_required:
                    required_params.append(f"{name}: int")
                elif opt.default is not None:
                    optional_params.append(f"{name}: int = {opt.default!r}")
                else:
                    optional_params.append(f"{name}: int | None = None")
            case "float":
                if is_required:
                    required_params.append(f"{name}: float")
                elif opt.default is not None:
                    optional_params.append(f"{name}: float = {opt.default!r}")
                else:
                    optional_params.append(f"{name}: float | None = None")
            case "incr":
                if is_required:
                    required_params.append(f"{name}: int")
                else:
                    optional_params.append(f"{name}: int = {opt.default or 0}")

    if has_input and not seen_input:
        required_params.insert(0, "input: str")

    return ", ".join(required_params + optional_params)


def register_perf_tool(
    mcp: Any,
    executor: PerfExecutor,
    *,
    tool_name: str,
    command: list[str],
    description: str,
    options: list[PerfOption],
    has_input: bool = True,
    output_options: list[str] | None = None,
    output_file_param: str | None = None,
    output_file_message: str = "Output written to",
    default_output_file: str | None = None,
    required_options: set[str] | None = None,
    input_before_subcommand: int = 0,
) -> None:
    """Register an MCP tool from a declarative PerfOption specification.

    This factory generates an async handler with an explicit parameter
    signature (required for FastMCP's pydantic validation), registers it,
    and enriches the JSON Schema with descriptions from the PerfOption list.

    Args:
        mcp: The FastMCP server instance.
        executor: The shared PerfExecutor.
        tool_name: MCP tool name (e.g. ``"perf_report"``).
        command: perf subcommand args (e.g. ``["report", "--stdio"]``).
        description: Tool description shown to the LLM.
        options: The PerfOption list defining CLI flags.
        has_input: If True, adds a required ``input`` parameter that
            gets validated via ``executor.validate_input_path()``.
        output_options: Parameter names whose values need output path
            validation (e.g. ``["output"]``, ``["to_json", "to_ctf"]``).
        output_file_param: If set, on success returns the output file's
            path and size instead of perf's stdout. Used by inject/timechart.
        output_file_message: Prefix for the success message when
            ``output_file_param`` is set (e.g. ``"Timechart written to"``).
        default_output_file: Default output filename when output_file_param
            is optional (e.g. ``"output.svg"`` for timechart).
        required_options: Option param_names that must be required in the
            schema (no default in the generated signature). Use for
            non-input params that are mandatory (e.g. ``{"output"}``
            for inject).
        input_before_subcommand: When non-zero, place ``--input`` before
            this index in ``command``. Some perf subcommands (kmem, kvm)
            require ``--input`` as a top-level flag before the sub-action
            word (e.g. ``perf kmem -i file stat``, not
            ``perf kmem stat -i file``).
    """
    if input_before_subcommand and not (0 < input_before_subcommand < len(command)):
        raise ValueError(
            f"input_before_subcommand={input_before_subcommand} "
            f"must be between 1 and {len(command) - 1}"
        )

    validated_output_params = set(output_options or [])

    async def _impl(**kwargs: Any) -> str:
        input_path = kwargs.get("input") if has_input else None
        params = {k: v for k, v in kwargs.items() if v is not None}
        if params.get("verbose") == 0:
            del params["verbose"]

        for op in validated_output_params:
            if op in params:
                params[op] = executor.validate_output_path(params[op])

        if input_before_subcommand and "input" in params:
            input_val = params.pop("input")
            input_cli = ["--input", str(input_val)]
            cli_args = options_to_cli_args(options, params)
            pos = input_before_subcommand
            args = list(command[:pos]) + input_cli + list(command[pos:]) + cli_args
        else:
            cli_args = options_to_cli_args(options, params)
            args = list(command) + cli_args
        result = await executor.run(args, input_path=input_path)

        if output_file_param and result.returncode == 0:
            out_path = params.get(output_file_param, default_output_file)
            if out_path:
                try:
                    size = os.path.getsize(out_path)
                    return f"{output_file_message}: {out_path} ({size} bytes)"
                except OSError:
                    pass

        return format_result(result)

    sig = _build_handler_signature(
        options,
        has_input=has_input,
        required_options=required_options,
    )
    fn_code = (
        f"async def {tool_name}({sig}) -> str:\n"
        f"    return await _impl(**{{k: v for k, v in locals().items()}})\n"
    )
    ns: dict[str, Any] = {"_impl": _impl}
    exec(fn_code, ns)  # noqa: S102
    handler = ns[tool_name]

    mcp.tool(name=tool_name, description=description)(handler)
    enrich_tool_schema(mcp, tool_name, options)


def format_result(result: PerfResult) -> str:
    """Format a PerfResult into a single string for MCP tool return.

    Combines stdout, stderr, and exit code into a human-readable string.
    stderr is appended under a ``[stderr]`` header only if non-empty.
    The exit code is appended only if non-zero.

    Args:
        result: The PerfResult from executor.run().

    Returns:
        A string suitable for returning to the LLM via MCP.
    """
    output = result.stdout
    if result.stderr:
        output += f"\n\n[stderr]\n{result.stderr}"
    if result.returncode != 0:
        output += f"\n\n[exit code: {result.returncode}]"
    return output
