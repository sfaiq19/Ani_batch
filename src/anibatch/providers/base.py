from abc import ABC, abstractmethod

from anibatch.core.models import (
    EpisodeMedia,
    ProviderCapabilities,
    ProviderEpisode,
    ProviderSeries,
)


class Provider(ABC):
    """Abstract base class for all pluggable media source providers."""

    name: str
    capabilities: ProviderCapabilities

    @abstractmethod
    async def search(self, query: str) -> list[ProviderSeries]:
        """Search for series matching the given query."""
        ...

    @abstractmethod
    async def get_series(self, series_id: str) -> ProviderSeries:
        """Retrieve detailed series information by provider series ID."""
        ...

    @abstractmethod
    async def get_episodes(self, series_id: str) -> list[ProviderEpisode]:
        """Retrieve list of available episodes for a series."""
        ...

    @abstractmethod
    async def get_media(self, episode: ProviderEpisode) -> EpisodeMedia:
        """Retrieve media variants and subtitle tracks for an episode."""
        ...

    async def health_check(self) -> bool:
        """Check if provider is online and reachable."""
        return True
