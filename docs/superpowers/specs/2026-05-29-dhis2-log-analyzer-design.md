# DHIS2 Log Analyzer — Design Spec

## Overview

A terminal CLI tool that connects to an LXD container running DHIS2, reads analytics log files, and renders a timing report in the terminal. Built to be extended with additional log types over time.

**Invocation:**
```
dhis2-analyze-logs hmis
dhis2-analyze-logs hmis --days 14
dhis2-analyze-logs hmis --type analytics   # explicit, analytics is default for now
```

---

## Architecture

```
dhis2-log-analyzer/
├── pyproject.toml
└── src/
    └── dhis2_log_analyzer/
        ├── cli.py              # entry point, argument parsing
        ├── lxc.py              # container access: file listing + streaming
        ├── parsers/
        │   ├── base.py         # shared types and parser protocol
        │   └── analytics.py    # analytics log parser
        └── renderers/
            ├── base.py         # renderer protocol
            └── terminal.py     # rich tables + plotext charts
```

**Package management:** `uv`

**Entry point:** `dhis2-analyze-logs` defined in `pyproject.toml`, maps to `dhis2_log_analyzer.cli:main`.

**Key dependencies:** `rich`, `plotext`

**Flow:**
1. `cli.py` parses arguments, resolves log type
2. `lxc.py` lists and streams log files from the container
3. The appropriate parser (e.g. `analytics.py`) consumes lines and produces structured run data
4. `terminal.py` renders the report

**Extensibility:** Adding a new log type means adding one file under `parsers/`, updating `cli.py` to register it. Nothing else changes.

---

## Log File Access

The tool shells out to `lxc` on the host. The user is assumed to be in the `lxd` group. 

**Reading files:**
- Plain files (`.log`, `.log.1`): `lxc exec <container> -- cat <path>`
- Gzipped rotated files (`.log.N.gz`): `lxc exec <container> -- zcat <path>`

**Log directory:** `/opt/dhis2/logs/` inside the container

**Analytics log files follow this rotation pattern:**
```
dhis-analytics-table.log             # current (always read)
dhis-analytics-table.log.1           # most recent rotated, uncompressed
dhis-analytics-table.log.2.gz        # older, compressed
dhis-analytics-table.log.N.gz        # ...up to 38+ files
dhis-analytics-table.log-YYYYMMDD    # alternate rotation format
```

**File selection:**
- Default (no `--days`): read only `dhis-analytics-table.log`
- `--days N`: run `lxc exec <container> -- ls -la /opt/dhis2/logs/` to get file listing with modification times, select all analytics log files with an mtime within the last N days, read them oldest-first to produce a chronological stream

---

## Data Model

All parsers produce a list of run objects. The analytics parser produces `AnalyticsRun`.

```python
@dataclass
class ProgramUpdate:
    uid: str
    had_data: bool                        # False = "No updated latest event data found"
    population_seconds: float | None      # from "Populating table: analytics_event_<uid>..."

@dataclass
class TableTypeUpdate:
    type_name: str                        # DATA_VALUE, EVENT, COMPLETENESS, etc.
    table_name: str                       # analytics, analytics_event, etc.
    duration_seconds: float               # elapsed time from "Table update done" or "Table update aborted" line
    index_seconds: float | None           # "Created indexes" elapsed minus "Applied aggregation levels" elapsed; None if aborted
    aborted: bool                         # True if "Table update aborted, no table or partitions"
    program_updates: list[ProgramUpdate]  # populated for EVENT type only

@dataclass
class ResourceTableUpdate:
    name: str                             # e.g. analytics_rs_orgunitstructure
    duration_seconds: float               # from "Resource table update done" '...' elapsed

@dataclass
class AnalyticsRun:
    start_time: datetime
    run_type: str                         # "full" | "continuous"
    resource_tables: list[ResourceTableUpdate]
    table_updates: list[TableTypeUpdate]
    total_duration_seconds: float         # wall-clock: last event timestamp minus start_time
    complete: bool                        # False if run has zero "Table update done" entries (caught mid-run)
```

### Parser Notes

**Run boundaries:**
- Full run: starts with `Found N analytics table types` logged by `DefaultAnalyticsTableGenerator`
- Continuous run: starts with `Starting continuous analytics table update` logged by `ContinuousAnalyticsTableJob`
- A new run boundary closes the previous run

**Elapsed times in the log** are cumulative from the start of each table type update (reported by `Clock.java`), not wall-clock durations. To derive individual phase durations:
- `index_seconds` = elapsed at `Created indexes` − elapsed at `Applied aggregation levels`
- `duration_seconds` for a table type = value reported in `Table update done: '<name>': HH:MM:SS.mmm`

**Resource table durations** are reported directly in wall-clock form: `Resource table update done: '<name>' 'HH:MM:SS.mmm'`

**Total run duration** is computed as: timestamp of the last log line in the run minus `start_time`.

---

## Report Layout

Rendered to the terminal via `rich` (tables, styled text) and `plotext` (charts).

### 1. Header
Container name, log files analyzed, date range covered, total number of runs found.

### 2. Latest Run Detail (rich table)
One row per table type. Skips aborted types.

```
Analytics Run: 2026-05-29 01:00:20  [full]  Total: 13m 42s
┌─────────────────────────────┬──────────┬────────────┬────────┐
│ Table Type                  │ Duration │ Index Time │ Status │
├─────────────────────────────┼──────────┼────────────┼────────┤
│ Resource Tables             │  1m 07s  │     —      │  done  │
│ DATA_VALUE                  │ 11m 46s  │   7m 12s   │  done  │
│ COMPLETENESS                │   33s    │    29s     │  done  │
│ TRACKED_ENTITY_INSTANCE     │    0s    │     —      │  done  │
│ EVENT                       │    9s    │     —      │  done  │
└─────────────────────────────┴──────────┴────────────┴────────┘
```

### 3. Run Duration Over Time (plotext line chart)
One point per run. X-axis: date/time. Y-axis: total minutes. Immediately shows whether runs are getting longer over time.

### 4. DATA_VALUE Index Time Over Time (plotext line chart)
Same axes, but showing only the index creation time for the DATA_VALUE table type. This is typically the dominant cost and worth tracking separately.

### 5. Per-Program Event Breakdown (plotext bar chart)
Only rendered when EVENT-type data with per-program timings is present (i.e. the continuous analytics log from a tracker/event server). One bar per program UID, sorted descending by population time. Programs with no updated data are omitted.

---

## Error Handling

All errors produce a clear user-facing message and exit cleanly — no stack traces shown to the user.

| Condition | Behaviour |
|---|---|
| `lxc` not on PATH | `Error: lxc not found. Is lxc installed and are you in the lxd group?` |
| Container not found | `Error: container 'hmis' not found.` |
| Log file missing in container | `Error: no analytics log found at /opt/dhis2/logs/ in container 'hmis'.` |
| Partial/incomplete run at end of log | Include data up to last complete event; mark run as `[incomplete]` in the latest run table |
| No EVENT program data | Omit per-program chart silently |

---

## Out of Scope (v1)

- HTML report output
- Interactive TUI / menus
- Side-by-side multi-container comparison
- Local caching of parsed results
- Any log type other than analytics
