import pytest

from anibatch.core.models import (
    EpisodeMedia,
    ProviderCapabilities,
    ProviderEpisode,
    ProviderSeries,
)
from anibatch.downloader.backends.base import DownloadBackend
from anibatch.media.base import MediaProcessor
from anibatch.metadata.base import MetadataProvider
from anibatch.providers.base import Provider
from anibatch.storage.base import JobRepository


def test_provider_abstract_enforcement() -> None:
    # Cannot instantiate without implementing abstract methods
    with pytest.raises(TypeError):
        Provider()  # type: ignore[abstract]

    class ConcreteProvider(Provider):
        name = "dummy"
        capabilities = ProviderCapabilities()

        async def search(self, query: str) -> list[ProviderSeries]:
            return []

        async def get_series(self, series_id: str) -> ProviderSeries:
            return ProviderSeries(id=series_id, title="Test", provider=self.name)

        async def get_episodes(self, series_id: str) -> list[ProviderEpisode]:
            return []

        async def get_media(self, episode: ProviderEpisode) -> EpisodeMedia:
            return EpisodeMedia(episode_id=episode.id)

    provider = ConcreteProvider()
    assert provider.name == "dummy"
    assert provider.capabilities.search is True


def test_download_backend_abstract_enforcement() -> None:
    with pytest.raises(TypeError):
        DownloadBackend()  # type: ignore[abstract]


def test_media_processor_abstract_enforcement() -> None:
    with pytest.raises(TypeError):
        MediaProcessor()  # type: ignore[abstract]


def test_metadata_provider_abstract_enforcement() -> None:
    with pytest.raises(TypeError):
        MetadataProvider()  # type: ignore[abstract]


def test_job_repository_abstract_enforcement() -> None:
    with pytest.raises(TypeError):
        JobRepository()  # type: ignore[abstract]
