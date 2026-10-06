from abc import ABC, abstractmethod

from anibatch.core.enums import DownloadState
from anibatch.core.models import Anime, DownloadJob, Episode


class JobRepository(ABC):
    """Abstract interface for managing download jobs and their lifecycle states."""

    @abstractmethod
    async def create_job(self, job: DownloadJob) -> None:
        """Persist a new download job."""
        ...

    @abstractmethod
    async def get_job(self, job_id: str) -> DownloadJob | None:
        """Fetch a job by ID."""
        ...

    @abstractmethod
    async def update_job(self, job: DownloadJob) -> None:
        """Update job progress, attempts, or state."""
        ...

    @abstractmethod
    async def list_jobs(self, state: DownloadState | None = None) -> list[DownloadJob]:
        """List jobs filtered optionally by state."""
        ...

    @abstractmethod
    async def recover_active_jobs(self) -> int:
        """Reset interrupted jobs (DOWNLOADING -> PAUSED) on startup."""
        ...


class AnimeRepository(ABC):
    """Abstract interface for managing cached anime series records."""

    @abstractmethod
    async def save_anime(self, anime: Anime) -> None: ...

    @abstractmethod
    async def get_anime(self, anime_id: str | int) -> Anime | None: ...

    @abstractmethod
    async def save_episodes(self, episodes: list[Episode]) -> None: ...

    @abstractmethod
    async def get_episodes(self, anime_id: str | int) -> list[Episode]: ...
