import httpx
import pytest
import respx

from anibatch.core.models import EpisodeMedia, ProviderSeries
from anibatch.providers.base import Provider
from anibatch.providers.nyaa.provider import NYAA_RSS_URL, NyaaProvider

MOCK_NYAA_SEARCH_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:nyaa="https://nyaa.si/xmlns/nyaa">
  <channel>
    <title>Nyaa - Anime - English-translated</title>
    <item>
      <title>[SubsPlease] Frieren - 01 (1080p) [ABCD1234].mkv</title>
      <link>https://nyaa.si/download/100001.torrent</link>
      <guid isPermaLink="true">https://nyaa.si/view/100001</guid>
      <nyaa:seeders>150</nyaa:seeders>
      <nyaa:leechers>5</nyaa:leechers>
      <nyaa:size>1.4 GiB</nyaa:size>
    </item>
    <item>
      <title>[SubsPlease] Frieren - 01 (720p) [ABCD1235].mkv</title>
      <link>https://nyaa.si/download/100002.torrent</link>
      <guid isPermaLink="true">https://nyaa.si/view/100002</guid>
      <nyaa:seeders>30</nyaa:seeders>
      <nyaa:leechers>1</nyaa:leechers>
      <nyaa:size>800 MiB</nyaa:size>
    </item>
    <item>
      <title>[SubsPlease] Frieren - 02 (1080p) [ABCD1236].mkv</title>
      <link>https://nyaa.si/download/100003.torrent</link>
      <guid isPermaLink="true">https://nyaa.si/view/100003</guid>
      <nyaa:seeders>120</nyaa:seeders>
      <nyaa:leechers>3</nyaa:leechers>
      <nyaa:size>1.4 GiB</nyaa:size>
    </item>
    <item>
      <title>[SubsPlease] Frieren (01-28) [Batch] (1080p) [ABCD9999].mkv</title>
      <link>https://nyaa.si/download/100004.torrent</link>
      <guid isPermaLink="true">https://nyaa.si/view/100004</guid>
      <nyaa:seeders>250</nyaa:seeders>
      <nyaa:leechers>10</nyaa:leechers>
      <nyaa:size>35.0 GiB</nyaa:size>
    </item>
  </channel>
</rss>
"""


@pytest.mark.asyncio
async def test_nyaa_provider_contract(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(NYAA_RSS_URL).respond(200, text=MOCK_NYAA_SEARCH_RSS)

    async with httpx.AsyncClient() as client:
        provider = NyaaProvider(client=client)
        assert isinstance(provider, Provider)
        assert provider.name == "nyaa"
        assert provider.capabilities.search is True
        assert provider.capabilities.episode_listing is True
        assert provider.capabilities.direct_download is True

        # 1. Search
        series_list = await provider.search("Frieren")
        assert len(series_list) >= 1
        series = series_list[0]
        assert isinstance(series, ProviderSeries)
        assert "frieren" in series.id
        assert series.episode_count == 2  # ep 1 and ep 2 (batch excluded)

        # 2. Get Series
        retrieved_series = await provider.get_series(series.id)
        assert retrieved_series.id == series.id

        # 3. Get Episodes
        episodes = await provider.get_episodes(series.id)
        assert len(episodes) == 2
        assert episodes[0].number == 1.0
        assert episodes[1].number == 2.0
        # Preferred 1080p release over 720p
        assert "1080p" in episodes[0].title
        assert episodes[0].url == "https://nyaa.si/download/100001.torrent"

        # 4. Get Media
        media = await provider.get_media(episodes[0])
        assert isinstance(media, EpisodeMedia)
        assert len(media.variants) == 1
        assert media.variants[0].quality == "1080p"
        assert media.variants[0].container == "mkv"
        assert media.variants[0].codec == "h264"
        assert media.variants[0].url == "https://nyaa.si/download/100001.torrent"

        # 5. Health Check
        is_healthy = await provider.health_check()
        assert is_healthy is True


@pytest.mark.asyncio
async def test_nyaa_slug_exclusion_regression(respx_mock: respx.MockRouter) -> None:
    """Regression test ensuring hyphenated slugs are unslugified to avoid Nyaa's '-' exclusion operator."""
    captured_requests = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, text=MOCK_NYAA_SEARCH_RSS)

    respx_mock.get(NYAA_RSS_URL).mock(side_effect=handle_request)

    async with httpx.AsyncClient() as client:
        provider = NyaaProvider(client=client)
        # Direct query with hyphenated ID not in cache
        episodes = await provider.get_episodes("sousou-no-frieren")
        assert len(episodes) == 2

        # Verify that outgoing HTTP request did NOT query with hyphens which triggers Nyaa exclusion
        assert len(captured_requests) > 0
        req = captured_requests[-1]
        assert "sousou-no-frieren" not in req.url.query.decode()
        assert (
            "sousou+no+frieren" in req.url.query.decode()
            or "sousou no frieren" in req.url.query.decode()
        )


@pytest.mark.asyncio
async def test_nyaa_quality_scoring_and_batch_exclusion(respx_mock: respx.MockRouter) -> None:
    score_4k = NyaaProvider._score_release("Anime - 01 [2160p]", 10)
    score_1080p = NyaaProvider._score_release("Anime - 01 [1080p]", 10)
    score_720p = NyaaProvider._score_release("Anime - 01 [720p]", 10)

    assert score_4k[0] == 4
    assert score_1080p[0] == 3
    assert score_720p[0] == 2
    assert score_4k > score_1080p > score_720p
