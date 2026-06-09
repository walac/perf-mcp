# perf-mcp

MCP server for Linux perf. Gives LLMs structured access to `perf report`, `perf script`, `perf annotate`, and 23 other perf analysis commands through typed tool parameters.

Operates on existing `perf.data` files only -- no recording, no system modification.

## Requirements

- Linux with `perf` installed (`perf --version`)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Quick Start

```bash
git clone <repo-url> ~/work/perf-mcp
cd ~/work/perf-mcp
uv sync
```

### Claude Code

Add to `.mcp.json` (project or global):

```json
{
  "mcpServers": {
    "perf-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "<path-to-perf-mcp>", "perf-mcp"]
    }
  }
}
```

Replace `<path-to-perf-mcp>` with the absolute path to your clone.

### Other MCP Clients

Run as a stdio MCP server:

```bash
cd ~/work/perf-mcp
uv run perf-mcp
```

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `PERF_BINARY` | `perf` | Path to the perf binary |
| `PERF_TIMEOUT` | `60` | Command timeout in seconds (max 300) |
| `PERF_MAX_OUTPUT_BYTES` | `2000000` | Output truncation limit (bytes) |

Set via the `env` key in `.mcp.json`:

```json
{
  "mcpServers": {
    "perf-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "<path>", "perf-mcp"],
      "env": {
        "PERF_TIMEOUT": "120"
      }
    }
  }
}
```

## Tools

26 tools across 7 categories. Each wraps a perf subcommand with every CLI option exposed as a typed parameter.

### Core Analysis

| Tool | Command | What it does |
|---|---|---|
| `perf_evlist` | `perf evlist` | List recorded events (start here) |
| `perf_report` | `perf report` | Overhead histogram by symbol/DSO/thread |
| `perf_script` | `perf script` | Raw per-sample event dump |
| `perf_annotate` | `perf annotate` | Source/assembly with per-line hit counts |
| `perf_diff` | `perf diff` | Compare two profiles side-by-side |
| `perf_c2c_report` | `perf c2c report` | False sharing / cache contention |
| `perf_inject` | `perf inject` | Decode Intel PT, inject build IDs |

### Scheduler

| Tool | Command |
|---|---|
| `perf_sched_latency` | Per-task scheduling latency stats |
| `perf_sched_timehist` | Timestamped context switch timeline |
| `perf_sched_map` | ASCII CPU activity map |
| `perf_sched_script` | Raw scheduler event dump |
| `perf_sched_replay` | Replay scheduling for simulation |

### Locks

| Tool | Command |
|---|---|
| `perf_lock_report` | Lock acquire/contention statistics |
| `perf_lock_contention` | Contention analysis with BPF support |
| `perf_lock_info` | Lock type information |

### Kernel Work Items

| Tool | Command |
|---|---|
| `perf_kwork_report` | IRQ/softirq/workqueue statistics |
| `perf_kwork_latency` | Work item latency breakdown |
| `perf_kwork_timehist` | Timestamped work item events |
| `perf_kwork_top` | Top work items by runtime |

### Memory, KVM, Utilities

| Tool | Command |
|---|---|
| `perf_kmem_stat` | Kernel memory allocation stats |
| `perf_mem_report` | Memory access data source analysis |
| `perf_kvm_stat_report` | KVM VM exit statistics |
| `perf_timechart` | Generate scheduling timechart SVG |
| `perf_buildid_list` | List binary build IDs |
| `perf_data_convert` | Convert perf.data to JSON/CTF |
| `perf_kallsyms` | Kernel symbol lookup |

## Typical Workflow

1. Record a profile (outside this tool): `perf record -g -a -- sleep 10`
2. Ask the LLM to analyze it:
   - "What events are in `./perf.data`?" -- calls `perf_evlist`
   - "Show the top CPU consumers" -- calls `perf_report`
   - "Annotate the hottest function" -- calls `perf_annotate`
   - "Show the raw samples for `malloc`" -- calls `perf_script` with `symbols='malloc'`
   - "Compare before and after" -- calls `perf_diff`

## Safety

- **Read-only** -- no recording or data modification commands
- **Path validation** -- input/output paths validated, `/proc` `/sys` `/dev` `/etc` blocked
- **No code execution** -- `--script`, `--dlfilter`, `--objdump`, `--addr2line` options excluded
- **Timeout enforcement** -- processes killed after the configured limit
- **Output truncation** -- large outputs capped with a clear marker
- **No shell** -- all commands use `subprocess.exec` (no shell injection)
