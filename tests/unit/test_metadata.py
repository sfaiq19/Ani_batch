import httpx
import pytest
import respx

from anibatch.core.enums import AnimeStatus
from anibatch.core.models import Anime
from anibatch.metadata.anilist import ANILIST_API_URL, AniListMetadataProvider
from anibatch.metadata.matcher import find_best_match, normalize_title

MOCK_GRAPHQL_SEARCH_PAYLOAD = {
    "data": {
        "Page": {
            "media": [
                {
                    "id": 154587,
                    "title": {
                        "romaji": "Sousou no Frieren",
                        "english": "Frieren: Beyond Journey's End",
                        "native": "葬送のフリーレン",
                    },
                    "synonyms": ["Frieren at the Funeral"],
                    "startDate": {"year": 2023},
                    "season": "FALL",
                    "episodes": 28,
                    "status": "FINISHED",
                    "coverImage": {"large": "https://example.com/frieren.jpg"},
                }
            ]
        }
    }
}


@pytest.mark.asyncio
async def test_anilist_search_with_mock(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ANILIST_API_URL).respond(200, json=MOCK_GRAPHQL_SEARCH_PAYLOAD)

    async with httpx.AsyncClient() as client:
        provider = AniListMetadataProvider(client=client)
        results = await provider.search("Frieren")

        assert len(results) == 1
        anime = results[0]
        assert anime.id == "154587"
        assert anime.title == "Frieren: Beyond Journey's End"
        assert anime.english_title == "Frieren: Beyond Journey's End"
        assert anime.romaji_title == "Sousou no Frieren"
        assert anime.year == 2023
        assert anime.season == "FALL"
        assert anime.episode_count == 28
        assert anime.status == AnimeStatus.FINISHED
        assert anime.cover_url == "https://example.com/frieren.jpg"
        assert "Frieren at the Funeral" in anime.aliases


@pytest.mark.asyncio
async def test_anilist_caching_behavior(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.post(ANILIST_API_URL).respond(200, json=MOCK_GRAPHQL_SEARCH_PAYLOAD)

    async with httpx.AsyncClient() as client:
        provider = AniListMetadataProvider(client=client)

        # First query should hit network mock
        res1 = await provider.search("Frieren")
        assert len(res1) == 1
        assert route.call_count == 1

        # Second identical query should hit cache
        res2 = await provider.search("Frieren")
        assert len(res2) == 1
        assert route.call_count == 1

        # Direct get_anime by ID should also hit the populated cache
        cached_anime = await provider.get_anime("154587")
        assert cached_anime is not None
        assert cached_anime.id == "154587"
        assert route.call_count == 1


@pytest.mark.asyncio
async def test_anilist_get_anime_by_id(respx_mock: respx.MockRouter) -> None:
    respx_mock.post(ANILIST_API_URL).respond(200, json=MOCK_GRAPHQL_SEARCH_PAYLOAD)

    async with httpx.AsyncClient() as client:
        provider = AniListMetadataProvider(client=client)
        anime = await provider.get_anime("154587")
        assert anime is not None
        assert anime.id == "154587"
        assert anime.title == "Frieren: Beyond Journey's End"


def test_title_normalizer() -> None:
    assert normalize_title("Attack on Titan: Season 1") == "attack on titan"
    assert normalize_title("Jujutsu Kaisen 2nd Season!") == "jujutsu kaisen"
    assert normalize_title("Frieren: Beyond Journey's End") == "frieren beyond journey s end"


def test_matcher_scoring_and_selection() -> None:
    frieren = Anime(
        id="1",
        title="Frieren: Beyond Journey's End",
        english_title="Frieren: Beyond Journey's End",
        romaji_title="Sousou no Frieren",
        aliases=["Frieren"],
        year=2023,
        episode_count=28,
        status=AnimeStatus.FINISHED,
    )
    unrelated = Anime(
        id="2",
        title="Bleach",
        year=2004,
        episode_count=366,
        status=AnimeStatus.FINISHED,
    )

    candidates = [frieren, unrelated]

    # Exact title match
    best, score = find_best_match("Frieren: Beyond Journey's End", candidates, threshold=0.75)
    assert best is not None
    assert best.id == "1"
    assert score >= 0.85

    # Alias / Romaji match
    best_romaji, romaji_score = find_best_match("Sousou no Frieren", candidates, threshold=0.75)
    assert best_romaji is not None
    assert best_romaji.id == "1"
    assert romaji_score >= 0.85

    # Below threshold query
    none_match, low_score = find_best_match("Naruto Shippuden", candidates, threshold=0.75)
    assert none_match is None
    assert low_score < 0.75
