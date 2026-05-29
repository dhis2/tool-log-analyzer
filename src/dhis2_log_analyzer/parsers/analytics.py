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
    agg_elapsed: float | None = None
    continuous_started_ts: datetime | None = None

    def _close_table(finalized: bool = False) -> None:
        nonlocal current_table, agg_elapsed
        if current_table is not None and current_run is not None and finalized:
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

        if _FULL_RUN.search(msg):
            # "Found N analytics table types" appears both as the start of a nightly full
            # run AND as an informational init line emitted ~1ms after "Starting continuous
            # analytics table update". Distinguish by time proximity: if this line appears
            # within 5 seconds of the continuous run start, it is informational only.
            if (
                continuous_started_ts is not None
                and (ts - continuous_started_ts).total_seconds() < 5
            ):
                continue
            _close_run()
            last_ts = ts
            current_run = AnalyticsRun(start_time=ts, run_type="full")
            continue

        if _CONTINUOUS_RUN.search(msg):
            _close_run()
            last_ts = ts
            continuous_started_ts = ts
            current_run = AnalyticsRun(start_time=ts, run_type="continuous")
            continue

        last_ts = ts  # only update for non-boundary lines

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
            _close_table(finalized=True)
            continue

        if m2 := _TABLE_ABORTED.search(msg):
            current_table.duration_seconds = parse_elapsed(m2.group(2))
            current_table.aborted = True
            _close_table(finalized=True)
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
                        # Accumulate: full runs have multiple year partitions per program
                        prog.population_seconds = (prog.population_seconds or 0.0) + seconds
                        break
                else:
                    # Full run: no preceding "Added latest" line — create on the fly
                    current_table.program_updates.append(
                        ProgramUpdate(uid=uid_lower, had_data=True, population_seconds=seconds)
                    )
                continue

    _close_run()
    return runs
