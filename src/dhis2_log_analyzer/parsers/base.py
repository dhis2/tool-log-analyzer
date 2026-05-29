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
