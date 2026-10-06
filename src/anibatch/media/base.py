from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from anibatch.core.models import SubtitleTrack


class MediaProcessor(ABC):
    """Abstract interface for media inspection, validation, and muxing."""

    @abstractmethod
    async def inspect(self, file_path: Path) -> dict[str, Any]:
        """Probe media file and extract stream metadata."""
        ...

    @abstractmethod
    async def mux_subtitles(
        self,
        video_file: Path,
        subtitles: list[SubtitleTrack],
        output_file: Path,
    ) -> Path:
        """Mux video and subtitle streams into final container (e.g. MKV/MP4)."""
        ...

    @abstractmethod
    async def verify(self, file_path: Path) -> bool:
        """Verify video/audio integrity of a downloaded or muxed file."""
        ...
