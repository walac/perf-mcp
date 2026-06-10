"""Shared pytest fixtures for perf-mcp tests.

Provides:
    executor: A PerfExecutor instance for testing subprocess execution.
    perf_data: Path to a small test perf.data fixture file. Skips tests
        if the fixture is not present or if the installed perf binary
        cannot parse its format (incompatible format).
"""

from __future__ import annotations

import functools
import shutil
import subprocess
from pathlib import Path

import pytest

from perf_mcp.executor import PerfExecutor

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_PERF_DATA = FIXTURES_DIR / "test.perf.data"


@functools.cache
def _perf_can_parse_fixture() -> tuple[bool, str]:
    """Probe whether the installed perf binary can read the test fixture."""
    if not TEST_PERF_DATA.exists():
        return False, "test.perf.data fixture not found"
    if not shutil.which("perf"):
        return False, "perf binary not found"
    probe = subprocess.run(
        ["perf", "evlist", "-i", str(TEST_PERF_DATA)],
        capture_output=True,
        timeout=10,
    )
    if probe.returncode != 0:
        return False, "perf cannot parse fixture (incompatible format)"
    return True, ""


@pytest.fixture
def executor() -> PerfExecutor:
    return PerfExecutor()


@pytest.fixture
def perf_data() -> str:
    ok, reason = _perf_can_parse_fixture()
    if not ok:
        pytest.skip(reason)
    return str(TEST_PERF_DATA)
