import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from types import TracebackType
from typing import Self
from urllib.parse import quote_plus

import httpx

from anibatch.core.exceptions import ProviderError
from anibatch.core.models import (
    EpisodeMedia,
    MediaVariant,
    ProviderCapabilities,
    ProviderEpisode,
    ProviderSeries,
)
from anibatch.providers.base import Provider

NYAA_RSS_URL = "https://nyaa.si/?page=rss"


@dataclass
class _NyaaRelease:
    title: str
    link: str
    guid: str
    seeders: int = 0


class NyaaProvider(Provider):
    """Provider adapter interfacing with Nyaa anime RSS feed."""

    name = "nyaa"
    capabilities = ProviderCapabilities(
        search=True,
        episode_listing=True,
        direct_download=True,
        subtitles=True,
        multi_audio=True,
    )

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None
        self._series_cache: dict[str, ProviderSeries] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self) -> None:
        """Close internal HTTP client if owned."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @staticmethod
    def _slugify(text: str) -> str:
        cleaned = re.sub(r"[^\w\s-]", "", text).strip().lower()
        return re.sub(r"[\s_-]+", "-", cleaned)

    @staticmethod
    def _clean_series_title(raw_title: str) -> str:
        # Strip leading brackets/tags e.g. [SubsPlease] [Erai-raws]
        title = re.sub(r"^(?:\[[^\]]*\]\s*)+", "", raw_title)
        # Strip file extension
        title = re.sub(r"\.(?:mkv|mp4|avi)$", "", title, flags=re.IGNORECASE)
        # Strip trailing tags [...] and (...)
        while True:
            stripped = re.sub(r"(?:\s*\[[^\]]*\]|\s*\([^\)]*\))\s*$", "", title)
            if stripped == title:
                break
            title = stripped

        # Extract episode pattern to isolate series title
        match = re.search(
            r"\s+-\s+(?:S\d{1,2})?(?:E(?:P|pisode)?\s*)?(\d{1,4}(?:\.\d)?)(?:v\d+)?(?:\s+.*)?$",
            title,
            flags=re.IGNORECASE,
        )
        if match:
            title = title[: match.start()].strip()
        else:
            match2 = re.search(
                r"\s+(?:S\d{1,2})?(?:E(?:P|pisode)?\s*)?(\d{1,4}(?:\.\d)?)(?:v\d+)?$",
                title,
                flags=re.IGNORECASE,
            )
            if match2:
                title = title[: match2.start()].strip()

        return title.strip()

    @staticmethod
    def _extract_episode_number(raw_title: str) -> float | None:
        title = re.sub(r"\.(?:mkv|mp4|avi)$", "", raw_title, flags=re.IGNORECASE)
        # 1. SxxExx or Exx
        m = re.search(r"(?i)\b(?:S\d{1,2})?E(\d{1,4}(?:\.\d)?)(?:v\d+)?\b", title)
        if m:
            return float(m.group(1))
        # 2. Episode / EP
        m = re.search(r"(?i)\b(?:EP|Episode)\s*(\d{1,4}(?:\.\d)?)(?:v\d+)?\b", title)
        if m:
            return float(m.group(1))
        # 3. ' - 01' or ' - 01v2'
        matches = list(re.finditer(r"-\s*(\d{1,4}(?:\.\d)?)(?:v\d+)?\b", title))
        if matches:
            return float(matches[-1].group(1))
        return None

    @staticmethod
    def _score_release(title: str, seeders: int) -> tuple[int, int]:
        t = title.lower()
        quality_score = 0
        if "1080p" in t:
            quality_score = 3
        elif "720p" in t:
            quality_score = 2
        elif "480p" in t:
            quality_score = 1
        return (quality_score, seeders)

    def _find_text(self, elem: ET.Element, tag_name: str) -> str:
        text = elem.findtext(tag_name)
        if text:
            return text.strip()

        for child in elem:
            tag = child.tag
            if (
                tag.endswith((f"}}{tag_name}", f":{tag_name}"))
                or tag == tag_name
            ) and child.text:
                return child.text.strip()
        return ""

    def _parse_rss(self, xml_content: str) -> list[_NyaaRelease]:
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            raise ProviderError(f"Failed to parse Nyaa RSS XML: {exc}") from exc

        items: list[_NyaaRelease] = []
        for item_elem in root.findall(".//item"):
            title = self._find_text(item_elem, "title")
            link = self._find_text(item_elem, "link")
            guid = self._find_text(item_elem, "guid")
            seeders_str = self._find_text(item_elem, "seeders")

            try:
                seeders = int(seeders_str) if seeders_str else 0
            except ValueError:
                seeders = 0

            if not link and guid:
                view_match = re.search(r"/view/(\d+)", guid)
                if view_match:
                    link = f"https://nyaa.si/download/{view_match.group(1)}.torrent"

            if title:
                items.append(_NyaaRelease(title=title, link=link, guid=guid, seeders=seeders))

        return items

    async def _fetch_rss(self, query: str) -> str:
        client = await self._get_client()
        params = {
            "page": "rss",
            "q": query,
            "c": "1_2",
            "f": "0",
        }
        try:
            resp = await client.get(NYAA_RSS_URL, params=params)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError as exc:
            raise ProviderError(f"Failed to query Nyaa RSS feed: {exc}") from exc

    async def search(self, query: str) -> list[ProviderSeries]:
        """Search for series matching the given query."""
        xml_content = await self._fetch_rss(query)
        items = self._parse_rss(xml_content)

        series_map: dict[str, ProviderSeries] = {}
        episodes_per_series: dict[str, set[float]] = {}

        for item in items:
            clean_title = self._clean_series_title(item.title)
            if not clean_title:
                continue
            slug = self._slugify(clean_title)
            ep_num = self._extract_episode_number(item.title)

            if slug not in series_map:
                series = ProviderSeries(
                    id=slug,
                    title=clean_title,
                    provider=self.name,
                    url=f"https://nyaa.si/?q={quote_plus(clean_title)}&c=1_2&f=0",
                    aliases=[],
                )
                series_map[slug] = series
                episodes_per_series[slug] = set()

            if ep_num is not None:
                episodes_per_series[slug].add(ep_num)

        for slug, series in series_map.items():
            ep_count = len(episodes_per_series[slug])
            if ep_count > 0:
                series.episode_count = ep_count
            self._series_cache[slug] = series
            self._series_cache[series.title.lower()] = series

        return list(series_map.values())

    async def get_series(self, series_id: str) -> ProviderSeries:
        """Retrieve detailed series information by provider series ID."""
        slug = self._slugify(series_id)
        if slug in self._series_cache:
            return self._series_cache[slug]
        if series_id.lower() in self._series_cache:
            return self._series_cache[series_id.lower()]

        results = await self.search(series_id)
        for s in results:
            if s.id == slug or self._slugify(s.title) == slug or s.id == series_id:
                return s
        if results:
            return results[0]

        raise ProviderError(f"Series '{series_id}' not found on Nyaa.")

    async def get_episodes(self, series_id: str) -> list[ProviderEpisode]:
        """Retrieve list of available episodes for a series."""
        xml_content = await self._fetch_rss(series_id)
        items = self._parse_rss(xml_content)

        candidates_by_ep: dict[float, list[_NyaaRelease]] = {}
        no_ep_items: list[_NyaaRelease] = []

        for item in items:
            ep_num = self._extract_episode_number(item.title)
            if ep_num is not None:
                candidates_by_ep.setdefault(ep_num, []).append(item)
            else:
                no_ep_items.append(item)

        if not candidates_by_ep and no_ep_items:
            candidates_by_ep[1.0] = no_ep_items

        episodes: list[ProviderEpisode] = []
        for ep_num in sorted(candidates_by_ep.keys()):
            item_list = candidates_by_ep[ep_num]
            best_item = max(item_list, key=lambda it: self._score_release(it.title, it.seeders))

            ep_int_str = f"{int(ep_num):02d}" if ep_num.is_integer() else f"{ep_num}"
            ep_id = f"{series_id}-{ep_int_str}"

            episodes.append(
                ProviderEpisode(
                    id=ep_id,
                    series_id=series_id,
                    number=ep_num,
                    title=best_item.title,
                    url=best_item.link or best_item.guid,
                )
            )

        return episodes

    async def get_media(self, episode: ProviderEpisode) -> EpisodeMedia:
        """Retrieve media variants for an episode."""
        quality = "1080p"
        container = "mkv"
        codec = "h264"

        if episode.title:
            t = episode.title.lower()
            if "720p" in t:
                quality = "720p"
            elif "480p" in t:
                quality = "480p"
            elif "2160p" in t or "4k" in t:
                quality = "2160p"

            if t.endswith(".mp4") or "[mp4]" in t:
                container = "mp4"

            if (
                "x265" in t
                or "hevc" in t
                or "h265" in t
                or "h.265" in t
            ):
                codec = "h265"

        return EpisodeMedia(
            episode_id=episode.id,
            variants=[
                MediaVariant(
                    url=episode.url or "",
                    quality=quality,
                    container=container,
                    codec=codec,
                )
            ],
            subtitles=[],
        )

    async def health_check(self) -> bool:
        """Check if provider is online and reachable."""
        try:
            client = await self._get_client()
            resp = await client.get(
                NYAA_RSS_URL,
                params={"page": "rss", "q": "test", "c": "1_2"},
            )
            return resp.status_code == 200
        except Exception:  # noqa: BLE001
            return False
