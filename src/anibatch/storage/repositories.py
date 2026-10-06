import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from anibatch.core.enums import AnimeStatus, DownloadState
from anibatch.core.models import Anime, DownloadJob, Episode
from anibatch.storage.base import AnimeRepository, JobRepository


class SqliteJobRepository(JobRepository):
    """SQLite implementation of JobRepository."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create_job(self, job: DownloadJob) -> None:
        await self.db.execute(
            """
            INSERT INTO download_jobs (
                id, anime_id, episode_id, provider, state,
                selected_quality, selected_audio, selected_subtitle,
                destination, temporary_path, bytes_total, bytes_downloaded,
                attempts, last_error, created_at, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(job.id),
                str(job.anime_id),
                str(job.episode_id),
                job.provider,
                job.state.value,
                job.selected_quality,
                job.selected_audio,
                job.selected_subtitle,
                str(job.destination),
                str(job.temporary_path),
                job.bytes_total,
                job.bytes_downloaded,
                job.attempts,
                job.last_error,
                job.created_at.isoformat(),
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
            ),
        )
        await self.db.commit()

    async def get_job(self, job_id: str) -> DownloadJob | None:
        async with self.db.execute("SELECT * FROM download_jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    async def update_job(self, job: DownloadJob) -> None:
        await self.db.execute(
            """
            UPDATE download_jobs SET
                state = ?,
                selected_quality = ?,
                selected_audio = ?,
                selected_subtitle = ?,
                destination = ?,
                temporary_path = ?,
                bytes_total = ?,
                bytes_downloaded = ?,
                attempts = ?,
                last_error = ?,
                started_at = ?,
                completed_at = ?
            WHERE id = ?
            """,
            (
                job.state.value,
                job.selected_quality,
                job.selected_audio,
                job.selected_subtitle,
                str(job.destination),
                str(job.temporary_path),
                job.bytes_total,
                job.bytes_downloaded,
                job.attempts,
                job.last_error,
                job.started_at.isoformat() if job.started_at else None,
                job.completed_at.isoformat() if job.completed_at else None,
                str(job.id),
            ),
        )
        await self.db.commit()

    async def list_jobs(self, state: DownloadState | None = None) -> list[DownloadJob]:
        if state is not None:
            query = "SELECT * FROM download_jobs WHERE state = ? ORDER BY created_at ASC"
            params: tuple[Any, ...] = (state.value,)
        else:
            query = "SELECT * FROM download_jobs ORDER BY created_at ASC"
            params = ()

        async with self.db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [self._row_to_job(r) for r in rows]

    async def recover_active_jobs(self) -> int:
        """Reset interrupted jobs (DOWNLOADING -> PAUSED) on startup."""
        cursor = await self.db.execute(
            """
            UPDATE download_jobs
            SET state = ?
            WHERE state = ?
            """,
            (DownloadState.PAUSED.value, DownloadState.DOWNLOADING.value),
        )
        await self.db.commit()
        return cursor.rowcount

    async def record_completed_file(
        self,
        job_id: str,
        episode_id: str,
        destination: Path,
        size: int,
        checksum: str | None = None,
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        file_id = f"{job_id}-done"
        await self.db.execute(
            """
            INSERT OR REPLACE INTO completed_files (
                id, job_id, episode_id, destination, size, checksum, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (file_id, job_id, episode_id, str(destination), size, checksum, now_iso),
        )
        await self.db.commit()

    async def list_completed_files(self) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM completed_files ORDER BY completed_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    def _row_to_job(self, row: aiosqlite.Row) -> DownloadJob:
        return DownloadJob(
            id=row["id"],
            anime_id=row["anime_id"],
            episode_id=row["episode_id"],
            provider=row["provider"],
            state=DownloadState(row["state"]),
            selected_quality=row["selected_quality"],
            selected_audio=row["selected_audio"],
            selected_subtitle=row["selected_subtitle"],
            destination=Path(row["destination"]),
            temporary_path=Path(row["temporary_path"]),
            bytes_total=row["bytes_total"],
            bytes_downloaded=row["bytes_downloaded"],
            attempts=row["attempts"],
            last_error=row["last_error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row["completed_at"]
            else None,
        )


class SqliteAnimeRepository(AnimeRepository):
    """SQLite implementation of AnimeRepository."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def save_anime(self, anime: Anime) -> None:
        aliases_json = json.dumps(anime.aliases)
        await self.db.execute(
            """
            INSERT OR REPLACE INTO anime (
                id, metadata_source, metadata_id, title, english_title,
                romaji_title, native_title, aliases, year, season,
                episode_count, status, cover_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(anime.id),
                anime.metadata_source,
                str(anime.metadata_id) if anime.metadata_id else None,
                anime.title,
                anime.english_title,
                anime.romaji_title,
                anime.native_title,
                aliases_json,
                anime.year,
                anime.season,
                anime.episode_count,
                anime.status.value,
                anime.cover_url,
            ),
        )
        await self.db.commit()

    async def get_anime(self, anime_id: str | int) -> Anime | None:
        async with self.db.execute("SELECT * FROM anime WHERE id = ?", (str(anime_id),)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            aliases = json.loads(row["aliases"]) if row["aliases"] else []
            return Anime(
                id=row["id"],
                metadata_source=row["metadata_source"],
                metadata_id=row["metadata_id"],
                title=row["title"],
                english_title=row["english_title"],
                romaji_title=row["romaji_title"],
                native_title=row["native_title"],
                aliases=aliases,
                year=row["year"],
                season=row["season"],
                episode_count=row["episode_count"],
                status=AnimeStatus(row["status"]),
                cover_url=row["cover_url"],
            )

    async def save_episodes(self, episodes: list[Episode]) -> None:
        for ep in episodes:
            ep_id = str(ep.id) if ep.id is not None else f"{ep.anime_id}-{ep.number}"
            await self.db.execute(
                """
                INSERT OR REPLACE INTO episodes (
                    id, anime_id, number, absolute_number, title, air_date, provider_episode_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ep_id,
                    str(ep.anime_id),
                    ep.number,
                    ep.absolute_number,
                    ep.title,
                    ep.air_date,
                    ep.provider_episode_id,
                ),
            )
        await self.db.commit()

    async def get_episodes(self, anime_id: str | int) -> list[Episode]:
        async with self.db.execute(
            "SELECT * FROM episodes WHERE anime_id = ? ORDER BY number ASC",
            (str(anime_id),),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                Episode(
                    id=r["id"],
                    anime_id=r["anime_id"],
                    number=r["number"],
                    absolute_number=r["absolute_number"],
                    title=r["title"],
                    air_date=r["air_date"],
                    provider_episode_id=r["provider_episode_id"],
                )
                for r in rows
            ]
