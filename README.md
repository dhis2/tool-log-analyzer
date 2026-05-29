# dhis2-log-analyzer

A terminal tool for analyzing DHIS2 server logs from LXD containers. Parses analytics table generation logs and renders timing reports — run duration trends, index creation times, and per-program event breakdowns — directly in the terminal.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- `lxc` on PATH (user must be in the `lxd` group)

## Installation

```bash
git clone <repo>
cd dhis2-log-analyzer
uv sync
```

## Usage

```bash
# Analyze the current analytics log from a container
dhis2-analyze-logs hmis

# Include rotated logs from the last 14 days
dhis2-analyze-logs hmis --days 14
```

The tool connects to the named LXD container, reads `/opt/dhis2/logs/dhis-analytics-table.log` (and rotated files when `--days` is set), and prints:

- **Latest run summary** — duration of each table type update and index creation time
- **Run duration over time** — line chart showing whether runs are getting longer
- **Index time over time** — DATA_VALUE index creation time trend
- **Per-program event breakdown** — population time per tracker program (event servers only)

## Log types

Currently supports:

| Flag | Log file | Description |
|------|----------|-------------|
| `--type analytics` (default) | `dhis-analytics-table.log` | Analytics table generation |

## Adding a new log type

1. Add a parser module under `src/dhis2_log_analyzer/parsers/`
2. Add the new `--type` choice to `cli.py`

## Development

```bash
uv sync --group dev
uv run pytest
```
