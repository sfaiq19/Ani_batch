import pytest

from anibatch.core.exceptions import ProviderError
from anibatch.providers.base import Provider
from anibatch.providers.registry import ProviderRegistry
from anibatch.providers.test_provider.provider import TestProvider


@pytest.mark.asyncio
async def test_test_provider_contract() -> None:
    provider = TestProvider()
    assert isinstance(provider, Provider)
    assert provider.name == "test"
    assert provider.capabilities.search is True
    assert provider.capabilities.episode_listing is True
    assert provider.capabilities.direct_download is True
    assert provider.capabilities.subtitles is True

    # Search
    results = await provider.search("Frieren")
    assert len(results) == 1
    series = results[0]
    assert series.id == "fake-frieren"
    assert series.title == "Frieren: Beyond Journey's End"
    assert series.year == 2023

    # All 3 series accessible
    s1 = await provider.get_series("fake-frieren")
    s2 = await provider.get_series("fake-aot")
    s3 = await provider.get_series("fake-steins")
    assert s1.title == "Frieren: Beyond Journey's End"
    assert s2.title == "Attack on Titan"
    assert s3.title == "Steins;Gate"

    # Exactly 12 episodes
    episodes = await provider.get_episodes("fake-frieren")
    assert len(episodes) == 12
    assert episodes[0].number == 1.0
    assert episodes[11].number == 12.0

    # Media streams and subtitles
    media = await provider.get_media(episodes[0])
    assert len(media.variants) == 2
    qualities = [v.quality for v in media.variants]
    assert "1080p" in qualities
    assert "720p" in qualities

    assert len(media.subtitles) == 1
    assert media.subtitles[0].language == "en"
    assert media.subtitles[0].format == "ass"

    # Health check
    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_test_provider_failure_modes() -> None:
    # 500
    p_500 = TestProvider(failure_mode="500")
    with pytest.raises(ProviderError, match="500"):
        await p_500.search("Frieren")

    # 429
    p_429 = TestProvider(failure_mode="429")
    with pytest.raises(ProviderError, match="429"):
        await p_429.get_episodes("fake-frieren")

    # Timeout
    p_timeout = TestProvider(failure_mode="timeout")
    with pytest.raises(TimeoutError):
        await p_timeout.get_series("fake-frieren")

    # Missing quality
    p_no_qual = TestProvider(failure_mode="missing_quality")
    episodes = await p_no_qual.get_episodes("fake-frieren")
    media = await p_no_qual.get_media(episodes[0])
    assert len(media.variants) == 0

    # Missing subtitles
    p_no_sub = TestProvider(failure_mode="missing_subtitle")
    media_no_sub = await p_no_sub.get_media(episodes[0])
    assert len(media_no_sub.subtitles) == 0

    # Unhealthy
    p_unhealthy = TestProvider(failure_mode="unhealthy")
    assert await p_unhealthy.health_check() is False


@pytest.mark.asyncio
async def test_provider_registry() -> None:
    reg = ProviderRegistry()
    test_prov = TestProvider()
    reg.register(test_prov)

    assert "test" in reg.list_available()
    retrieved = reg.get("test")
    assert retrieved is test_prov

    health = await reg.health_check_all()
    assert health["test"] is True
