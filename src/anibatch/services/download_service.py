from pathlib import Path
from typing import Any

import aiosqlite
import httpx

from anibatch.core.config import AniBatchConfig
from anibatch.core.enums import DownloadState
from anibatch.core.exceptions import AniBatchError
from anibatch.core.models import DownloadJob
from anibatch.downloader.batch_parser import parse_episode_selection
from anibatch.media.ffmpeg import FFmpegService
from anibatch.metadata.anilist import AniListMetadataProvider
from anibatch.naming.formatter import PathFormatter
from anibatch.providers.registry import init_default_providers, registry
from anibatch.storage.database import Database
from anibatch.storage.migrations import run_migrations
from anibatch.storage.repositories import SqliteAnimeRepository, SqliteJobRepository


class DownloadService:
    """Application Service coordinating CLI with metadata, storage, provider, and download engines."""

    def __init__(
        self,
        config: AniBatchConfig | None = None,
        db_path: Path | None = None,
    ) -> None:
        self.config = config or AniBatchConfig()
        db_file = db_path or (self.config.general.data_directory / "anibatch.db")
        self.database = Database(db_file)
        self.path_formatter = PathFormatter(
            base_dir=self.config.general.download_directory,
            series_folder_template=self.config.naming.series_folder,
            season_folder_template=self.config.naming.season_folder,
            episode_template=self.config.naming.episode,
        )
        self.ffmpeg_service = FFmpegService()
        init_default_providers()

    async def init_db(self) -> None:
        async with self.database.connect() as conn:
            await run_migrations(conn)

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search metadata via AniList, with fallback to provider search."""
        results: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                anilist = AniListMetadataProvider(client=client)
                anime_list = await anilist.search(query)
                for a in anime_list:
                    results.append(
                        {
                            "id": str(a.id),
                            "title": a.title,
                            "year": a.year,
                            "episodes": a.episode_count,
                            "source": "anilist",
                        }
                    )
        except (httpx.HTTPError, TimeoutError, OSError):
            pass

        if not results:
            for p_name in registry.list_available():
                prov = registry.get(p_name)
                if prov:
                    try:
                        p_results = await prov.search(query)
                        for ps in p_results:
                            results.append(
                                {
                                    "id": ps.id,
                                    "title": ps.title,
                                    "year": ps.year,
                                    "episodes": ps.episode_count,
                                    "source": p_name,
                                }
                            )
                    except (AniBatchError, OSError):
                        pass
        return results

    async def get_series_info(self, series_id: str, provider_name: str = "test") -> dict[str, Any]:
        """Fetch series information and available episode list."""
        prov = registry.get(provider_name)
        if not prov:
            return {"error": f"Provider '{provider_name}' not found."}

        series = await prov.get_series(series_id)
        episodes = await prov.get_episodes(series_id)

        return {
            "id": series.id,
            "title": series.title,
            "year": series.year,
            "provider": provider_name,
            "episodes": [{"number": ep.number, "title": ep.title, "id": ep.id} for ep in episodes],
        }

    async def queue_episodes(
        self,
        series_id: str,
        episode_range: str = "all",
        quality: str = "1080p",
        provider_name: str = "test",
    ) -> list[str]:
        """Enqueue episodes matching the episode_range string."""
        await self.init_db()

        prov = registry.get(provider_name)
        if not prov:
            raise ValueError(f"Unknown provider '{provider_name}'")

        series = await prov.get_series(series_id)
        all_episodes = await prov.get_episodes(series_id)
        total_ep_count = len(all_episodes)

        selected_nums = parse_episode_selection(
            episode_range,
            total_episodes=total_ep_count if total_ep_count > 0 else None,
        )

        selected_episodes = [ep for ep in all_episodes if int(ep.number) in selected_nums]

        async with self.database.connect() as conn:
            job_repo = SqliteJobRepository(conn)
            anime_repo = SqliteAnimeRepository(conn)

            # Persist series in DB
            from anibatch.core.models import Anime, Episode

            anime_record = Anime(
                id=series.id,
                title=series.title,
                year=series.year,
                episode_count=total_ep_count,
            )
            await anime_repo.save_anime(anime_record)

            queued_ids: list[str] = []
            for ep in selected_episodes:
                # Save episode
                await anime_repo.save_episodes(
                    [Episode(anime_id=series.id, number=ep.number, title=ep.title)]
                )

                dest = self.path_formatter.format_destination(
                    anime_title=series.title,
                    season=1,
                    episode_num=ep.number,
                    episode_title=ep.title,
                    extension="mp4",
                )
                part = dest.with_name(f"{dest.stem}.part{dest.suffix}")

                job_id = f"job-{series.id}-{int(ep.number):02d}"
                job = DownloadJob(
                    id=job_id,
                    anime_id=series.id,
                    episode_id=ep.id,
                    provider=provider_name,
                    state=DownloadState.QUEUED,
                    selected_quality=quality,
                    destination=dest,
                    temporary_path=part,
                )
                await job_repo.create_job(job)
                queued_ids.append(job_id)

            return queued_ids

    async def list_jobs(self, state: DownloadState | None = None) -> list[DownloadJob]:
        await self.init_db()
        async with self.database.connect() as conn:
            job_repo = SqliteJobRepository(conn)
            return await job_repo.list_jobs(state=state)

    async def pause_job(self, job_id: str) -> None:
        await self.init_db()
        async with self.database.connect() as conn:
            job_repo = SqliteJobRepository(conn)
            job = await job_repo.get_job(job_id)
            if job and job.state in (DownloadState.QUEUED, DownloadState.DOWNLOADING):
                job.state = DownloadState.PAUSED
                await job_repo.update_job(job)

    async def cancel_job(self, job_id: str) -> None:
        await self.init_db()
        async with self.database.connect() as conn:
            job_repo = SqliteJobRepository(conn)
            job = await job_repo.get_job(job_id)
            if job:
                job.state = DownloadState.CANCELLED
                await job_repo.update_job(job)

    async def resume_all(self) -> int:
        await self.init_db()
        async with self.database.connect() as conn:
            job_repo = SqliteJobRepository(conn)
            paused = await job_repo.list_jobs(state=DownloadState.PAUSED)
            for j in paused:
                j.state = DownloadState.QUEUED
                await job_repo.update_job(j)
            return len(paused)

    async def list_history(self) -> list[dict[str, Any]]:
        await self.init_db()
        async with self.database.connect() as conn:
            job_repo = SqliteJobRepository(conn)
            return await job_repo.list_completed_files()

    async def run_diagnostics(self) -> dict[str, Any]:
        """Perform system checks for 'doctor' command."""
        results: dict[str, Any] = {}

        # 1. Config
        results["config_loaded"] = True

        # 2. Database
        try:
            await self.init_db()
            results["database_writable"] = True
        except (aiosqlite.Error, OSError) as e:
            results["database_writable"] = f"Error: {e}"

        # 3. Destination folder
        try:
            self.config.general.download_directory.mkdir(parents=True, exist_ok=True)
            results["destination_writable"] = True
        except OSError as e:
            results["destination_writable"] = f"Error: {e}"

        # 4. FFmpeg & ffprobe
        results["ffmpeg"] = bool(self.ffmpeg_service.ffmpeg_path)
        results["ffprobe"] = bool(self.ffmpeg_service.ffprobe_path)

        # 5. AniList API
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    "https://graphql.anilist.co",
                    json={"query": "{ Page(page: 1, perPage: 1) { media(id: 1) { id } } }"},
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                results["anilist_reachable"] = res.status_code == 200
        except (httpx.HTTPError, TimeoutError, OSError):
            results["anilist_reachable"] = False

        # 6. Providers
        results["providers"] = await registry.health_check_all()

        return results
