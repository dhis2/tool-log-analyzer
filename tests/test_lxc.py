import subprocess
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

from dhis2_log_analyzer.lxc import (
    LogFile,
    check_container_exists,
    check_lxc_available,
    list_log_files,
    stream_lines,
)


def test_check_lxc_available_exits_when_not_found():
    with patch("dhis2_log_analyzer.lxc.shutil.which", return_value=None):
        with pytest.raises(SystemExit) as exc:
            check_lxc_available()
    assert "lxc not found" in str(exc.value)


def test_check_lxc_available_passes_when_found():
    with patch("dhis2_log_analyzer.lxc.shutil.which", return_value="/usr/bin/lxc"):
        check_lxc_available()  # should not raise


def test_check_container_exists_exits_on_nonzero_returncode():
    with patch("dhis2_log_analyzer.lxc.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(SystemExit) as exc:
            check_container_exists("missing")
    assert "missing" in str(exc.value)


def test_check_container_exists_passes_on_zero_returncode():
    with patch("dhis2_log_analyzer.lxc.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        check_container_exists("hmis")  # should not raise


def test_list_log_files_returns_sorted_by_mtime():
    find_output = (
        "1000.0 /opt/dhis2/logs/dhis-analytics-table.log.1\n"
        "2000.0 /opt/dhis2/logs/dhis-analytics-table.log\n"
    )
    now = 3000.0
    with patch("dhis2_log_analyzer.lxc.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=find_output, returncode=0)
        files = list_log_files("hmis", "/opt/dhis2/logs/", "dhis-analytics-table.log*", days=5, now=now)
    assert len(files) == 2
    assert files[0].path == "/opt/dhis2/logs/dhis-analytics-table.log.1"
    assert files[1].path == "/opt/dhis2/logs/dhis-analytics-table.log"


def test_list_log_files_filters_by_days():
    now = 10000.0
    cutoff = now - 1 * 86400  # 1 day
    find_output = (
        f"{cutoff - 1:.1f} /opt/dhis2/logs/dhis-analytics-table.log.5.gz\n"  # too old
        f"{cutoff + 1:.1f} /opt/dhis2/logs/dhis-analytics-table.log.1\n"     # within range
        f"{now:.1f} /opt/dhis2/logs/dhis-analytics-table.log\n"              # within range
    )
    with patch("dhis2_log_analyzer.lxc.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=find_output, returncode=0)
        files = list_log_files("hmis", "/opt/dhis2/logs/", "dhis-analytics-table.log*", days=1, now=now)
    assert len(files) == 2
    paths = [f.path for f in files]
    assert "/opt/dhis2/logs/dhis-analytics-table.log.5.gz" not in paths


def test_stream_lines_uses_cat_for_plain_files():
    mock_proc = MagicMock()
    mock_proc.stdout = iter(["line1\n", "line2\n"])
    with patch("dhis2_log_analyzer.lxc.subprocess.Popen", return_value=mock_proc) as mock_popen:
        lines = list(stream_lines("hmis", "/opt/dhis2/logs/dhis-analytics-table.log"))
    mock_popen.assert_called_once_with(
        ["lxc", "exec", "hmis", "--", "cat", "/opt/dhis2/logs/dhis-analytics-table.log"],
        stdout=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    assert lines == ["line1", "line2"]


def test_stream_lines_uses_zcat_for_gz_files():
    mock_proc = MagicMock()
    mock_proc.stdout = iter(["line1\n"])
    with patch("dhis2_log_analyzer.lxc.subprocess.Popen", return_value=mock_proc) as mock_popen:
        list(stream_lines("hmis", "/opt/dhis2/logs/dhis-analytics-table.log.2.gz"))
    cmd = mock_popen.call_args[0][0]
    assert "zcat" in cmd
    assert "cat" not in cmd
