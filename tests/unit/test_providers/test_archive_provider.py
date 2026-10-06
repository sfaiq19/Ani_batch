import httpx
import pytest
import respx

from anibatch.providers.archive.provider import ARCHIVE_API_BASE, ArchiveProvider
from anibatch.providers.base import Provider

MOCK_ARCHIVE_SEARCH_RESPONSE = {
    "response": {
        "docs": [
            {
                "identifier": "night-of-the-living-dead-1968",
                "title": "Night of the Living Dead",
                "year": "1968",
            }
        ]
    }
}

MOCK_METADATA_RESPONSE = {
    "metadata": {
        "identifier": "night-of-the-living-dead-1968",
        "title": "Night of the Living Dead",
        "year": "1968",
    },
    "files": [
        {"name": "notld_feature.mp4", "title": "Main Feature Film"},
        {"name": "subtitles_en.srt", "title": "English Subtitles"},
    ],
}


@pytest.mark.asyncio
async def test_archive_provider_contract(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ARCHIVE_API_BASE).respond(200, json=MOCK_ARCHIVE_SEARCH_RESPONSE)
    respx_mock.get("https://archive.org/metadata/night-of-the-living-dead-1968").respond(
        200, json=MOCK_METADATA_RESPONSE
    )

    async with httpx.AsyncClient() as client:
        provider = ArchiveProvider(client=client)
        assert isinstance(provider, Provider)
        assert provider.name == "archive"

        # Search
        results = await provider.search("Living Dead")
        assert len(results) == 1
        assert results[0].id == "night-of-the-living-dead-1968"
        assert results[0].year == 1968

        # Get Series
        series = await provider.get_series("night-of-the-living-dead-1968")
        assert series.id == "night-of-the-living-dead-1968"
        assert series.title == "Night of the Living Dead"

        # Get Episodes
        episodes = await provider.get_episodes("night-of-the-living-dead-1968")
        assert len(episodes) == 1
        assert episodes[0].number == 1.0
        assert "notld_feature.mp4" in episodes[0].id

        # Get Media
        media = await provider.get_media(episodes[0])
        assert len(media.variants) == 1
        assert media.variants[0].quality == "1080p"
        assert len(media.subtitles) == 1
        assert media.subtitles[0].language == "en"

        # Health check
        assert await provider.health_check() is True
