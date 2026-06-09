"""Declarative option definitions and converters for perf CLI tools.

This module defines the mapping between perf CLI options (as declared by
OPT_* macros in the perf C source) and the MCP tool parameters exposed
to LLMs. The pipeline is:

    PerfOption list  -->  function signature  -->  build_params(locals())
         |                                              |
         v                                              v
    options_to_cli_args(OPTIONS, params)  -->  ["--sort", "comm", ...]

Each tool module declares a list of PerfOption objects describing every
supported CLI flag. At runtime, build_params() captures the function's
local variables (the MCP parameter values), and options_to_cli_args()
converts them to the CLI argument list passed to the perf subprocess.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from perf_mcp.executor import PerfResult


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

    Called as ``build_params(locals())`` inside each tool function to
    capture the MCP parameter values. Filters out:
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
    matching PerfOption.param_name to the schema property names.

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
