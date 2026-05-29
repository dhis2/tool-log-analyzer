import pytest
from datetime import datetime

from dhis2_log_analyzer.parsers.analytics import parse, parse_elapsed


# ── fixtures ──────────────────────────────────────────────────────────────────

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
