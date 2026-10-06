import asyncio
from pathlib import Path

import pytest

from anibatch.core.models import SubtitleTrack
from anibatch.media.ffmpeg import FFmpegService
from anibatch.naming.formatter import PathFormatter
from anibatch.naming.sanitizer import sanitize_filename


def test_sanitizer_illegal_and_reserved_characters() -> None:
    # Illegal chars
    dirty = 'Frieren: Beyond Journey\'s "End" <Director/s Cut>?*|'
    cleaned = sanitize_filename(dirty)
    for bad in '<>:"/\\|?*':
        assert bad not in cleaned

    # Trailing dots/spaces
    assert sanitize_filename("Anime Title. . . ") == "Anime Title"

    # Reserved Windows names
    assert sanitize_filename("CON.mp4") == "_CON.mp4"
    assert sanitize_filename("nul.mkv") == "_nul.mkv"
    assert sanitize_filename("aux") == "_aux"


def test_path_formatter(tmp_path: Path) -> None:
    formatter = PathFormatter(base_dir=tmp_path)
    dest = formatter.format_destination(
        anime_title="Frieren: Beyond Journey's End",
        season=1,
        episode_num=1,
        episode_title="The Journey's End",
        extension="mkv",
    )
    # Check directory structure
    assert dest.parent.name == "Season 01"
    assert ":" not in str(dest) or str(dest)[1] == ":"  # only allow drive letter colon like D:
    assert dest.suffix == ".mkv"


@pytest.mark.asyncio
async def test_ffmpeg_service_real_synthetic_media(tmp_path: Path) -> None:
    service = FFmpegService()
    assert service.is_available() is True

    # Generate 1-second synthetic video using ffmpeg lavfi
    video_path = tmp_path / "synthetic.mp4"
    cmd = [
        str(service.ffmpeg_path),
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=1:size=320x240:rate=10",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    assert video_path.exists()

    # Inspect
    info = await service.inspect(video_path)
    assert "streams" in info
    assert len(info["streams"]) >= 1
    assert info["streams"][0]["codec_type"] == "video"

    # Duration & verification
    duration = await service.get_duration(video_path)
    assert duration is not None
    assert duration >= 0.5

    assert await service.verify(video_path) is True

    # Create dummy SRT subtitle
    srt_path = tmp_path / "sub.srt"
    srt_path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nHello Frieren!\n",
        encoding="utf-8",
    )

    mux_output = tmp_path / "muxed.mkv"
    sub_track = SubtitleTrack(
        language="eng",
        title="English",
        url=str(srt_path),
        format="srt",
    )

    result = await service.mux_subtitles(video_path, [sub_track], mux_output)
    assert result == mux_output
    assert mux_output.exists()

    # Original video preserved
    assert video_path.exists()

    # Verify muxed output contains subtitle stream
    mux_info = await service.inspect(mux_output)
    stream_types = [s["codec_type"] for s in mux_info["streams"]]
    assert "video" in stream_types
    assert "subtitle" in stream_types
