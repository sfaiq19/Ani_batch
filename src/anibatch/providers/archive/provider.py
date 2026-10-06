import httpx

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

ARCHIVE_API_BASE = "https://archive.org/advancedsearch.php"


class ArchiveProvider(Provider):
    """Provider adapter interfacing with open authorized media archive endpoints."""

    name = "archive"
    capabilities = ProviderCapabilities(
        search=True,
        episode_listing=True,
        direct_download=True,
        subtitles=True,
        multi_audio=False,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search(self, query: str) -> list[ProviderSeries]:
        """Search open archive collection for media matching query."""
        client = await self._get_client()
        params = httpx.QueryParams(
            [
                ("q", f"title:({query}) AND mediatype:(movies)"),
                ("fl[]", "identifier"),
                ("fl[]", "title"),
                ("fl[]", "year"),
                ("output", "json"),
                ("rows", "10"),
            ]
        )
        try:
            resp = await client.get(ARCHIVE_API_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
            docs = data.get("response", {}).get("docs", [])
            return [
                ProviderSeries(
                    id=doc["identifier"],
                    title=doc.get("title", doc["identifier"]),
                    provider=self.name,
                    url=f"https://archive.org/details/{doc['identifier']}",
                    year=int(doc["year"]) if "year" in doc and str(doc["year"]).isdigit() else None,
                )
                for doc in docs
            ]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ProviderError(f"Failed to query archive collection: {exc}") from exc

    async def get_series(self, series_id: str) -> ProviderSeries:
        """Fetch series item metadata."""
        client = await self._get_client()
        url = f"https://archive.org/metadata/{series_id}"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            meta = data.get("metadata", {})
            return ProviderSeries(
                id=series_id,
                title=meta.get("title", series_id),
                provider=self.name,
                url=f"https://archive.org/details/{series_id}",
                year=int(meta["year"]) if "year" in meta and str(meta["year"]).isdigit() else None,
            )
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ProviderError(
                f"Failed to fetch archive metadata for '{series_id}': {exc}"
            ) from exc

    async def get_episodes(self, series_id: str) -> list[ProviderEpisode]:
        """Parse available episode files from media item."""
        client = await self._get_client()
        url = f"https://archive.org/metadata/{series_id}"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            files = data.get("files", [])

            episodes: list[ProviderEpisode] = []
            ep_num = 1
            for f in files:
                name = f.get("name", "")
                if name.endswith((".mp4", ".mkv")):
                    episodes.append(
                        ProviderEpisode(
                            id=f"{series_id}:{name}",
                            series_id=series_id,
                            number=float(ep_num),
                            title=f.get("title") or name,
                            url=f"https://archive.org/download/{series_id}/{name}",
                        )
                    )
                    ep_num += 1

            if not episodes:
                # Fallback to single primary feature episode
                episodes.append(
                    ProviderEpisode(
                        id=f"{series_id}:main",
                        series_id=series_id,
                        number=1.0,
                        title=series_id,
                        url=f"https://archive.org/download/{series_id}/{series_id}.mp4",
                    )
                )

            return episodes
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ProviderError(f"Failed to fetch episodes for '{series_id}': {exc}") from exc

    async def get_media(self, episode: ProviderEpisode) -> EpisodeMedia:
        """Construct media variant from archive download URL."""
        stream_url = episode.url or f"https://archive.org/download/{episode.series_id}/{episode.id}"
        variants = [
            MediaVariant(
                url=stream_url,
                quality="1080p",
                container="mp4",
                codec="h264",
                audio_language="ja",
            )
        ]
        subtitles = [
            SubtitleTrack(
                language="en",
                url=f"https://archive.org/download/{episode.series_id}/sub_en.srt",
                format="srt",
            )
        ]
        return EpisodeMedia(
            episode_id=episode.id,
            variants=variants,
            subtitles=subtitles,
        )

    async def health_check(self) -> bool:
        """Verify archive gateway reachability."""
        client = await self._get_client()
        try:
            resp = await client.get(
                ARCHIVE_API_BASE,
                params={"q": "collection:(movies)", "rows": 1, "output": "json"},
            )
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False
