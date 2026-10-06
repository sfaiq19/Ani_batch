import asyncio
from pathlib import Path

from anibatch.core.enums import DownloadState
from anibatch.core.models import DownloadJob
from anibatch.downloader.manager import DownloadManager
from anibatch.storage.base import JobRepository


class QueueManager:
    """Manages concurrent job scheduling, priority queues, and rate-limiting semaphore."""

    def __init__(
        self,
        repository: JobRepository,
        download_manager: DownloadManager,
        max_concurrent: int = 3,
    ) -> None:
        self.repository = repository
        self.download_manager = download_manager
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_downloads: dict[str, asyncio.Task[Path]] = {}
        self._queued_jobs: list[tuple[DownloadJob, str]] = []
        self._current_active = 0
        self._peak_active = 0

    @property
    def peak_active(self) -> int:
        return self._peak_active

    @property
    def active_count(self) -> int:
        return self._current_active

    async def enqueue(self, job: DownloadJob, stream_url: str) -> None:
        """Enqueue a job and persist its state as QUEUED."""
        job.state = DownloadState.QUEUED
        await self.repository.create_job(job)
        self._queued_jobs.append((job, stream_url))

    async def enqueue_batch(self, items: list[tuple[DownloadJob, str]]) -> None:
        """Enqueue multiple jobs in bulk."""
        for job, stream_url in items:
            await self.enqueue(job, stream_url)

    async def process_all(self) -> list[Path]:
        """Process all queued jobs within semaphore concurrency constraints."""
        tasks: list[asyncio.Task[Path]] = []

        async def _worker(job: DownloadJob, stream_url: str) -> Path:
            async with self._semaphore:
                self._current_active += 1
                self._peak_active = max(self._peak_active, self._current_active)
                try:
                    return await self.download_manager.execute_job(job, stream_url)
                finally:
                    self._current_active -= 1

        for job, stream_url in list(self._queued_jobs):
            task = asyncio.create_task(_worker(job, stream_url))
            self._active_downloads[job.id] = task
            tasks.append(task)

        self._queued_jobs.clear()
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_paths: list[Path] = []
        for r in results:
            if isinstance(r, Path):
                final_paths.append(r)
            elif isinstance(r, Exception):
                pass  # job failure is tracked in repository
        return final_paths

    async def cancel_job(self, job_id: str) -> None:
        """Cancel an active or queued job."""
        if job_id in self._active_downloads:
            task = self._active_downloads[job_id]
            task.cancel()
        await self.download_manager.cancel_job(job_id)

    async def retry_failed(self, stream_urls: dict[str, str]) -> list[Path]:
        """Re-queue all failed jobs."""
        failed_jobs = await self.repository.list_jobs(state=DownloadState.FAILED)
        for job in failed_jobs:
            if job.id in stream_urls:
                job.state = DownloadState.QUEUED
                job.attempts = 0
                await self.repository.update_job(job)
                self._queued_jobs.append((job, stream_urls[job.id]))
        return await self.process_all()
