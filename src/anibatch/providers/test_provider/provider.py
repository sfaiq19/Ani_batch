from typing import Literal

from anibatch.core.exceptions import ProviderError
from anibatch.core.models import (
    EpisodeMedia,
    MediaVariant,
    ProviderCapabilities,
    ProviderEpisode,
    ProviderSeries,
    SubtitleTrack,
)
from anibatch.providers.base import Provider

FailureMode = Literal[
    "500",
    "404",
    "429",
    "timeout",
    "missing_quality",
    "missing_subtitle",
    "unhealthy",
]


class TestProvider(Provider):
    """Controlled offline provider simulating normal responses and failure modes."""

    __test__ = False
    name = "test"
    capabilities = ProviderCapabilities(
        search=True,
        episode_listing=True,
        direct_download=True,
        subtitles=True,
        multi_audio=False,
    )

    def __init__(self, failure_mode: FailureMode | None = None) -> None:
        self.failure_mode = failure_mode
        self._series_data: dict[str, ProviderSeries] = {
            "fake-frieren": ProviderSeries(
                id="fake-frieren",
                title="Frieren: Beyond Journey's End",
                provider=self.name,
                url="https://test.local/series/frieren",
                aliases=["Sousou no Frieren"],
                year=2023,
                episode_count=12,
            ),
            "fake-aot": ProviderSeries(
                id="fake-aot",
                title="Attack on Titan",
                provider=self.name,
                url="https://test.local/series/aot",
                aliases=["Shingeki no Kyojin"],
                year=2013,
                episode_count=12,
            ),
            "fake-steins": ProviderSeries(
                id="fake-steins",
                title="Steins;Gate",
                provider=self.name,
                url="https://test.local/series/steinsgate",
                aliases=["Steins Gate"],
                year=2011,
                episode_count=12,
            ),
        }

    async def search(self, query: str) -> list[ProviderSeries]:
        self._check_failure()
        q = query.strip().lower()
        results: list[ProviderSeries] = []
        for s in self._series_data.values():
            if q in s.title.lower() or any(q in a.lower() for a in s.aliases):
                results.append(s)
        return results

    async def get_series(self, series_id: str) -> ProviderSeries:
        self._check_failure()
        if series_id not in self._series_data:
            raise ProviderError(f"Series '{series_id}' not found (HTTP 404 simulated).")
        return self._series_data[series_id]

    async def get_episodes(self, series_id: str) -> list[ProviderEpisode]:
        self._check_failure()
        if series_id not in self._series_data:
            raise ProviderError(f"Series '{series_id}' not found.")

        # Generate 12 fake episodes
        return [
            ProviderEpisode(
                id=f"{series_id}-ep-{i:02d}",
                series_id=series_id,
                number=float(i),
                title=f"Episode {i}",
                url=f"https://test.local/series/{series_id}/ep/{i}",
            )
            for i in range(1, 13)
        ]

    async def get_media(self, episode: ProviderEpisode) -> EpisodeMedia:
        self._check_failure()

        variants: list[MediaVariant] = []
        if self.failure_mode != "missing_quality":
            variants = [
                MediaVariant(
                    url=f"https://test.local/streams/{episode.id}/1080p.mp4",
                    quality="1080p",
                    width=1920,
                    height=1080,
                    codec="h264",
                    container="mp4",
                    bitrate=5_000_000,
                    audio_language="ja",
                    subtitle_languages=["en"],
                    size=200_000_000,
                ),
                MediaVariant(
                    url=f"https://test.local/streams/{episode.id}/720p.mp4",
                    quality="720p",
                    width=1280,
                    height=720,
                    codec="h264",
                    container="mp4",
                    bitrate=2_500_000,
                    audio_language="ja",
                    subtitle_languages=["en"],
                    size=100_000_000,
                ),
            ]

        subtitles: list[SubtitleTrack] = []
        if self.failure_mode != "missing_subtitle":
            subtitles = [
                SubtitleTrack(
                    language="en",
                    title="English Subtitle",
                    url=f"https://test.local/subtitles/{episode.id}/en.ass",
                    format="ass",
                )
            ]

        return EpisodeMedia(
            episode_id=episode.id,
            variants=variants,
            subtitles=subtitles,
        )

    async def health_check(self) -> bool:
        return self.failure_mode != "unhealthy"

    def _check_failure(self) -> None:
        if self.failure_mode == "500":
            raise ProviderError("Simulated internal server error (HTTP 500).")
        if self.failure_mode == "429":
            raise ProviderError("Simulated rate limit exceeded (HTTP 429).")
        if self.failure_mode == "timeout":
            raise TimeoutError("Simulated connection timeout.")
        if self.failure_mode == "404":
            raise ProviderError("Simulated resource not found (HTTP 404).")
