from pathlib import Path

from anibatch.naming.sanitizer import sanitize_filename


class PathFormatter:
    """Formats series directories, season folders, and episode filenames according to templates."""

    def __init__(
        self,
        base_dir: Path | str,
        series_folder_template: str = "{title}",
        season_folder_template: str = "Season {season:02d}",
        episode_template: str = "{title} - S{season:02d}E{episode:02d} - {episode_title}",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.series_folder_template = series_folder_template
        self.season_folder_template = season_folder_template
        self.episode_template = episode_template

    def format_destination(
        self,
        anime_title: str,
        season: int,
        episode_num: float,
        episode_title: str | None = None,
        extension: str = "mkv",
    ) -> Path:
        """Construct a sanitized destination path for an episode."""
        ep_title = episode_title or f"Episode {episode_num}"

        clean_series = sanitize_filename(
            self.series_folder_template.format(title=anime_title, season=season)
        )
        clean_season = sanitize_filename(
            self.season_folder_template.format(season=season, title=anime_title)
        )

        ep_int = int(episode_num)
        clean_file_base = sanitize_filename(
            self.episode_template.format(
                title=anime_title,
                season=season,
                episode=ep_int,
                episode_title=ep_title,
            )
        )

        ext = extension.lstrip(".")
        return self.base_dir / clean_series / clean_season / f"{clean_file_base}.{ext}"
