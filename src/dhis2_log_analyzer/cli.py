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
