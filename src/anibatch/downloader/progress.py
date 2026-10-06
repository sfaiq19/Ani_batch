import shutil
from datetime import UTC, datetime
from pathlib import Path


class ProgressTracker:
    """Tracks byte transfer speed, ETA, and progress metrics."""

    def __init__(self, total_bytes: int = 0) -> None:
        self.total_bytes = total_bytes
        self.downloaded_bytes = 0
        self.start_time = datetime.now(UTC)
        self.last_time = self.start_time
        self.last_bytes = 0
        self.speed = 0.0

    def update(self, current_downloaded: int) -> None:
        now = datetime.now(UTC)
        elapsed_delta = (now - self.last_time).total_seconds()
        if elapsed_delta >= 0.5:
            bytes_delta = current_downloaded - self.last_bytes
            self.speed = bytes_delta / elapsed_delta
            self.last_time = now
            self.last_bytes = current_downloaded
        self.downloaded_bytes = current_downloaded

    @property
    def eta_seconds(self) -> float | None:
        if self.speed <= 0 or self.total_bytes <= self.downloaded_bytes:
            return None
        remaining = self.total_bytes - self.downloaded_bytes
        return remaining / self.speed

    def format_status(self) -> str:
        speed_mb = self.speed / (1024 * 1024)
        eta = self.eta_seconds
        eta_str = f"{int(eta)}s" if eta is not None else "--"
        percent = (self.downloaded_bytes / self.total_bytes * 100) if self.total_bytes > 0 else 0.0
        return f"{percent:.1f}% | {speed_mb:.2f} MB/s | ETA: {eta_str}"


def check_disk_space(target_dir: Path, required_bytes: int) -> bool:
    """Check if target filesystem directory has sufficient free space."""
    target = target_dir if target_dir.exists() else target_dir.parent
    try:
        usage = shutil.disk_usage(target)
        return usage.free >= required_bytes
    except OSError:
        return True
