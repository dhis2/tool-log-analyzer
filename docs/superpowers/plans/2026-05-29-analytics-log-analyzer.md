# DHIS2 Analytics Log Analyzer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool (`dhis2-analyze-logs <container>`) that reads DHIS2 analytics logs from an LXD container and renders a timing report in the terminal.

**Architecture:** A thin CLI entry point wires together an LXC file-access module, a pluggable analytics parser, and a terminal renderer. Each component has a clear interface and is independently testable. Adding a future log type means adding one parser file and registering it in `cli.py`.

**Tech Stack:** Python 3.11+, `uv`, `rich`, `plotext`, `pytest`

---

## File Map

```
dhis2-log-analyzer/
├── pyproject.toml
├── tests/
│   ├── __init__.py
│   ├── test_lxc.py
│   └── parsers/
│       ├── __init__.py
│       └── test_analytics.py
└── src/
    └── dhis2_log_analyzer/
        ├── __init__.py
        ├── cli.py                     # entry point, argparse, wires everything together
        ├── lxc.py                     # container access: check, list files, stream lines
        ├── parsers/
        │   ├── __init__.py
        │   ├── base.py                # shared dataclasses used by all parsers
        │   └── analytics.py          # analytics log parser → list[AnalyticsRun]
        └── renderers/
            ├── __init__.py
            └── terminal.py           # rich tables + plotext charts
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/dhis2_log_analyzer/__init__.py`
- Create: `src/dhis2_log_analyzer/parsers/__init__.py`
- Create: `src/dhis2_log_analyzer/renderers/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/parsers/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "dhis2-log-analyzer"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "rich>=13.0.0",
    "plotext>=5.0.0",
]

[project.scripts]
dhis2-analyze-logs = "dhis2_log_analyzer.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/dhis2_log_analyzer"]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
]
```

- [ ] **Step 2: Create directory structure and empty `__init__.py` files**

```bash
mkdir -p src/dhis2_log_analyzer/parsers
mkdir -p src/dhis2_log_analyzer/renderers
mkdir -p tests/parsers

touch src/dhis2_log_analyzer/__init__.py
touch src/dhis2_log_analyzer/parsers/__init__.py
touch src/dhis2_log_analyzer/renderers/__init__.py
touch tests/__init__.py
touch tests/parsers/__init__.py
```

- [ ] **Step 3: Create stub files so the package is importable**

`src/dhis2_log_analyzer/cli.py`:
```python
def main():
    pass
```

`src/dhis2_log_analyzer/lxc.py`:
```python
```

`src/dhis2_log_analyzer/parsers/base.py`:
```python
```

`src/dhis2_log_analyzer/parsers/analytics.py`:
```python
```

`src/dhis2_log_analyzer/renderers/terminal.py`:
```python
```

- [ ] **Step 4: Install with uv and verify importable**

```bash
uv sync --group dev
uv run python -c "import dhis2_log_analyzer; print('ok')"
```

Expected output: `ok`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: scaffold project structure"
```

---

### Task 2: Data model

**Files:**
- Modify: `src/dhis2_log_analyzer/parsers/base.py`
- Create: `tests/parsers/test_base.py`

- [ ] **Step 1: Write the failing test**

`tests/parsers/test_base.py`:
```python
from datetime import datetime
from dhis2_log_analyzer.parsers.base import (
    AnalyticsRun,
    ProgramUpdate,
    ResourceTableUpdate,
    TableTypeUpdate,
)


def test_program_update_with_data():
    p = ProgramUpdate(uid="cGlCzO4q3PJ", had_data=True, population_seconds=0.118)
    assert p.uid == "cGlCzO4q3PJ"
    assert p.had_data is True
    assert p.population_seconds == 0.118


def test_program_update_without_data():
    p = ProgramUpdate(uid="vEUa0tfdgNy", had_data=False, population_seconds=None)
    assert p.population_seconds is None


def test_table_type_update_aborted():
    t = TableTypeUpdate(
        type_name="TRACKED_ENTITY_INSTANCE_EVENTS",
        table_name="analytics_tei_events",
        duration_seconds=0.007,
        index_seconds=None,
        aborted=True,
        program_updates=[],
    )
    assert t.aborted is True
    assert t.index_seconds is None


def test_analytics_run_complete_false_by_default():
    run = AnalyticsRun(
        start_time=datetime(2026, 5, 24, 1, 0, 20),
        run_type="full",
        resource_tables=[],
        table_updates=[],
        total_duration_seconds=0.0,
        complete=False,
    )
    assert run.complete is False
    assert run.run_type == "full"
```

- [ ] **Step 2: Run to confirm it fails**

```bash
uv run pytest tests/parsers/test_base.py -v
```

Expected: `ImportError` — classes not defined yet.

- [ ] **Step 3: Implement `parsers/base.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ProgramUpdate:
    uid: str
    had_data: bool
    population_seconds: float | None


@dataclass
class TableTypeUpdate:
    type_name: str
    table_name: str
    duration_seconds: float
    index_seconds: float | None
    aborted: bool
    program_updates: list[ProgramUpdate] = field(default_factory=list)


@dataclass
class ResourceTableUpdate:
    name: str
    duration_seconds: float


@dataclass
class AnalyticsRun:
    start_time: datetime
    run_type: str                      # "full" | "continuous"
    resource_tables: list[ResourceTableUpdate] = field(default_factory=list)
    table_updates: list[TableTypeUpdate] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    complete: bool = False
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/parsers/test_base.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/dhis2_log_analyzer/parsers/base.py tests/parsers/test_base.py
git commit -m "feat: add analytics run data model"
```

---

### Task 3: LXC access module

**Files:**
- Modify: `src/dhis2_log_analyzer/lxc.py`
- Create: `tests/test_lxc.py`

- [ ] **Step 1: Write failing tests**

`tests/test_lxc.py`:
```python
import subprocess
import sys
import time
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from dhis2_log_analyzer.lxc import (
    LogFile,
    check_container_exists,
    check_lxc_available,
    list_log_files,
    stream_lines,
)


def test_check_lxc_available_exits_when_not_found():
    with patch("dhis2_log_analyzer.lxc.shutil.which", return_value=None):
        with pytest.raises(SystemExit) as exc:
            check_lxc_available()
    assert "lxc not found" in str(exc.value)


def test_check_lxc_available_passes_when_found():
    with patch("dhis2_log_analyzer.lxc.shutil.which", return_value="/usr/bin/lxc"):
        check_lxc_available()  # should not raise


def test_check_container_exists_exits_on_nonzero_returncode():
    with patch("dhis2_log_analyzer.lxc.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(SystemExit) as exc:
            check_container_exists("missing")
    assert "missing" in str(exc.value)


def test_check_container_exists_passes_on_zero_returncode():
    with patch("dhis2_log_analyzer.lxc.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        check_container_exists("hmis")  # should not raise


def test_list_log_files_returns_sorted_by_mtime():
    find_output = (
        "1000.0 /opt/dhis2/logs/dhis-analytics-table.log.1\n"
        "2000.0 /opt/dhis2/logs/dhis-analytics-table.log\n"
    )
    now = 3000.0
    with patch("dhis2_log_analyzer.lxc.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=find_output, returncode=0)
        files = list_log_files("hmis", "/opt/dhis2/logs/", "dhis-analytics-table.log*", days=5, now=now)
    assert len(files) == 2
    assert files[0].path == "/opt/dhis2/logs/dhis-analytics-table.log.1"
    assert files[1].path == "/opt/dhis2/logs/dhis-analytics-table.log"


def test_list_log_files_filters_by_days():
    now = 10000.0
    cutoff = now - 1 * 86400  # 1 day
    find_output = (
        f"{cutoff - 1:.1f} /opt/dhis2/logs/dhis-analytics-table.log.5.gz\n"  # too old
        f"{cutoff + 1:.1f} /opt/dhis2/logs/dhis-analytics-table.log.1\n"     # within range
        f"{now:.1f} /opt/dhis2/logs/dhis-analytics-table.log\n"              # within range
    )
    with patch("dhis2_log_analyzer.lxc.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=find_output, returncode=0)
        files = list_log_files("hmis", "/opt/dhis2/logs/", "dhis-analytics-table.log*", days=1, now=now)
    assert len(files) == 2
    paths = [f.path for f in files]
    assert "/opt/dhis2/logs/dhis-analytics-table.log.5.gz" not in paths


def test_stream_lines_uses_cat_for_plain_files():
    mock_proc = MagicMock()
    mock_proc.stdout = iter(["line1\n", "line2\n"])
    with patch("dhis2_log_analyzer.lxc.subprocess.Popen", return_value=mock_proc) as mock_popen:
        lines = list(stream_lines("hmis", "/opt/dhis2/logs/dhis-analytics-table.log"))
    mock_popen.assert_called_once_with(
        ["lxc", "exec", "hmis", "--", "cat", "/opt/dhis2/logs/dhis-analytics-table.log"],
        stdout=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert lines == ["line1", "line2"]


def test_stream_lines_uses_zcat_for_gz_files():
    mock_proc = MagicMock()
    mock_proc.stdout = iter(["line1\n"])
    with patch("dhis2_log_analyzer.lxc.subprocess.Popen", return_value=mock_proc) as mock_popen:
        list(stream_lines("hmis", "/opt/dhis2/logs/dhis-analytics-table.log.2.gz"))
    cmd = mock_popen.call_args[0][0]
    assert "zcat" in cmd
    assert "cat" not in cmd
```

- [ ] **Step 2: Run to confirm they fail**

```bash
uv run pytest tests/test_lxc.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `lxc.py`**

```python
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class LogFile:
    path: str
    mtime: float


def check_lxc_available() -> None:
    if shutil.which("lxc") is None:
        sys.exit("Error: lxc not found. Is lxc installed and are you in the lxd group?")


def check_container_exists(container: str) -> None:
    result = subprocess.run(
        ["lxc", "info", container],
        capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(f"Error: container '{container}' not found.")


def list_log_files(
    container: str,
    log_dir: str,
    pattern: str,
    days: int,
    now: float | None = None,
) -> list[LogFile]:
    if now is None:
        now = time.time()
    cutoff = now - days * 86400

    result = subprocess.run(
        ["lxc", "exec", container, "--", "find", log_dir, "-name", pattern, "-printf", "%T@ %p\n"],
        capture_output=False,
        text=True,
        stdout=subprocess.PIPE,
    )

    files: list[LogFile] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        mtime_str, path = line.split(" ", 1)
        mtime = float(mtime_str)
        if mtime >= cutoff:
            files.append(LogFile(path=path.strip(), mtime=mtime))

    return sorted(files, key=lambda f: f.mtime)


def stream_lines(container: str, path: str) -> Iterator[str]:
    cmd = (
        ["lxc", "exec", container, "--", "zcat", path]
        if path.endswith(".gz")
        else ["lxc", "exec", container, "--", "cat", path]
    )
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, errors="replace")
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
    finally:
        proc.wait()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_lxc.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/dhis2_log_analyzer/lxc.py tests/test_lxc.py
git commit -m "feat: add LXC container access module"
```

---

### Task 4: Analytics log parser

**Files:**
- Modify: `src/dhis2_log_analyzer/parsers/analytics.py`
- Create: `tests/parsers/test_analytics.py`

The parser reads log lines sequentially, tracking state across run boundaries. Key patterns extracted via regex:

| Pattern | What it signals |
|---|---|
| `Found N analytics table types.*DefaultAnalyticsTableGenerator` | Full run start |
| `Starting continuous analytics table update` | Continuous run start |
| `Resource table update done: 'name' 'HH:MM:SS.mmm'` | Resource table timing |
| `Starting update of type: TYPE, table name: 'name'` | Table type update begin |
| `Applied aggregation levels: HH:MM:SS.mmm` | Phase elapsed (for index calc) |
| `Created indexes: HH:MM:SS.mmm` | Phase elapsed (for index calc) |
| `Table update done: 'name': HH:MM:SS.mmm` | Table type complete |
| `Table update aborted.*'name': HH:MM:SS.mmm` | Table type aborted |
| `No updated latest event data found for program: 'UID'` | Program, no data |
| `Added latest event analytics partition for program: 'UID'` | Program, has data |
| `Populating table: 'analytics_event_<uid>_N_temp' in: X sec.` | Per-program timing |

Elapsed time strings (`HH:MM:SS.mmm`) represent time since the **start of the current table type update**, not wall-clock. Index time = `Created indexes` elapsed − `Applied aggregation levels` elapsed.

- [ ] **Step 1: Write failing tests**

`tests/parsers/test_analytics.py`:
```python
from datetime import datetime

from dhis2_log_analyzer.parsers.analytics import parse, parse_elapsed


# ── helpers ──────────────────────────────────────────────────────────────────

FULL_RUN_LINES = [
    "* INFO  2026-05-24T01:00:20,025 Found 11 analytics table types: [DATA_VALUE] (DefaultAnalyticsTableGenerator.java [pool-13-thread-269])",
    "* INFO  2026-05-24T01:00:20,460 Generating resource table: 'analytics_rs_orgunitstructure' (JdbcResourceTableStore.java [pool-13-thread-269])",
    "* INFO  2026-05-24T01:00:29,391 Resource table update done: 'analytics_rs_orgunitstructure' '00:00:08.930' (JdbcResourceTableStore.java [pool-13-thread-269])",
    "* INFO  2026-05-24T01:01:27,296 Starting update of type: DATA_VALUE, table name: 'analytics', parallel jobs: 19: 00:00:00.000 (Clock.java [pool-13-thread-269])",
    "* INFO  2026-05-24T01:05:48,129 Applied aggregation levels: 00:04:20.203 (Clock.java [pool-13-thread-269])",
    "* INFO  2026-05-24T01:13:00,522 Created indexes: 00:11:32.596 (Clock.java [pool-13-thread-269])",
    "* INFO  2026-05-24T01:13:13,768 Table update done: 'analytics': 00:11:45.842 (Clock.java [pool-13-thread-269])",
    "* INFO  2026-05-24T01:13:13,769 Starting update of type: TRACKED_ENTITY_INSTANCE_EVENTS, table name: 'analytics_tei_events', parallel jobs: 19: 00:00:00.000 (Clock.java [pool-13-thread-269])",
    "* INFO  2026-05-24T01:13:13,776 Table update aborted, no table or partitions to be updated: 'analytics_tei_events': 00:00:00.007 (Clock.java [pool-13-thread-269])",
]

CONTINUOUS_RUN_LINES = [
    "* INFO  2025-09-12T16:26:20,030 Starting continuous analytics table update, current time: '2025-09-12T16:26:20' (ContinuousAnalyticsTableJob.java [pool-14-thread-52])",
    "* INFO  2025-09-12T16:26:20,031 Found 11 analytics table types: [EVENT] (DefaultAnalyticsTableGenerator.java [pool-14-thread-52])",
    "* INFO  2025-09-12T16:26:29,820 Starting update of type: EVENT, table name: 'analytics_event', parallel jobs: 8: 00:00:00.000 (Clock.java [pool-14-thread-52])",
    "* INFO  2025-09-12T16:26:29,825 No updated latest event data found for program: 'vEUa0tfdgNy' with start: '2025-09-12T15:26:20' and end: '2025-09-12T16:26:20 (JdbcEventAnalyticsTableManager.java [pool-14-thread-52])",
    "* INFO  2025-09-12T16:26:29,837 Added latest event analytics partition for program: 'cGlCzO4q3PJ' with start: '2025-09-12T01:26:20' and end: '2025-09-12T16:26:20' (JdbcEventAnalyticsTableManager.java [pool-14-thread-52])",
    "* INFO  2025-09-12T16:26:29,859 Added latest event analytics partition for program: 'K44XOBXX4tE' with start: '2025-09-12T01:26:20' and end: '2025-09-12T16:26:20' (JdbcEventAnalyticsTableManager.java [pool-14-thread-52])",
    "* INFO  2025-09-12T16:26:30,113 Populating table: 'analytics_event_cglczo4q3pj_0_temp' in: 0.118378 sec. (AbstractJdbcTableManager.java [ForkJoinPool-1232-worker-2])",
    "* INFO  2025-09-12T16:26:37,200 Populating table: 'analytics_event_k44xobxx4te_0_temp' in: 7.205030 sec. (AbstractJdbcTableManager.java [ForkJoinPool-1232-worker-1])",
    "* INFO  2025-09-12T16:26:38,482 Table update done: 'analytics_event': 00:00:08.661 (Clock.java [pool-14-thread-52])",
    "* INFO  2025-09-12T16:26:38,483 Starting update of type: ENROLLMENT, table name: 'analytics_enrollment', parallel jobs: 8: 00:00:00.000 (Clock.java [pool-14-thread-52])",
    "* INFO  2025-09-12T16:26:38,484 Table update aborted, no table or partitions to be updated: 'analytics_enrollment': 00:00:00.000 (Clock.java [pool-14-thread-52])",
]


# ── parse_elapsed ─────────────────────────────────────────────────────────────

def test_parse_elapsed_seconds_only():
    assert parse_elapsed("00:00:08.930") == pytest.approx(8.930)


def test_parse_elapsed_minutes_and_seconds():
    assert parse_elapsed("00:04:20.203") == pytest.approx(260.203)


def test_parse_elapsed_hours_minutes_seconds():
    assert parse_elapsed("00:11:45.842") == pytest.approx(705.842)


# ── full run ──────────────────────────────────────────────────────────────────

def test_full_run_detected():
    runs = parse(iter(FULL_RUN_LINES))
    assert len(runs) == 1
    assert runs[0].run_type == "full"


def test_full_run_start_time():
    runs = parse(iter(FULL_RUN_LINES))
    assert runs[0].start_time == datetime(2026, 5, 24, 1, 0, 20, 25000)


def test_full_run_resource_tables():
    runs = parse(iter(FULL_RUN_LINES))
    assert len(runs[0].resource_tables) == 1
    rt = runs[0].resource_tables[0]
    assert rt.name == "analytics_rs_orgunitstructure"
    assert rt.duration_seconds == pytest.approx(8.930)


def test_full_run_table_update_done():
    runs = parse(iter(FULL_RUN_LINES))
    done = [t for t in runs[0].table_updates if not t.aborted]
    assert len(done) == 1
    assert done[0].type_name == "DATA_VALUE"
    assert done[0].table_name == "analytics"
    assert done[0].duration_seconds == pytest.approx(705.842)


def test_full_run_index_seconds():
    runs = parse(iter(FULL_RUN_LINES))
    data_value = next(t for t in runs[0].table_updates if t.type_name == "DATA_VALUE")
    # Created indexes elapsed (692.596) - Applied aggregation levels elapsed (260.203)
    assert data_value.index_seconds == pytest.approx(692.596 - 260.203, rel=1e-3)


def test_full_run_aborted_table_type():
    runs = parse(iter(FULL_RUN_LINES))
    aborted = [t for t in runs[0].table_updates if t.aborted]
    assert len(aborted) == 1
    assert aborted[0].type_name == "TRACKED_ENTITY_INSTANCE_EVENTS"
    assert aborted[0].duration_seconds == pytest.approx(0.007)
    assert aborted[0].index_seconds is None


def test_full_run_is_complete():
    runs = parse(iter(FULL_RUN_LINES))
    assert runs[0].complete is True


def test_full_run_total_duration():
    runs = parse(iter(FULL_RUN_LINES))
    # last timestamp 01:13:13,776 minus start 01:00:20,025
    expected = (
        datetime(2026, 5, 24, 1, 13, 13, 776000)
        - datetime(2026, 5, 24, 1, 0, 20, 25000)
    ).total_seconds()
    assert runs[0].total_duration_seconds == pytest.approx(expected)


# ── continuous run ────────────────────────────────────────────────────────────

def test_continuous_run_detected():
    runs = parse(iter(CONTINUOUS_RUN_LINES))
    assert len(runs) == 1
    assert runs[0].run_type == "continuous"


def test_continuous_run_per_program_no_data():
    runs = parse(iter(CONTINUOUS_RUN_LINES))
    event = next(t for t in runs[0].table_updates if t.type_name == "EVENT")
    no_data = [p for p in event.program_updates if not p.had_data]
    assert len(no_data) == 1
    assert no_data[0].uid == "vEUa0tfdgNy"
    assert no_data[0].population_seconds is None


def test_continuous_run_per_program_with_data_and_timing():
    runs = parse(iter(CONTINUOUS_RUN_LINES))
    event = next(t for t in runs[0].table_updates if t.type_name == "EVENT")
    with_data = {p.uid: p for p in event.program_updates if p.had_data}
    assert "cGlCzO4q3PJ" in with_data
    assert with_data["cGlCzO4q3PJ"].population_seconds == pytest.approx(0.118378)
    assert "K44XOBXX4tE" in with_data
    assert with_data["K44XOBXX4tE"].population_seconds == pytest.approx(7.205030)


# ── multi-run ─────────────────────────────────────────────────────────────────

def test_two_consecutive_runs_parsed():
    lines = FULL_RUN_LINES + [
        "* INFO  2026-05-25T01:00:20,025 Found 11 analytics table types: [DATA_VALUE] (DefaultAnalyticsTableGenerator.java [pool-13-thread-6])",
        "* INFO  2026-05-25T01:01:27,296 Starting update of type: DATA_VALUE, table name: 'analytics', parallel jobs: 19: 00:00:00.000 (Clock.java [pool-13-thread-6])",
        "* INFO  2026-05-25T01:12:00,000 Table update done: 'analytics': 00:10:32.000 (Clock.java [pool-13-thread-6])",
    ]
    runs = parse(iter(lines))
    assert len(runs) == 2
    assert runs[1].run_type == "full"
    assert runs[1].start_time.day == 25


# ── incomplete run ────────────────────────────────────────────────────────────

def test_incomplete_run_has_no_table_update_done():
    lines = [
        "* INFO  2026-05-24T01:00:20,025 Found 11 analytics table types: [DATA_VALUE] (DefaultAnalyticsTableGenerator.java [pool-13-thread-269])",
        "* INFO  2026-05-24T01:01:27,296 Starting update of type: DATA_VALUE, table name: 'analytics', parallel jobs: 19: 00:00:00.000 (Clock.java [pool-13-thread-269])",
    ]
    runs = parse(iter(lines))
    assert len(runs) == 1
    assert runs[0].complete is False
```

- [ ] **Step 2: Run to confirm they fail**

```bash
uv run pytest tests/parsers/test_analytics.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `parsers/analytics.py`**

```python
from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime

from dhis2_log_analyzer.parsers.base import (
    AnalyticsRun,
    ProgramUpdate,
    ResourceTableUpdate,
    TableTypeUpdate,
)

# ── patterns ──────────────────────────────────────────────────────────────────

_LINE = re.compile(r"^\* INFO\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},\d+)\s+(.+)$")
_FULL_RUN = re.compile(r"Found \d+ analytics table types:.*DefaultAnalyticsTableGenerator")
_CONTINUOUS_RUN = re.compile(r"Starting continuous analytics table update")
_RESOURCE_DONE = re.compile(r"Resource table update done: '([^']+)' '(\d{2}:\d{2}:\d{2}\.\d+)'")
_TABLE_START = re.compile(r"Starting update of type: (\w+), table name: '([^']+)'")
_TABLE_DONE = re.compile(r"Table update done: '([^']+)': (\d{2}:\d{2}:\d{2}\.\d+)")
_TABLE_ABORTED = re.compile(r"Table update aborted[^:]*: '([^']+)': (\d{2}:\d{2}:\d{2}\.\d+)")
_AGG_LEVELS = re.compile(r"Applied aggregation levels: (\d{2}:\d{2}:\d{2}\.\d+)")
_INDEXES = re.compile(r"Created indexes: (\d{2}:\d{2}:\d{2}\.\d+)")
_PROG_NO_DATA = re.compile(r"No updated latest event data found for program: '([^']+)'")
_PROG_WITH_DATA = re.compile(r"Added latest event analytics partition for program: '([^']+)'")
_PROG_POPULATE = re.compile(
    r"Populating table: 'analytics_event_([a-z0-9]+)_\d+_temp' in: ([\d.]+) sec\."
)


# ── helpers ───────────────────────────────────────────────────────────────────

def parse_elapsed(elapsed: str) -> float:
    """Parse 'HH:MM:SS.mmm' to total seconds."""
    h, m, s = elapsed.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def _parse_timestamp(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S,%f")


# ── parser ────────────────────────────────────────────────────────────────────

def parse(lines: Iterable[str]) -> list[AnalyticsRun]:
    runs: list[AnalyticsRun] = []

    current_run: AnalyticsRun | None = None
    current_table: TableTypeUpdate | None = None
    last_ts: datetime | None = None
    agg_elapsed: float | None = None  # elapsed at "Applied aggregation levels"

    def _close_table() -> None:
        nonlocal current_table, agg_elapsed
        if current_table is not None and current_run is not None:
            current_run.table_updates.append(current_table)
        current_table = None
        agg_elapsed = None

    def _close_run() -> None:
        nonlocal current_run, last_ts
        if current_run is not None:
            _close_table()
            if last_ts is not None:
                current_run.total_duration_seconds = (
                    last_ts - current_run.start_time
                ).total_seconds()
            current_run.complete = any(
                not t.aborted for t in current_run.table_updates
            )
            runs.append(current_run)
        current_run = None
        last_ts = None

    for line in lines:
        m = _LINE.match(line)
        if not m:
            continue
        ts_str, msg = m.group(1), m.group(2)
        ts = _parse_timestamp(ts_str)
        last_ts = ts

        if _FULL_RUN.search(msg):
            _close_run()
            current_run = AnalyticsRun(start_time=ts, run_type="full")
            continue

        if _CONTINUOUS_RUN.search(msg):
            _close_run()
            current_run = AnalyticsRun(start_time=ts, run_type="continuous")
            continue

        if current_run is None:
            continue

        if m2 := _RESOURCE_DONE.search(msg):
            current_run.resource_tables.append(
                ResourceTableUpdate(name=m2.group(1), duration_seconds=parse_elapsed(m2.group(2)))
            )
            continue

        if m2 := _TABLE_START.search(msg):
            _close_table()
            current_table = TableTypeUpdate(
                type_name=m2.group(1),
                table_name=m2.group(2),
                duration_seconds=0.0,
                index_seconds=None,
                aborted=False,
            )
            continue

        if current_table is None:
            continue

        if m2 := _AGG_LEVELS.search(msg):
            agg_elapsed = parse_elapsed(m2.group(1))
            continue

        if m2 := _INDEXES.search(msg):
            if agg_elapsed is not None:
                current_table.index_seconds = parse_elapsed(m2.group(1)) - agg_elapsed
            continue

        if m2 := _TABLE_DONE.search(msg):
            current_table.duration_seconds = parse_elapsed(m2.group(2))
            _close_table()
            continue

        if m2 := _TABLE_ABORTED.search(msg):
            current_table.duration_seconds = parse_elapsed(m2.group(2))
            current_table.aborted = True
            _close_table()
            continue

        if current_table.type_name == "EVENT":
            if m2 := _PROG_NO_DATA.search(msg):
                current_table.program_updates.append(
                    ProgramUpdate(uid=m2.group(1), had_data=False, population_seconds=None)
                )
                continue

            if m2 := _PROG_WITH_DATA.search(msg):
                current_table.program_updates.append(
                    ProgramUpdate(uid=m2.group(1), had_data=True, population_seconds=None)
                )
                continue

            if m2 := _PROG_POPULATE.search(msg):
                uid_lower = m2.group(1)
                seconds = float(m2.group(2))
                for prog in current_table.program_updates:
                    if prog.uid.lower() == uid_lower and prog.had_data:
                        prog.population_seconds = seconds
                        break
                continue

    _close_run()
    return runs
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/parsers/test_analytics.py -v
```

Expected: all tests pass. If `test_parse_elapsed_*` tests show `NameError` for `pytest`, add `import pytest` at the top of the test file.

- [ ] **Step 5: Commit**

```bash
git add src/dhis2_log_analyzer/parsers/analytics.py tests/parsers/test_analytics.py
git commit -m "feat: implement analytics log parser"
```

---

### Task 5: Terminal renderer

**Files:**
- Modify: `src/dhis2_log_analyzer/renderers/terminal.py`
- Create: `tests/test_terminal.py`

The renderer has one testable pure function (`format_duration`) and one side-effectful function (`render`) that is tested for non-crash behaviour only.

- [ ] **Step 1: Write failing tests**

`tests/test_terminal.py`:
```python
from datetime import datetime
from io import StringIO
from unittest.mock import patch

from dhis2_log_analyzer.parsers.base import AnalyticsRun, TableTypeUpdate
from dhis2_log_analyzer.renderers.terminal import format_duration, render


def test_format_duration_seconds_only():
    assert format_duration(33.0) == "33s"


def test_format_duration_minutes_and_seconds():
    assert format_duration(67.0) == "1m 07s"


def test_format_duration_sub_second_rounds_to_zero():
    assert format_duration(0.5) == "1s"


def test_format_duration_exact_minute():
    assert format_duration(120.0) == "2m 00s"


def _make_run(run_type: str = "full", complete: bool = True) -> AnalyticsRun:
    return AnalyticsRun(
        start_time=datetime(2026, 5, 29, 1, 0, 20),
        run_type=run_type,
        resource_tables=[],
        table_updates=[
            TableTypeUpdate(
                type_name="DATA_VALUE",
                table_name="analytics",
                duration_seconds=705.842,
                index_seconds=432.393,
                aborted=False,
            )
        ],
        total_duration_seconds=822.0,
        complete=complete,
    )


def test_render_does_not_raise_with_single_run():
    runs = [_make_run()]
    render(runs, container="hmis", log_files=["dhis-analytics-table.log"])


def test_render_does_not_raise_with_multiple_runs():
    runs = [_make_run(), _make_run()]
    render(runs, container="hmis", log_files=["dhis-analytics-table.log"])


def test_render_does_not_raise_with_incomplete_run():
    runs = [_make_run(complete=False)]
    render(runs, container="hmis", log_files=["dhis-analytics-table.log"])
```

- [ ] **Step 2: Run to confirm they fail**

```bash
uv run pytest tests/test_terminal.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `renderers/terminal.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table
from rich import box
import plotext as plt

from dhis2_log_analyzer.parsers.base import AnalyticsRun

_console = Console()


def format_duration(seconds: float) -> str:
    """Format seconds as '1m 07s' or '33s'."""
    total = max(1, round(seconds))
    if total < 60:
        return f"{total}s"
    m, s = divmod(total, 60)
    return f"{m}m {s:02d}s"


def render(runs: list[AnalyticsRun], container: str, log_files: list[str]) -> None:
    _render_header(runs, container, log_files)
    _render_latest_run(runs[-1])
    if len(runs) > 1:
        _render_duration_chart(runs)
        _render_index_chart(runs)
    _render_program_breakdown(runs[-1])


def _render_header(runs: list[AnalyticsRun], container: str, log_files: list[str]) -> None:
    _console.print()
    _console.print(f"[bold]DHIS2 Analytics Log Report[/bold]")
    _console.print(f"  Container : [cyan]{container}[/cyan]")
    _console.print(f"  Log files : {', '.join(log_files)}")
    if runs:
        start = runs[0].start_time.strftime("%Y-%m-%d")
        end = runs[-1].start_time.strftime("%Y-%m-%d")
        _console.print(f"  Date range: {start} → {end}")
    _console.print(f"  Runs found: {len(runs)}")
    _console.print()


def _render_latest_run(run: AnalyticsRun) -> None:
    label = "[incomplete]" if not run.complete else f"[{run.run_type}]"
    total = format_duration(run.total_duration_seconds)
    _console.print(
        f"[bold]Latest run:[/bold] {run.start_time.strftime('%Y-%m-%d %H:%M:%S')}  "
        f"{label}  Total: {total}"
    )
    _console.print()

    table = Table(box=box.SIMPLE_HEAD, show_footer=False)
    table.add_column("Table Type", style="bold")
    table.add_column("Duration", justify="right")
    table.add_column("Index Time", justify="right")
    table.add_column("Status", justify="center")

    if run.resource_tables:
        total_rs = sum(r.duration_seconds for r in run.resource_tables)
        table.add_row("Resource Tables", format_duration(total_rs), "—", "done")

    for t in run.table_updates:
        status = "abort" if t.aborted else "done"
        index = format_duration(t.index_seconds) if t.index_seconds is not None else "—"
        table.add_row(t.type_name, format_duration(t.duration_seconds), index, status)

    _console.print(table)


def _render_duration_chart(runs: list[AnalyticsRun]) -> None:
    labels = [r.start_time.strftime("%m-%d") for r in runs]
    values = [r.total_duration_seconds / 60 for r in runs]

    plt.clf()
    plt.plot(values, label="Total duration (min)")
    plt.xticks(range(len(labels)), labels)
    plt.title("Run Duration Over Time")
    plt.ylabel("minutes")
    plt.show()


def _render_index_chart(runs: list[AnalyticsRun]) -> None:
    data = []
    for r in runs:
        for t in r.table_updates:
            if t.type_name == "DATA_VALUE" and t.index_seconds is not None:
                data.append((r.start_time, t.index_seconds))

    if not data:
        return

    labels = [d[0].strftime("%m-%d") for d in data]
    values = [d[1] / 60 for d in data]

    plt.clf()
    plt.plot(values, label="Index time (min)")
    plt.xticks(range(len(labels)), labels)
    plt.title("DATA_VALUE Index Creation Time Over Time")
    plt.ylabel("minutes")
    plt.show()


def _render_program_breakdown(run: AnalyticsRun) -> None:
    event_updates = [
        t for t in run.table_updates
        if t.type_name == "EVENT" and t.program_updates
    ]
    if not event_updates:
        return

    programs = [
        p for t in event_updates
        for p in t.program_updates
        if p.had_data and p.population_seconds is not None
    ]
    if not programs:
        return

    programs.sort(key=lambda p: p.population_seconds, reverse=True)

    _console.print("[bold]Per-Program Event Breakdown (latest run)[/bold]")
    plt.clf()
    plt.bar(
        [p.uid for p in programs],
        [p.population_seconds for p in programs],
    )
    plt.title("Event Table Population Time by Program")
    plt.ylabel("seconds")
    plt.show()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
uv run pytest tests/test_terminal.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/dhis2_log_analyzer/renderers/terminal.py tests/test_terminal.py
git commit -m "feat: implement terminal renderer"
```

---

### Task 6: CLI entry point

**Files:**
- Modify: `src/dhis2_log_analyzer/cli.py`

No unit tests for `cli.py` — it is integration glue. Verify manually with the sample log files already in the project.

- [ ] **Step 1: Implement `cli.py`**

```python
from __future__ import annotations

import sys
from itertools import chain

from dhis2_log_analyzer import lxc
from dhis2_log_analyzer.parsers import analytics
from dhis2_log_analyzer.renderers import terminal

_LOG_DIR = "/opt/dhis2/logs/"
_ANALYTICS_LOG = "dhis-analytics-table.log"
_ANALYTICS_PATTERN = "dhis-analytics-table.log*"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="dhis2-analyze-logs",
        description="Analyze DHIS2 logs from an LXD container",
    )
    parser.add_argument("container", help="LXD container name")
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        metavar="N",
        help="Include rotated logs from the last N days (default: current log only)",
    )
    parser.add_argument(
        "--type",
        dest="log_type",
        default="analytics",
        choices=["analytics"],
        help="Log type to analyze (default: analytics)",
    )
    args = parser.parse_args()

    lxc.check_lxc_available()
    lxc.check_container_exists(args.container)

    if args.days > 0:
        log_files = lxc.list_log_files(
            args.container, _LOG_DIR, _ANALYTICS_PATTERN, days=args.days
        )
        if not log_files:
            sys.exit(
                f"Error: no analytics log found at {_LOG_DIR} in container '{args.container}'."
            )
    else:
        log_files = [lxc.LogFile(path=_LOG_DIR + _ANALYTICS_LOG, mtime=0.0)]

    all_lines = chain.from_iterable(
        lxc.stream_lines(args.container, lf.path) for lf in log_files
    )

    runs = analytics.parse(all_lines)

    if not runs:
        sys.exit("No analytics runs found in the log files.")

    log_file_names = [lf.path.rsplit("/", 1)[-1] for lf in log_files]
    terminal.render(runs, args.container, log_file_names)
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Smoke test against the sample log files already in the project**

The project has two local sample logs. Test the parser directly against them (bypassing LXC):

```bash
uv run python - <<'EOF'
from dhis2_log_analyzer.parsers import analytics
from dhis2_log_analyzer.renderers import terminal

with open("dhis-analytics-table.log") as f:
    runs = analytics.parse(f)

print(f"Aggregate server: {len(runs)} runs parsed")
terminal.render(runs, container="local-test", log_files=["dhis-analytics-table.log"])
EOF
```

Expected: report renders without error, showing run count, latest run table, and charts.

```bash
uv run python - <<'EOF'
from dhis2_log_analyzer.parsers import analytics
from dhis2_log_analyzer.renderers import terminal

with open("event-server.log") as f:
    runs = analytics.parse(f)

print(f"Event server: {len(runs)} runs parsed")
terminal.render(runs, container="local-test", log_files=["event-server.log"])
EOF
```

Expected: same, plus per-program breakdown chart.

- [ ] **Step 4: Commit**

```bash
git add src/dhis2_log_analyzer/cli.py
git commit -m "feat: wire up CLI entry point"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| `dhis2-analyze-logs <container>` entry point | Task 6 |
| `--days N` to include rotated logs | Tasks 3 + 6 |
| `--type analytics` flag (default) | Task 6 |
| LXC file access via `lxc exec` | Task 3 |
| `.gz` files read via `zcat` | Task 3 |
| File selection by mtime | Task 3 |
| AnalyticsRun data model | Task 2 |
| Full run detection | Task 4 |
| Continuous run detection | Task 4 |
| Resource table timings | Task 4 |
| Table type duration from "Table update done" | Task 4 |
| Index time calculation | Task 4 |
| Aborted table types | Task 4 |
| Per-program event timings | Task 4 |
| Incomplete run detection | Task 4 |
| Header with container/files/range/count | Task 5 |
| Latest run rich table | Task 5 |
| Run duration over time chart | Task 5 |
| DATA_VALUE index time chart | Task 5 |
| Per-program bar chart | Task 5 |
| Error: lxc not available | Task 3 |
| Error: container not found | Task 3 |
| Error: no log files found | Task 6 |
| Incomplete run marked in output | Task 5 |
| `uv` for package management | Task 1 |

All spec requirements are covered. No gaps found.
