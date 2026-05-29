from datetime import datetime
from unittest.mock import patch

from dhis2_log_analyzer.parsers.base import AnalyticsRun, TableTypeUpdate
from dhis2_log_analyzer.renderers.terminal import format_duration, render


def test_format_duration_seconds_only():
    assert format_duration(33.0) == "33s"


def test_format_duration_minutes_and_seconds():
    assert format_duration(67.0) == "1m 07s"


def test_format_duration_sub_second_rounds_to_one():
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
