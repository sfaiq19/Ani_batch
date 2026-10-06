import asyncio
import shutil
from pathlib import Path

from anibatch.core.exceptions import DownloaderError
from anibatch.core.models import DownloadJob
from anibatch.downloader.backends.base import DownloadBackend, ProgressCallback
from anibatch.downloader.verification import verify_downloaded_file


class Aria2Backend(DownloadBackend):
    """Optional high-performance download backend delegating to external aria2c binary."""

    name = "aria2"

    def __init__(self, aria2c_path: str | Path | None = None) -> None:
        self.aria2c_path = Path(aria2c_path) if aria2c_path else self._find_binary()
        self._active_procs: dict[str, asyncio.subprocess.Process] = {}

    @staticmethod
    def _find_binary() -> Path | None:
        which = shutil.which("aria2c")
        if which:
            return Path(which)
        # Check project-relative bin directory
        local_candidates = [
            Path("bin/aria2c.exe"),
            Path("bin/aria2c"),
            Path(__file__).resolve().parents[3] / "bin" / "aria2c.exe",
            Path(__file__).resolve().parents[3] / "bin" / "aria2c",
        ]
        for candidate in local_candidates:
            if candidate.is_file():
                return candidate.resolve()
        return None

    def is_available(self) -> bool:
        return self.aria2c_path is not None

    async def download(
        self,
        job: DownloadJob,
        stream_url: str,
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        """Execute stream download via aria2c subprocess."""
        if not self.aria2c_path:
            raise DownloaderError(
                "aria2c binary not found on system PATH. Install aria2 or set downloads.backend = 'native'."
            )

        part_path = job.temporary_path
        dest_path = job.destination
        part_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(self.aria2c_path),
            "--dir",
            str(part_path.parent),
            "--out",
            part_path.name,
            "--continue=true",
            "--max-connection-per-server=4",
            "--split=4",
            "--min-split-size=1M",
            "--summary-interval=1",
            "--follow-torrent=mem",
            "--seed-time=0",
            stream_url,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._active_procs[job.id] = proc
        _, stderr = await proc.communicate()
        self._active_procs.pop(job.id, None)

        if proc.returncode != 0:
            raise DownloaderError(
                f"aria2c execution failed with code {proc.returncode}: {stderr.decode(errors='replace')}"
            )

        source_path = part_path
        if not source_path.exists():
            candidates = [
                p
                for p in part_path.parent.iterdir()
                if p != dest_path and not p.name.endswith(".part")
            ]
            if candidates:
                source_path = max(candidates, key=lambda p: p.stat().st_size)

        # Verification step
        verify_downloaded_file(source_path)

        # Atomic finalization
        if dest_path.exists():
            dest_path.unlink()
        source_path.replace(dest_path)

        return dest_path

    async def cancel(self, job_id: str) -> None:
        """Cancel in-flight aria2c process."""
        proc = self._active_procs.get(job_id)
        if proc:
            proc.terminate()
            await proc.wait()
