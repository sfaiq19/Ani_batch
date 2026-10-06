from pathlib import Path

import pytest

from anibatch.core.exceptions import DownloaderError
from anibatch.core.models import DownloadJob
from anibatch.downloader.backends.aria2 import Aria2Backend
from anibatch.downloader.backends.base import DownloadBackend


def test_aria2_backend_interface_and_properties() -> None:
    backend = Aria2Backend()
    assert isinstance(backend, DownloadBackend)
    assert backend.name == "aria2"


@pytest.mark.asyncio
async def test_aria2_backend_missing_binary(tmp_path: Path) -> None:
    job = DownloadJob(
        id="j-aria",
        anime_id="1",
        episode_id="e-1",
        provider="test",
        selected_quality="1080p",
        destination=tmp_path / "out.mp4",
        temporary_path=tmp_path / "out.mp4.part",
    )

    with pytest.raises(DownloaderError, match="aria2c binary not found"):
        backend_missing = Aria2Backend(aria2c_path=None)
        # Force is_available to False
        backend_missing.aria2c_path = None
        await backend_missing.download(job, "https://test.local/stream.mp4")


@pytest.mark.asyncio
async def test_aria2_cancel_no_op_when_inactive() -> None:
    backend = Aria2Backend()
    # Canceling non-existent job should not raise
    await backend.cancel("non-existent-job")
