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
