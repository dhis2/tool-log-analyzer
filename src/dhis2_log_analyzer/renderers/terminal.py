from __future__ import annotations

import shutil

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
    _render_latest_run(runs[-1])
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
