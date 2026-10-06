from pathlib import Path

import pytest

from anibatch.core.enums import AnimeStatus, DownloadState
from anibatch.core.models import Anime, DownloadJob, Episode
from anibatch.storage.database import Database
from anibatch.storage.migrations import run_migrations
from anibatch.storage.repositories import SqliteAnimeRepository, SqliteJobRepository


@pytest.fixture
async def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_anibatch.db"
    database = Database(db_file)
    async with database.connect() as conn:
        await run_migrations(conn)
        yield conn


@pytest.mark.asyncio
async def test_migrations_idempotency(temp_db) -> None:
    # Running migrations again should be a no-op
    await run_migrations(temp_db)


@pytest.mark.asyncio
async def test_anime_and_episodes_persistence(temp_db) -> None:
    repo = SqliteAnimeRepository(temp_db)
    anime = Anime(
        id="154587",
        metadata_id="154587",
        title="Frieren: Beyond Journey's End",
        english_title="Frieren",
        romaji_title="Sousou no Frieren",
        aliases=["Frieren: Nach dem Ende der Reise", "葬送的芙莉莲"],
        year=2023,
        season="FALL",
        episode_count=28,
        status=AnimeStatus.FINISHED,
        cover_url="https://example.com/cover.jpg",
    )
    await repo.save_anime(anime)

    fetched = await repo.get_anime("154587")
    assert fetched is not None
    assert fetched.title == "Frieren: Beyond Journey's End"
    assert fetched.aliases == ["Frieren: Nach dem Ende der Reise", "葬送的芙莉莲"]
    assert fetched.status == AnimeStatus.FINISHED

    episodes = [
        Episode(anime_id="154587", number=1.0, title="The Journey's End"),
        Episode(anime_id="154587", number=2.0, title="It Didn't Have to Be Magic"),
    ]
    await repo.save_episodes(episodes)

    fetched_eps = await repo.get_episodes("154587")
    assert len(fetched_eps) == 2
    assert fetched_eps[0].number == 1.0
    assert fetched_eps[0].title == "The Journey's End"
    assert fetched_eps[1].number == 2.0


@pytest.mark.asyncio
async def test_job_persistence_crud(temp_db, tmp_path: Path) -> None:
    job_repo = SqliteJobRepository(temp_db)
    job = DownloadJob(
        id="job-1",
        anime_id="154587",
        episode_id="ep-1",
        provider="test-provider",
        state=DownloadState.QUEUED,
        selected_quality="1080p",
        destination=tmp_path / "ep1.mkv",
        temporary_path=tmp_path / "ep1.mkv.part",
        bytes_total=1000,
        bytes_downloaded=0,
    )
    await job_repo.create_job(job)

    fetched = await job_repo.get_job("job-1")
    assert fetched is not None
    assert fetched.state == DownloadState.QUEUED
    assert fetched.destination == tmp_path / "ep1.mkv"

    # Update job
    fetched.bytes_downloaded = 500
    fetched.state = DownloadState.DOWNLOADING
    await job_repo.update_job(fetched)

    updated = await job_repo.get_job("job-1")
    assert updated is not None
    assert updated.state == DownloadState.DOWNLOADING
    assert updated.bytes_downloaded == 500


@pytest.mark.asyncio
async def test_crash_restart_recovery(temp_db, tmp_path: Path) -> None:
    job_repo = SqliteJobRepository(temp_db)

    # Simulate 3 jobs in various states
    job_active = DownloadJob(
        id="job-active",
        anime_id="154587",
        episode_id="ep-1",
        provider="test-provider",
        state=DownloadState.DOWNLOADING,
        selected_quality="1080p",
        destination=tmp_path / "ep1.mkv",
        temporary_path=tmp_path / "ep1.mkv.part",
    )
    job_queued = DownloadJob(
        id="job-queued",
        anime_id="154587",
        episode_id="ep-2",
        provider="test-provider",
        state=DownloadState.QUEUED,
        selected_quality="1080p",
        destination=tmp_path / "ep2.mkv",
        temporary_path=tmp_path / "ep2.mkv.part",
    )
    job_completed = DownloadJob(
        id="job-completed",
        anime_id="154587",
        episode_id="ep-3",
        provider="test-provider",
        state=DownloadState.COMPLETED,
        selected_quality="1080p",
        destination=tmp_path / "ep3.mkv",
        temporary_path=tmp_path / "ep3.mkv.part",
    )

    await job_repo.create_job(job_active)
    await job_repo.create_job(job_queued)
    await job_repo.create_job(job_completed)

    # Simulate crash / program restart recovery
    recovered_count = await job_repo.recover_active_jobs()
    assert recovered_count == 1

    # Check state transitions
    rec_active = await job_repo.get_job("job-active")
    assert rec_active is not None
    assert rec_active.state == DownloadState.PAUSED

    rec_queued = await job_repo.get_job("job-queued")
    assert rec_queued is not None
    assert rec_queued.state == DownloadState.QUEUED

    rec_completed = await job_repo.get_job("job-completed")
    assert rec_completed is not None
    assert rec_completed.state == DownloadState.COMPLETED


@pytest.mark.asyncio
async def test_completed_files_recording(temp_db, tmp_path: Path) -> None:
    job_repo = SqliteJobRepository(temp_db)
    job = DownloadJob(
        id="job-100",
        anime_id="154587",
        episode_id="ep-1",
        provider="test-provider",
        state=DownloadState.COMPLETED,
        selected_quality="1080p",
        destination=tmp_path / "ep1.mkv",
        temporary_path=tmp_path / "ep1.mkv.part",
    )
    await job_repo.create_job(job)
    await job_repo.record_completed_file(
        job_id="job-100",
        episode_id="ep-1",
        destination=tmp_path / "ep1.mkv",
        size=50_000_000,
        checksum="sha256-abcdef",
    )

    history = await job_repo.list_completed_files()
    assert len(history) == 1
    assert history[0]["job_id"] == "job-100"
    assert history[0]["size"] == 50_000_000
