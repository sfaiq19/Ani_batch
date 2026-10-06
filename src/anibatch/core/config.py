import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def get_default_config_path() -> Path:
    """Return platform-appropriate configuration file path."""
    if os.name == "nt":
        app_data = os.environ.get("APPDATA")
        base = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return base / "anibatch" / "config.toml"
    return Path.home() / ".config" / "anibatch" / "config.toml"


class GeneralConfig(BaseModel):
    download_directory: Path = Field(default_factory=lambda: Path("downloads"))
    data_directory: Path = Field(default_factory=lambda: Path("data"))


class DownloadsConfig(BaseModel):
    concurrency: int = 3
    chunk_size: int = 1048576
    timeout: int = 30
    retries: int = 4
    backend: str = "native"


class VideoConfig(BaseModel):
    preferred_quality: str = "1080p"
    fallback: bool = True


class AudioConfig(BaseModel):
    preferred_languages: list[str] = Field(default_factory=lambda: ["ja"])


class SubtitlesConfig(BaseModel):
    preferred_languages: list[str] = Field(default_factory=lambda: ["en"])
    embed: bool = True
    keep_external: bool = False


class NamingConfig(BaseModel):
    season_folders: bool = True
    series_folder: str = "{title}"
    season_folder: str = "Season {season:02d}"
    episode: str = "{title} - S{season:02d}E{episode:02d} - {episode_title}"


class MetadataConfig(BaseModel):
    provider: str = "anilist"


class AniBatchConfig(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    downloads: DownloadsConfig = Field(default_factory=DownloadsConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    subtitles: SubtitlesConfig = Field(default_factory=SubtitlesConfig)
    naming: NamingConfig = Field(default_factory=NamingConfig)
    metadata: MetadataConfig = Field(default_factory=MetadataConfig)

    @classmethod
    def load(cls, path: Path | None = None) -> "AniBatchConfig":
        config_path = path or get_default_config_path()
        if not config_path.exists():
            return cls()

        with open(config_path, "rb") as f:
            data: dict[str, Any] = tomllib.load(f)
        return cls.model_validate(data)
