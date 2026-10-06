import asyncio
from pathlib import Path

import pytest

from anibatch.core.enums import DownloadState
from anibatch.core.models import DownloadJob
from anibatch.downloader.backends.base import DownloadBackend, ProgressCallback
from anibatch.downloader.batch_parser import BatchSyntaxError, parse_episode_selection
from anibatch.downloader.manager import DownloadManager
from anibatch.downloader.queue import QueueManager
from anibatch.storage.database import Database
from anibatch.storage.migrations import run_migrations
from anibatch.storage.repositories import SqliteJobRepository


def test_batch_parser_valid_expressions() -> None:
    assert parse_episode_selection("1") == [1]
    assert parse_episode_selection("1-12") == list(range(1, 13))
    assert parse_episode_selection("1,3,7") == [1, 3, 7]
    assert parse_episode_selection("1-4,8,12-15") == [1, 2, 3, 4, 8, 12, 13, 14, 15]
    assert parse_episode_selection("1-3,6,9-11") == [1, 2, 3, 6, 9, 10, 11]
    assert parse_episode_selection("all", total_episodes=28) == list(range(1, 29))
    assert parse_episode_selection("latest", total_episodes=28) == [28]


def test_batch_parser_malformed_inputs() -> None:
    malformed = ["abc", "5-", "-7", "10-3", "1,,4", "0", "", "   ", "all"]
    for val in malformed:
        with pytest.raises(BatchSyntaxError):
            parse_episode_selection(val)

    with pytest.raises(BatchSyntaxError):
        parse_episode_selection("1-10", total_episodes=5)


class ControlledFakeBackend(DownloadBackend):
    """Backend simulating async downloads with artificial non-zero sleep to test concurrency."""

    name = "fake"

    async def download(
        self,
        job: DownloadJob,
        stream_url: str,
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        # Simulate slight I/O duration
        await asyncio.sleep(0.02)
        job.destination.parent.mkdir(parents=True, exist_ok=True)
        job.destination.write_bytes(b"content")
        return job.destination

    async def cancel(self, job_id: str) -> None:
        pass


@pytest.mark.asyncio
async def test_queue_concurrency_28_jobs_max_3(tmp_path: Path) -> None:
    """Acceptance test: 28 jobs, max concurrency 3, verify never > 3 concurrent."""
    db_file = tmp_path / "queue_test.db"
    db = Database(db_file)
    async with db.connect() as conn:
        await run_migrations(conn)
        repo = SqliteJobRepository(conn)
        backend = ControlledFakeBackend()
        manager = DownloadManager(repository=repo, backend=backend)
        queue = QueueManager(repository=repo, download_manager=manager, max_concurrent=3)

        # Create 28 jobs
        batch: list[tuple[DownloadJob, str]] = []
        for i in range(1, 29):
            dest = tmp_path / f"ep_{i:02d}.mp4"
            part = tmp_path / f"ep_{i:02d}.mp4.part"
            job = DownloadJob(
                id=f"job-{i:02d}",
                anime_id="154587",
                episode_id=f"ep-{i:02d}",
                provider="test",
                selected_quality="1080p",
                destination=dest,
                temporary_path=part,
            )
            batch.append((job, f"https://test.local/ep/{i}"))

        await queue.enqueue_batch(batch)

        # Process all jobs
        completed = await queue.process_all()

        assert len(completed) == 28
        assert queue.peak_active <= 3
        assert queue.active_count == 0

        # Verify all 28 jobs in repository are marked COMPLETED
        db_jobs = await repo.list_jobs(state=DownloadState.COMPLETED)
        assert len(db_jobs) == 28
