from typing import Any

import httpx

from anibatch.core.enums import AnimeStatus
from anibatch.core.models import Anime
from anibatch.metadata.base import MetadataProvider

ANILIST_API_URL = "https://graphql.anilist.co"

ANILIST_SEARCH_QUERY = """
query ($search: String, $id: Int) {
  Page(page: 1, perPage: 10) {
    media(search: $search, id: $id, type: ANIME) {
      id
      title {
        romaji
        english
        native
      }
      synonyms
      startDate {
        year
      }
      season
      episodes
      status
      coverImage {
        large
      }
    }
  }
}
"""

STATUS_MAP = {
    "FINISHED": AnimeStatus.FINISHED,
    "RELEASING": AnimeStatus.RELEASING,
    "NOT_YET_RELEASED": AnimeStatus.NOT_YET_RELEASED,
    "CANCELLED": AnimeStatus.CANCELLED,
    "HIATUS": AnimeStatus.HIATUS,
}


class AniListMetadataProvider(MetadataProvider):
    """AniList GraphQL metadata provider with local caching."""

    name = "anilist"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        cache_backend: dict[str, Any] | None = None,
    ) -> None:
        self._client = client
        self._owns_client = client is None
        self._cache: dict[str, Any] = cache_backend if cache_backend is not None else {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search(self, query: str) -> list[Anime]:
        cache_key = f"search:{query.strip().lower()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        client = await self._get_client()
        response = await client.post(
            ANILIST_API_URL,
            json={"query": ANILIST_SEARCH_QUERY, "variables": {"search": query}},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        media_list = data.get("data", {}).get("Page", {}).get("media", [])

        results = [self._parse_media(item) for item in media_list]
        self._cache[cache_key] = results
        for anime in results:
            self._cache[f"anime:{anime.metadata_id}"] = anime

        return results

    async def get_anime(self, anime_id: str | int) -> Anime | None:
        cache_key = f"anime:{anime_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            numeric_id = int(anime_id)
        except ValueError:
            return None

        client = await self._get_client()
        response = await client.post(
            ANILIST_API_URL,
            json={"query": ANILIST_SEARCH_QUERY, "variables": {"id": numeric_id}},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        media_list = data.get("data", {}).get("Page", {}).get("media", [])
        if not media_list:
            return None

        anime = self._parse_media(media_list[0])
        self._cache[cache_key] = anime
        return anime

    def _parse_media(self, item: dict[str, Any]) -> Anime:
        titles = item.get("title", {}) or {}
        romaji = titles.get("romaji")
        english = titles.get("english")
        native = titles.get("native")
        main_title = english or romaji or native or f"Anime {item.get('id')}"

        aliases = list(item.get("synonyms") or [])
        for alt in (romaji, english, native):
            if alt and alt != main_title and alt not in aliases:
                aliases.append(alt)

        status_str = item.get("status") or "UNKNOWN"
        status = STATUS_MAP.get(status_str, AnimeStatus.UNKNOWN)

        year = None
        start_date = item.get("startDate")
        if start_date and start_date.get("year"):
            year = start_date["year"]

        cover_url = None
        cover_image = item.get("coverImage")
        if cover_image:
            cover_url = cover_image.get("large")

        return Anime(
            id=str(item["id"]),
            metadata_id=str(item["id"]),
            metadata_source="anilist",
            title=main_title,
            english_title=english,
            romaji_title=romaji,
            native_title=native,
            aliases=aliases,
            year=year,
            season=item.get("season"),
            episode_count=item.get("episodes"),
            status=status,
            cover_url=cover_url,
        )
