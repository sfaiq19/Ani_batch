from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from anibatch.core.enums import AnimeStatus, DownloadState


class Anime(BaseModel):
    id: str | int
    metadata_id: str | int | None = None
    metadata_source: str = "anilist"
    title: str
    english_title: str | None = None
    romaji_title: str | None = None
    native_title: str | None = None
    aliases: list[str] = Field(default_factory=list)
    year: int | None = None
    season: str | None = None
    episode_count: int | None = None
    status: AnimeStatus = AnimeStatus.UNKNOWN
    cover_url: str | None = None


class Episode(BaseModel):
    id: str | int | None = None
    anime_id: str | int
    number: float
    absolute_number: int | None = None
    title: str | None = None
    air_date: str | None = None
    provider_episode_id: str | None = None


class MediaVariant(BaseModel):
    url: str
    quality: str
    width: int | None = None
    height: int | None = None
    codec: str | None = None
    container: str | None = None
    bitrate: int | None = None
    audio_language: str = "ja"
    subtitle_languages: list[str] = Field(default_factory=list)
    size: int | None = None


class SubtitleTrack(BaseModel):
    language: str
    title: str | None = None
    url: str
    format: str = "ass"
    forced: bool = False
    hearing_impaired: bool = False


class DownloadJob(BaseModel):
    id: str
    anime_id: str | int
    episode_id: str | int
    provider: str
    state: DownloadState = DownloadState.PENDING
    selected_quality: str
    selected_audio: str = "ja"
    selected_subtitle: str | None = "en"
    destination: Path
    temporary_path: Path
    bytes_total: int = 0
    bytes_downloaded: int = 0
    attempts: int = 0
    last_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ProviderSeries(BaseModel):
    id: str
    title: str
    provider: str
    url: str | None = None
    aliases: list[str] = Field(default_factory=list)
    year: int | None = None
    episode_count: int | None = None


class ProviderEpisode(BaseModel):
    id: str
    series_id: str
    number: float
    title: str | None = None
    url: str | None = None


class EpisodeMedia(BaseModel):
    episode_id: str
    variants: list[MediaVariant] = Field(default_factory=list)
    subtitles: list[SubtitleTrack] = Field(default_factory=list)


class ProviderCapabilities(BaseModel):
    search: bool = True
    episode_listing: bool = True
    direct_download: bool = True
    subtitles: bool = True
    multi_audio: bool = False
