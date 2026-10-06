import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from anibatch.core.exceptions import MediaProcessingError
from anibatch.core.models import SubtitleTrack
from anibatch.media.base import MediaProcessor


class FFmpegService(MediaProcessor):
    """FFmpeg and FFprobe wrapper strictly using safe argument vectors."""

    def __init__(
        self,
        ffmpeg_path: str | Path | None = None,
        ffprobe_path: str | Path | None = None,
    ) -> None:
        self.ffmpeg_path = Path(ffmpeg_path) if ffmpeg_path else self._find_binary("ffmpeg")
        self.ffprobe_path = Path(ffprobe_path) if ffprobe_path else self._find_binary("ffprobe")

    @staticmethod
    def _find_binary(name: str) -> Path | None:
        which = shutil.which(name)
        return Path(which) if which else None

    def is_available(self) -> bool:
        return bool(self.ffmpeg_path and self.ffprobe_path)

    async def inspect(self, file_path: Path) -> dict[str, Any]:
        """Inspect media file using ffprobe JSON output."""
        if not self.ffprobe_path:
            raise MediaProcessingError("ffprobe executable not found on system.")
        if not file_path.exists():
            raise MediaProcessingError(f"Media file does not exist: {file_path}")

        cmd = [
            str(self.ffprobe_path),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise MediaProcessingError(
                f"ffprobe failed for {file_path}: {stderr.decode(errors='replace')}"
            )

        try:
            return json.loads(stdout.decode())
        except json.JSONDecodeError as exc:
            raise MediaProcessingError(f"Failed to parse ffprobe output: {exc}") from exc

    async def verify(self, file_path: Path) -> bool:
        """Verify video file has at least one valid video or audio stream and non-zero duration."""
        try:
            info = await self.inspect(file_path)
            streams = info.get("streams", [])
            has_media_stream = any(s.get("codec_type") in ("video", "audio") for s in streams)
            fmt = info.get("format", {})
            duration = float(fmt.get("duration", 0))
            return has_media_stream and (duration > 0 or len(streams) > 0)
        except (MediaProcessingError, KeyError, ValueError, OSError):
            return False

    async def get_duration(self, file_path: Path) -> float | None:
        """Extract media duration in seconds."""
        try:
            info = await self.inspect(file_path)
            fmt = info.get("format", {})
            dur = fmt.get("duration")
            return float(dur) if dur else None
        except (MediaProcessingError, KeyError, ValueError, OSError):
            return None

    async def mux_subtitles(
        self,
        video_file: Path,
        subtitles: list[SubtitleTrack],
        output_file: Path,
    ) -> Path:
        """Mux video stream and subtitle files into output Matroska container."""
        if not self.ffmpeg_path:
            raise MediaProcessingError("ffmpeg executable not found on system.")

        if not video_file.exists():
            raise MediaProcessingError(f"Source video file not found: {video_file}")

        output_file.parent.mkdir(parents=True, exist_ok=True)
        temp_output = output_file.with_name(f"{output_file.stem}.part{output_file.suffix}")

        # Build argument vector
        cmd: list[str] = [
            str(self.ffmpeg_path),
            "-y",  # overwrite temporary output if exists
            "-i",
            str(video_file),
        ]

        # Add subtitle inputs
        for sub in subtitles:
            cmd.extend(["-i", sub.url])

        # Map original video & audio
        cmd.extend(["-map", "0:v?", "-map", "0:a?"])

        # Map subtitles and attach metadata
        for idx, sub in enumerate(subtitles, start=1):
            cmd.extend(
                [
                    "-map",
                    f"{idx}:s?",
                    f"-metadata:s:s:{idx - 1}",
                    f"language={sub.language}",
                ]
            )
            if sub.title:
                cmd.extend([f"-metadata:s:s:{idx - 1}", f"title={sub.title}"])

        # Copy streams without re-encoding
        cmd.extend(["-c", "copy", str(temp_output)])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            if temp_output.exists():
                temp_output.unlink()
            raise MediaProcessingError(f"FFmpeg muxing failed: {stderr.decode(errors='replace')}")

        # Verification step: ensure temp_output is valid before renaming
        is_valid = await self.verify(temp_output)
        if not is_valid:
            if temp_output.exists():
                temp_output.unlink()
            raise MediaProcessingError(f"Verification failed on muxed output: {temp_output}")

        if output_file.exists():
            output_file.unlink()
        temp_output.replace(output_file)

        return output_file
