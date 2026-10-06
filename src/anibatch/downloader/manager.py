from datetime import UTC, datetime
from pathlib import Path

from anibatch.core.enums import DownloadState
from anibatch.core.exceptions import DownloaderError
from anibatch.core.models import DownloadJob
from anibatch.downloader.backends.base import DownloadBackend
from anibatch.downloader.retry import with_retry
from anibatch.storage.base import JobRepository


class DownloadManager:
    """Coordinates download lifecycle, state persistence, retries, and atomic commits."""

    def __init__(
        self,
        repository: JobRepository,
        backend: DownloadBackend,
    ) -> None:
        self.repository = repository
        self.backend = backend

    async def execute_job(self, job: DownloadJob, stream_url: str) -> Path:
        """Execute a single download job with state tracking, backoff retries, and persistence."""
        job.state = DownloadState.DOWNLOADING
        job.started_at = datetime.now(UTC)
        await self.repository.update_job(job)

        async def _download_action() -> Path:
            job.attempts += 1
            await self.repository.update_job(job)

            def _on_progress(downloaded: int, total: int) -> None:
                job.bytes_downloaded = downloaded
                job.bytes_total = total

            return await self.backend.download(
                job=job,
                stream_url=stream_url,
                on_progress=_on_progress,
            )

        try:
            dest_file = await with_retry(
                operation=_download_action,
                max_attempts=3,
                initial_delay=0.1,  # fast backoff for tests
            )
            job.state = DownloadState.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.last_error = None
            await self.repository.update_job(job)
            return dest_file

        except Exception as exc:
            job.state = DownloadState.FAILED
            job.last_error = str(exc)
            await self.repository.update_job(job)
            raise DownloaderError(f"Job {job.id} failed: {exc}") from exc

    async def cancel_job(self, job_id: str) -> None:
        """Cancel an in-flight job and set its state to CANCELLED."""
        await self.backend.cancel(job_id)
        job = await self.repository.get_job(job_id)
        if job:
            job.state = DownloadState.CANCELLED
            await self.repository.update_job(job)
