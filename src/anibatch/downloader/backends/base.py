from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from anibatch.core.models import DownloadJob

ProgressCallback = Callable[[int, int], None]


class DownloadBackend(ABC):
    """Abstract interface for download execution backends (HTTPX, aria2)."""

    name: str

    @abstractmethod
    async def download(
        self,
        job: DownloadJob,
        stream_url: str,
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        """Execute stream download to job's temporary path and finalize to destination."""
        ...

    @abstractmethod
    async def cancel(self, job_id: str) -> None:
        """Cancel an ongoing download."""
        ...
