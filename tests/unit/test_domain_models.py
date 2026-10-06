from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from anibatch.core.enums import AnimeStatus, DownloadState
from anibatch.core.models import (
    Anime,
    DownloadJob,
    Episode,
    EpisodeMedia,
    MediaVariant,
    ProviderCapabilities,
    ProviderEpisode,
    ProviderSeries,
    SubtitleTrack,
)


def test_anime_model_instantiation() -> None:
    anime = Anime(
        id=154587,
        metadata_id="154587",
        title="Frieren: Beyond Journey's End",
        english_title="Frieren: Beyond Journey's End",
        romaji_title="Sousou no Frieren",
        year=2023,
        season="FALL",
        episode_count=28,
        status=AnimeStatus.FINISHED,
    )
    assert anime.id == 154587
    assert anime.status == AnimeStatus.FINISHED
    assert anime.metadata_source == "anilist"
    assert anime.aliases == []


def test_episode_model_instantiation() -> None:
    ep = Episode(
        anime_id=154587,
        number=1.0,
        absolute_number=1,
        title="The Journey's End",
    )
    assert ep.number == 1.0
    assert ep.anime_id == 154587
    assert ep.title == "The Journey's End"


def test_media_variant_and_subtitle_track() -> None:
    variant = MediaVariant(
        url="https://example.com/video.mp4",
        quality="1080p",
        width=1920,
        height=1080,
        codec="h264",
        container="mp4",
        bitrate=5_000_000,
        audio_language="ja",
        subtitle_languages=["en"],
    )
    assert variant.quality == "1080p"
    assert variant.width == 1920

    sub = SubtitleTrack(
        language="en",
        title="English Subtitles",
        url="https://example.com/sub.ass",
        format="ass",
    )
    assert sub.language == "en"
    assert sub.forced is False


def test_episode_media_container() -> None:
    media = EpisodeMedia(
        episode_id="ep-01",
        variants=[
            MediaVariant(url="https://example.com/1080.mp4", quality="1080p"),
            MediaVariant(url="https://example.com/720.mp4", quality="720p"),
        ],
        subtitles=[
            SubtitleTrack(language="en", url="https://example.com/en.ass"),
        ],
    )
    assert len(media.variants) == 2
    assert len(media.subtitles) == 1


def test_download_job_instantiation_and_state() -> None:
    now = datetime.now(UTC)
    job = DownloadJob(
        id="job-123",
        anime_id=154587,
        episode_id="ep-1",
        provider="test-provider",
        state=DownloadState.PENDING,
        selected_quality="1080p",
        destination=Path("D:/Anime/Frieren/S01E01.mkv"),
        temporary_path=Path("D:/Anime/Frieren/S01E01.mkv.part"),
        created_at=now,
    )
    assert job.id == "job-123"
    assert job.state == DownloadState.PENDING
    assert job.destination == Path("D:/Anime/Frieren/S01E01.mkv")
    assert job.temporary_path == Path("D:/Anime/Frieren/S01E01.mkv.part")
    assert job.attempts == 0
    assert job.bytes_total == 0


def test_provider_series_and_episode() -> None:
    ps = ProviderSeries(
        id="prov-101",
        title="Frieren",
        provider="test-provider",
        year=2023,
    )
    pe = ProviderEpisode(
        id="prov-ep-1",
        series_id="prov-101",
        number=1.0,
        title="Episode 1",
    )
    assert ps.id == "prov-101"
    assert pe.number == 1.0


def test_provider_capabilities_defaults() -> None:
    caps = ProviderCapabilities()
    assert caps.search is True
    assert caps.episode_listing is True
    assert caps.direct_download is True
    assert caps.subtitles is True
    assert caps.multi_audio is False


def test_validation_error_on_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        # Missing required title and id
        Anime.model_validate({})
