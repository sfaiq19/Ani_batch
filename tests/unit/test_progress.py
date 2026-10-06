import time
from pathlib import Path

from anibatch.downloader.progress import ProgressTracker, check_disk_space


def test_progress_tracker_speed_and_eta() -> None:
    tracker = ProgressTracker(total_bytes=10_000_000)
    tracker.update(1_000_000)
    # Simulate slight time passage
    time.sleep(0.55)
    tracker.update(3_000_000)

    assert tracker.speed > 0
    assert tracker.eta_seconds is not None
    assert tracker.eta_seconds > 0

    status_str = tracker.format_status()
    assert "%" in status_str
    assert "MB/s" in status_str
    assert "ETA:" in status_str


def test_check_disk_space(tmp_path: Path) -> None:
    # Checking for 1 KB should succeed on any running filesystem
    assert check_disk_space(tmp_path, required_bytes=1024) is True
