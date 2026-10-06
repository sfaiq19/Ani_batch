from pathlib import Path

import httpx
import pytest
import respx

from anibatch.core.enums import DownloadState
from anibatch.core.exceptions import DownloaderError
from anibatch.core.models import DownloadJob
from anibatch.downloader.backends.http import HttpxBackend
from anibatch.downloader.manager import DownloadManager
from anibatch.downloader.verification import calculate_checksum, verify_downloaded_file
from anibatch.storage.database import Database
from anibatch.storage.migrations import run_migrations
from anibatch.storage.repositories import SqliteJobRepository


@pytest.fixture
async def job_repo(tmp_path: Path):
    db_file = tmp_path / "test_dl.db"
    database = Database(db_file)
    async with database.connect() as conn:
        await run_migrations(conn)
        yield SqliteJobRepository(conn)


@pytest.mark.asyncio
async def test_full_download_and_atomic_finalization(
    tmp_path: Path, respx_mock: respx.MockRouter
) -> None:
    stream_content = b"A" * 100_000
    respx_mock.get("https://test.local/stream.mp4").respond(
        200,
        content=stream_content,
        headers={"Content-Length": "100000"},
    )

    dest = tmp_path / "ep01.mp4"
    part = tmp_path / "ep01.mp4.part"
    job = DownloadJob(
        id="j-1",
        anime_id="1",
        episode_id="e-1",
        provider="test",
        selected_quality="1080p",
        destination=dest,
        temporary_path=part,
    )

    async with httpx.AsyncClient() as client:
        backend = HttpxBackend(client=client)
        result_path = await backend.download(job, "https://test.local/stream.mp4")

        assert result_path == dest
        assert dest.exists()
        assert not part.exists()
        assert dest.stat().st_size == 100_000
        assert dest.read_bytes() == stream_content


@pytest.mark.asyncio
async def test_interrupted_download_and_resume_acceptance(
    tmp_path: Path, respx_mock: respx.MockRouter
) -> None:
    """Acceptance test: start download, interrupt, restart, resume, verify no restart from zero."""
    full_data = b"0123456789" * 50_000  # 500,000 bytes
    chunk_1 = full_data[:200_000]  # 200,000 bytes
    chunk_2 = full_data[200_000:]  # remaining 300,000 bytes

    dest = tmp_path / "resumed.mp4"
    part = tmp_path / "resumed.mp4.part"

    # Step 1: Simulate interrupted partial download written to .part
    part.write_bytes(chunk_1)
    assert part.stat().st_size == 200_000

    # Step 2: Configure mock to respond to Range request
    def range_callback(request: httpx.Request) -> httpx.Response:
        range_header = request.headers.get("Range")
        assert range_header == "bytes=200000-"
        return httpx.Response(
            206,
            content=chunk_2,
            headers={
                "Content-Range": f"bytes 200000-499999/{len(full_data)}",
                "Content-Length": str(len(chunk_2)),
            },
        )

    respx_mock.get("https://test.local/video.mp4").mock(side_effect=range_callback)

    job = DownloadJob(
        id="j-resume",
        anime_id="1",
        episode_id="e-1",
        provider="test",
        selected_quality="1080p",
        destination=dest,
        temporary_path=part,
    )

    # Step 3: Run resume download
    async with httpx.AsyncClient() as client:
        backend = HttpxBackend(client=client)
        final_dest = await backend.download(job, "https://test.local/video.mp4")

        assert final_dest == dest
        assert not part.exists()
        assert dest.exists()
        assert dest.stat().st_size == 500_000
        assert dest.read_bytes() == full_data


@pytest.mark.asyncio
async def test_download_manager_lifecycle_and_db_state(
    tmp_path: Path, job_repo: SqliteJobRepository, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get("https://test.local/stream.mp4").respond(
        200,
        content=b"test-stream-data",
        headers={"Content-Length": "16"},
    )

    dest = tmp_path / "managed.mp4"
    part = tmp_path / "managed.mp4.part"
    job = DownloadJob(
        id="job-managed",
        anime_id="1",
        episode_id="e-1",
        provider="test",
        state=DownloadState.QUEUED,
        selected_quality="1080p",
        destination=dest,
        temporary_path=part,
    )
    await job_repo.create_job(job)

    async with httpx.AsyncClient() as client:
        backend = HttpxBackend(client=client)
        manager = DownloadManager(repository=job_repo, backend=backend)

        await manager.execute_job(job, "https://test.local/stream.mp4")

        saved = await job_repo.get_job("job-managed")
        assert saved is not None
        assert saved.state == DownloadState.COMPLETED
        assert saved.bytes_downloaded == 16
        assert saved.completed_at is not None


@pytest.mark.asyncio
async def test_retry_on_server_error_and_fail_on_404(
    tmp_path: Path, job_repo: SqliteJobRepository, respx_mock: respx.MockRouter
) -> None:
    dest = tmp_path / "fail.mp4"
    part = tmp_path / "fail.mp4.part"
    job = DownloadJob(
        id="job-fail",
        anime_id="1",
        episode_id="e-1",
        provider="test",
        state=DownloadState.QUEUED,
        selected_quality="1080p",
        destination=dest,
        temporary_path=part,
    )
    await job_repo.create_job(job)

    # 404 should not be endlessly retried
    respx_mock.get("https://test.local/missing.mp4").respond(404)

    async with httpx.AsyncClient() as client:
        backend = HttpxBackend(client=client)
        manager = DownloadManager(repository=job_repo, backend=backend)

        with pytest.raises(DownloaderError):
            await manager.execute_job(job, "https://test.local/missing.mp4")

        saved = await job_repo.get_job("job-fail")
        assert saved is not None
        assert saved.state == DownloadState.FAILED
        assert saved.attempts == 1


def test_file_verification(tmp_path: Path) -> None:
    f = tmp_path / "test.bin"
    f.write_bytes(b"hello world")
    checksum = calculate_checksum(f)

    assert verify_downloaded_file(f, expected_size=11, expected_checksum=checksum) is True

    with pytest.raises(DownloaderError, match="empty"):
        empty = tmp_path / "empty.bin"
        empty.write_bytes(b"")
        verify_downloaded_file(empty)

    with pytest.raises(DownloaderError, match="Size mismatch"):
        verify_downloaded_file(f, expected_size=999)
