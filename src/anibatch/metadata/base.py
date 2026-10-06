from abc import ABC, abstractmethod

from anibatch.core.models import Anime


class MetadataProvider(ABC):
    """Abstract base class for canonical anime metadata providers (e.g. AniList)."""

    name: str

    @abstractmethod
    async def search(self, query: str) -> list[Anime]:
        """Search metadata service for anime titles."""
        ...

    @abstractmethod
    async def get_anime(self, anime_id: str | int) -> Anime | None:
        """Get canonical anime record by its metadata ID."""
        ...
