from __future__ import annotations

import shutil
from statistics import mean as _mean

from rich import box
from rich.console import Console
from rich.table import Table
import plotext as plt

from dhis2_log_analyzer.parsers.base import AnalyticsRun

_console = Console()
_CHART_HEIGHT = 20


def _chart_size() -> tuple[int, int]:
    cols = shutil.get_terminal_size().columns
    return cols, _CHART_HEIGHT


def format_duration(seconds: float) -> str:
    """Format seconds as '1m 07s' or '33s'."""
    total = max(1, round(seconds))
    if total < 60:
        return f"{total}s"
    m, s = divmod(total, 60)
    return f"{m}m {s:02d}s"


def render(runs: list[AnalyticsRun], container: str, log_files: list[str]) -> None:
    _render_header(runs, container, log_files)
    _render_latest_run_header(runs[-1])
    _render_summary_table(runs)
    if len(runs) > 1:
        _render_duration_chart(runs)
        _render_index_chart(runs)
    _render_program_breakdown(runs[-1])


def _render_header(runs: list[AnalyticsRun], container: str, log_files: list[str]) -> None:
    _console.print()
    _console.print("[bold]DHIS2 Analytics Log Report[/bold]")
    _console.print(f"  Container : [cyan]{container}[/cyan]")
    _console.print(f"  Log files : {', '.join(log_files)}")
    if runs:
        start = runs[0].start_time.strftime("%Y-%m-%d")
        end = runs[-1].start_time.strftime("%Y-%m-%d")
        _console.print(f"  Date range: {start} → {end}")
    n_full = sum(1 for r in runs if r.run_type == "full")
    n_cont = sum(1 for r in runs if r.run_type == "continuous")
    parts = []
    if n_full:
        parts.append(f"full: {n_full}")
    if n_cont:
        parts.append(f"continuous: {n_cont}")
    suffix = f"  ({', '.join(parts)})" if parts else ""
    _console.print(f"  Runs found: {len(runs)}{suffix}")
    _console.print()


def _render_latest_run_header(run: AnalyticsRun) -> None:
    label = "[incomplete]" if not run.complete else f"[{run.run_type}]"
    total = format_duration(run.total_duration_seconds)
    _console.print(
        f"[bold]Latest run:[/bold] {run.start_time.strftime('%Y-%m-%d %H:%M:%S')}  "
        f"{label}  Total: {total}"
    )
    _console.print()


def _collect_stats(runs: list[AnalyticsRun]) -> dict[str, list[float]]:
    rows: dict[str, list[float]] = {}

    rs_totals = [
        sum(rt.duration_seconds for rt in r.resource_tables)
        for r in runs if r.resource_tables
    ]
    if rs_totals:
        rows["Resource Tables"] = rs_totals

    for run in runs:
        for t in run.table_updates:
            if t.aborted:
                continue
            if t.type_name == "EVENT":
                if t.index_seconds is not None:
                    rows.setdefault("EVENT / indexes", []).append(t.index_seconds)
                run_totals: dict[str, float] = {}
                for p in t.program_updates:
                    if p.had_data and p.population_seconds is not None:
                        uid_key = p.uid.lower()
                        run_totals[uid_key] = run_totals.get(uid_key, 0.0) + p.population_seconds
                for uid_key, total in run_totals.items():
                    rows.setdefault(f"EVENT / {uid_key}", []).append(total)
            else:
                rows.setdefault(t.type_name, []).append(t.duration_seconds)

    return rows


def _print_stats_table(rows: dict[str, list[float]]) -> None:
    table = Table(box=box.SIMPLE_HEAD, show_footer=False)
    table.add_column("Table Type", style="bold")
    table.add_column("Mean", justify="right")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("N", justify="right")
    for label, durations in sorted(rows.items()):
        table.add_row(
            label,
            format_duration(_mean(durations)),
            format_duration(min(durations)),
            format_duration(max(durations)),
            str(len(durations)),
        )
    _console.print(table)
    _console.print()


def _render_summary_table(runs: list[AnalyticsRun]) -> None:
    complete = [r for r in runs if r.complete]
    if not complete:
        return

    by_type: dict[str, list[AnalyticsRun]] = {}
    for run in complete:
        by_type.setdefault(run.run_type, []).append(run)

    titles = {"full": "Full Run Duration Summary", "continuous": "Continuous Run Duration Summary"}
    for run_type in ("full", "continuous"):
        if run_type not in by_type:
            continue
        type_runs = by_type[run_type]
        rows = _collect_stats(type_runs)
        if not rows:
            continue
        _console.print(f"[bold]{titles[run_type]}[/bold]  ({len(type_runs)} runs)")
        _console.print()
        _print_stats_table(rows)


def _render_duration_chart(runs: list[AnalyticsRun]) -> None:
    labels = [r.start_time.strftime("%m-%d") for r in runs]
    values = [r.total_duration_seconds / 60 for r in runs]

    plt.clf()
    plt.plot_size(*_chart_size())
    plt.plot(values, label="Total duration (min)")
    plt.xticks(range(len(labels)), labels)
    plt.title("Run Duration Over Time")
    plt.ylabel("minutes")
    plt.show()


def _render_index_chart(runs: list[AnalyticsRun]) -> None:
    data = [
        (r.start_time, t.index_seconds)
        for r in runs
        for t in r.table_updates
        if t.type_name == "DATA_VALUE" and t.index_seconds is not None
    ]
    if not data:
        return

    labels = [d[0].strftime("%m-%d") for d in data]
    values = [d[1] / 60 for d in data]

    plt.clf()
    plt.plot_size(*_chart_size())
    plt.plot(values, label="Index time (min)")
    plt.xticks(range(len(labels)), labels)
    plt.title("DATA_VALUE Index Creation Time Over Time")
    plt.ylabel("minutes")
    plt.show()


def _render_program_breakdown(run: AnalyticsRun) -> None:
    by_uid: dict[str, float] = {}
    for t in run.table_updates:
        if t.type_name != "EVENT":
            continue
        for p in t.program_updates:
            if p.had_data and p.population_seconds is not None:
                by_uid[p.uid] = by_uid.get(p.uid, 0.0) + p.population_seconds

    if not by_uid:
        return

    items = sorted(by_uid.items(), key=lambda x: x[1], reverse=True)

    _console.print("[bold]Per-Program Event Breakdown (latest run)[/bold]")
    plt.clf()
    plt.plot_size(*_chart_size())
    plt.bar([uid for uid, _ in items], [secs for _, secs in items])
    plt.title("Event Table Population Time by Program")
    plt.ylabel("seconds")
    plt.show()
