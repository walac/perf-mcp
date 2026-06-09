#!/usr/bin/env python3
"""Extract OPT_* macro definitions from perf builtin-*.c source files.

Parses the option arrays in each perf subcommand source file and outputs
structured JSON with every option's type, short flag, long name, metavar,
and description. Used to keep perf-mcp tool definitions in sync with the
perf source.

Usage:
    python scripts/extract_options.py /path/to/linux/tools/perf
    python scripts/extract_options.py /path/to/linux/tools/perf --validate
    python scripts/extract_options.py /path/to/linux/tools/perf --command report
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ExtractedOption:
    macro: str
    short_name: str | None
    long_name: str
    metavar: str | None
    description: str
    param_type: str
    source_file: str
    line_number: int


# Map OPT_* macro names to our param_type values
MACRO_TYPE_MAP = {
    "OPT_BOOLEAN": "boolean",
    "OPT_BOOLEAN_FLAG": "boolean",
    "OPT_BOOLEAN_SET": "boolean",
    "OPT_STRING": "string",
    "OPT_STRING_NOEMPTY": "string",
    "OPT_INTEGER": "integer",
    "OPT_UINTEGER": "integer",
    "OPT_ULONG": "integer",
    "OPT_INCR": "integer",
    "OPT_CALLBACK": "string",
    "OPT_CALLBACK_DEFAULT": "string",
    "OPT_CALLBACK_OPTARG": "string",
    "OPT_CALLBACK_NOOPT": "boolean",
}

# Commands we care about (analysis-only, matching our MCP tools)
ANALYSIS_COMMANDS = {
    "annotate",
    "report",
    "script",
    "diff",
    "evlist",
    "inject",
    "c2c",
    "sched",
    "lock",
    "kwork",
    "kmem",
    "mem",
    "kvm",
    "timechart",
    "buildid-list",
    "data",
    "kallsyms",
}

# Macros to skip (not user-facing options)
SKIP_MACROS = {"OPT_END", "OPT_PARENT", "OPT_ARGUMENT"}


def _extract_c_string(text: str) -> str | None:
    """Extract a C string literal, handling concatenation across lines."""
    # Match one or more adjacent "..." segments
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', text)
    if not parts:
        return None
    return "".join(parts)


def _parse_short_flag(token: str) -> str | None:
    """Parse the short flag from a macro argument like '0' or "'f'"."""
    token = token.strip()
    if token == "0":
        return None
    m = re.match(r"'(.)'", token)
    return m.group(1) if m else None


def _find_matching_paren(text: str, start: int) -> int:
    """Find the closing paren matching the opening paren at `start`."""
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        elif ch == '"':
            # Skip string literals
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] == "\\":
                    i += 1
                i += 1
        i += 1
    return -1


def _split_macro_args(body: str) -> list[str]:
    """Split a macro body on commas, respecting parens and string literals."""
    args: list[str] = []
    depth = 0
    current: list[str] = []
    in_string = False
    i = 0
    while i < len(body):
        ch = body[i]
        if in_string:
            current.append(ch)
            if ch == "\\" and i + 1 < len(body):
                i += 1
                current.append(body[i])
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
            current.append(ch)
        elif ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    if current:
        args.append("".join(current).strip())
    return args


def extract_options_from_file(filepath: Path) -> list[ExtractedOption]:
    """Extract all OPT_* macros from a single C source file."""
    text = filepath.read_text(encoding="utf-8", errors="replace")
    results: list[ExtractedOption] = []

    # Pattern: OPT_TYPENAME( at the start of a line (with optional whitespace)
    pattern = re.compile(r"^\s*(OPT_\w+)\s*\(", re.MULTILINE)

    for m in pattern.finditer(text):
        macro_name = m.group(1)
        if macro_name in SKIP_MACROS:
            continue
        if macro_name not in MACRO_TYPE_MAP:
            continue

        paren_start = m.end() - 1  # position of the '('
        paren_end = _find_matching_paren(text, paren_start)
        if paren_end == -1:
            continue

        body = text[paren_start + 1 : paren_end]
        line_number = text[: m.start()].count("\n") + 1

        args = _split_macro_args(body)
        opt = _parse_macro(macro_name, args, str(filepath), line_number)
        if opt is not None:
            results.append(opt)

    return results


def _parse_macro(macro: str, args: list[str], source: str, line: int) -> ExtractedOption | None:
    """Parse a split OPT_* macro into an ExtractedOption."""
    param_type = MACRO_TYPE_MAP.get(macro)
    if param_type is None:
        return None

    # All macros start with: short_flag, "long_name", &variable, ...
    if len(args) < 3:
        return None

    short = _parse_short_flag(args[0])
    long_name = _extract_c_string(args[1])
    if long_name is None:
        # Some macros like OPT_CALLBACK_NOOPT('g', NULL, ...) have NULL long name
        return None

    metavar = None
    description = None

    match macro:
        case "OPT_BOOLEAN" | "OPT_BOOLEAN_FLAG":
            # OPT_BOOLEAN(short, "long", &var, "description")
            # OPT_BOOLEAN_FLAG(short, "long", &var, "description", flags)
            description = _extract_c_string(" ".join(args[3:]))

        case "OPT_BOOLEAN_SET":
            # OPT_BOOLEAN_SET(short, "long", &var, &set_var, "description")
            description = _extract_c_string(" ".join(args[4:]))

        case "OPT_STRING" | "OPT_STRING_NOEMPTY":
            # OPT_STRING(short, "long", &var, "metavar", "description")
            if len(args) >= 5:
                metavar = _extract_c_string(args[3])
                description = _extract_c_string(" ".join(args[4:]))

        case "OPT_INTEGER" | "OPT_UINTEGER" | "OPT_ULONG":
            # OPT_INTEGER(short, "long", &var, "description")
            description = _extract_c_string(" ".join(args[3:]))

        case "OPT_INCR":
            # OPT_INCR(short, "long", &var, "description")
            description = _extract_c_string(" ".join(args[3:]))

        case "OPT_CALLBACK":
            # OPT_CALLBACK(short, "long", &var, "metavar", "description", callback)
            if len(args) >= 6:
                metavar = _extract_c_string(args[3])
                description = _extract_c_string(" ".join(args[4:-1]))

        case "OPT_CALLBACK_DEFAULT":
            # OPT_CALLBACK_DEFAULT(short, "long", &var, "metavar", "description", callback, default)
            if len(args) >= 7:
                metavar = _extract_c_string(args[3])
                description = _extract_c_string(" ".join(args[4:-2]))

        case "OPT_CALLBACK_OPTARG":
            # OPT_CALLBACK_OPTARG(short, "long", &var, default, "metavar", "description", callback)
            if len(args) >= 7:
                metavar = _extract_c_string(args[4])
                description = _extract_c_string(" ".join(args[5:-1]))

        case "OPT_CALLBACK_NOOPT":
            # OPT_CALLBACK_NOOPT(short, "long", &var, "", "description", callback)
            if len(args) >= 6:
                description = _extract_c_string(" ".join(args[4:-1]))

    if description is None:
        description = ""

    # Clean up description: collapse whitespace, remove trailing punctuation artifacts
    description = re.sub(r"\s+", " ", description).strip()

    return ExtractedOption(
        macro=macro,
        short_name=short,
        long_name=long_name,
        metavar=metavar,
        description=description,
        param_type=param_type,
        source_file=source,
        line_number=line,
    )


def extract_command_name(filepath: Path) -> str:
    """Derive the perf command name from a builtin-*.c filename."""
    stem = filepath.stem  # e.g., "builtin-report"
    if stem.startswith("builtin-"):
        return stem[len("builtin-") :]
    return stem


def extract_all(
    perf_dir: Path, command_filter: str | None = None
) -> dict[str, list[ExtractedOption]]:
    """Extract options from all builtin-*.c files under the perf directory."""
    results: dict[str, list[ExtractedOption]] = {}

    for filepath in sorted(perf_dir.glob("builtin-*.c")):
        cmd = extract_command_name(filepath)
        if command_filter and cmd != command_filter:
            continue
        if cmd not in ANALYSIS_COMMANDS:
            continue

        options = extract_options_from_file(filepath)
        if options:
            results[cmd] = options

    return results


def validate_against_tools(
    extracted: dict[str, list[ExtractedOption]],
    tools_dir: Path,
) -> list[str]:
    """Compare extracted options against hand-coded PerfOption lists in tool modules.

    Returns a list of diagnostic messages.
    """
    diagnostics: list[str] = []

    # Load all PerfOption long_names from each tool module
    for tool_file in sorted(tools_dir.glob("*.py")):
        if tool_file.name == "__init__.py":
            continue

        text = tool_file.read_text()
        # Extract PerfOption("long-name", ...) definitions
        tool_options = set(re.findall(r'PerfOption\(\s*"([^"]+)"', text))
        if not tool_options:
            continue

        module_name = tool_file.stem

        # Map tool module to perf command(s)
        cmd_map = {
            "report": ["report"],
            "script": ["script"],
            "annotate": ["annotate"],
            "diff": ["diff"],
            "c2c": ["c2c"],
            "inject": ["inject"],
            "evlist": ["evlist"],
            "buildid": ["buildid-list"],
            "data": ["data"],
            "kallsyms": ["kallsyms"],
            "sched": ["sched"],
            "lock": ["lock"],
            "kwork": ["kwork"],
            "kmem": ["kmem"],
            "mem": ["mem"],
            "kvm": ["kvm"],
            "timechart": ["timechart"],
        }

        cmds = cmd_map.get(module_name, [])

        for cmd in cmds:
            if cmd not in extracted:
                continue

            source_options = {opt.long_name for opt in extracted[cmd]}

            # Options in source but not in tool module
            missing = source_options - tool_options
            # Exclude known intentionally-omitted options
            intentionally_omitted = {
                "help",
                "version",
                "exec-path",
                "paginate",
                "no-pager",
                "debug",
                "debug-file",
                # TUI/GTK options (we force --stdio)
                "tui",
                "gtk",
                "stdio",
                # Security-excluded (execute arbitrary code/binaries)
                "script",
                "gen-script",
                "dlfilter",
                "objdump",
                "addr2line",
                "addr2line-style",
                # Hidden aliases
                "showcpuutilization",
                # Build-conditional (may not be present)
                "pfm-events",
                # Terminal-specific (no use in MCP stdio context)
                "stdio-color",
                # Experimental/internal
                "stdio2",
                # Debug/internal modes in perf script
                "debug-mode",
                "dlarg",
                "dump-unsorted-raw-trace",
                # Subcommand list modes (not analysis options)
                "list",
                "list-dlfilters",
                # Capital-letter option in sched (unusual, skip)
                "CPU",
            }
            missing -= intentionally_omitted

            if missing:
                diagnostics.append(
                    f"[{module_name}.py] Missing from tool (in perf {cmd} source): "
                    + ", ".join(sorted(missing))
                )

            # Options in tool module but not in source
            extra = tool_options - source_options
            # Common shared options that appear in tools but may not be in this specific command's source
            shared_options = {
                "input",
                "verbose",
                "force",
                "vmlinux",
                "kallsyms",
                "modules",
                "symfs",
                "cpu",
                "ignore-vmlinux",
                "demangle",
                "demangle-kernel",
                # Options that exist in sub-command option arrays (not the
                # main array the extractor parses from the builtin-*.c file)
                "comms",
                "ns",
                "sort",
                "fields",
                # Version-dependent options present in some builds
                "max-events",
            }
            extra -= shared_options

            if extra:
                diagnostics.append(
                    f"[{module_name}.py] Extra in tool (not in perf {cmd} source): "
                    + ", ".join(sorted(extra))
                )

    return diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract OPT_* options from perf source files")
    parser.add_argument(
        "perf_dir",
        type=Path,
        help="Path to tools/perf/ directory in a Linux source tree",
    )
    parser.add_argument(
        "--command",
        "-c",
        help="Extract options for a specific command only",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Compare extracted options against perf-mcp tool modules",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (default: human-readable table)",
    )
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=Path(__file__).parent.parent / "src" / "perf_mcp" / "tools",
        help="Path to perf_mcp/tools/ directory (for --validate)",
    )
    args = parser.parse_args()

    if not args.perf_dir.exists():
        print(f"Error: {args.perf_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    extracted = extract_all(args.perf_dir, args.command)

    if args.validate:
        diagnostics = validate_against_tools(extracted, args.tools_dir)
        if diagnostics:
            print(f"Found {len(diagnostics)} discrepancies:\n")
            for d in diagnostics:
                print(f"  {d}")
            sys.exit(1)
        else:
            total = sum(len(opts) for opts in extracted.values())
            print(f"OK: {total} options across {len(extracted)} commands — all in sync")
            sys.exit(0)

    if args.json:
        output = {cmd: [asdict(opt) for opt in opts] for cmd, opts in extracted.items()}
        json.dump(output, sys.stdout, indent=2)
        print()
    else:
        for cmd, opts in sorted(extracted.items()):
            print(f"\n{'=' * 60}")
            print(f"perf {cmd} ({len(opts)} options)")
            print(f"{'=' * 60}")
            for opt in opts:
                short = f"-{opt.short_name}" if opt.short_name else "  "
                desc = (
                    opt.description[:60] + "..." if len(opt.description) > 60 else opt.description
                )
                print(f"  {short} --{opt.long_name:<30s} [{opt.param_type:<7s}] {desc}")


if __name__ == "__main__":
    main()
