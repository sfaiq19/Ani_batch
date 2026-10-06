import asyncio
from pathlib import Path

import httpx

from anibatch.core.exceptions import DownloaderError
from anibatch.core.models import DownloadJob
from anibatch.downloader.backends.base import DownloadBackend, ProgressCallback
from anibatch.downloader.verification import verify_downloaded_file


class HttpxBackend(DownloadBackend):
    """Native asynchronous HTTP download engine using HTTPX streaming and range-resumes."""

    name = "native"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._owns_client = client is None
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=60.0))
        return self._client

    async def close(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def download(
        self,
        job: DownloadJob,
        stream_url: str,
        on_progress: ProgressCallback | None = None,
    ) -> Path:
        """Stream media to job.temporary_path with resume support and finalize atomically."""
        client = await self._get_client()

        part_path = job.temporary_path
        dest_path = job.destination
        part_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        existing_bytes = part_path.stat().st_size if part_path.exists() else 0

        headers = {}
        if existing_bytes > 0:
            headers["Range"] = f"bytes={existing_bytes}-"

        try:
            async with client.stream("GET", stream_url, headers=headers) as response:
                if response.status_code == 416:  # Range Not Satisfiable (already fully downloaded)
                    pass
                else:
                    response.raise_for_status()

                is_resume = response.status_code == 206
                mode = "ab" if is_resume else "wb"
                downloaded = existing_bytes if is_resume else 0

                content_len = response.headers.get("Content-Length")
                if content_len:
                    total_bytes = downloaded + int(content_len)
                else:
                    total_bytes = job.bytes_total or 0

                job.bytes_total = total_bytes

                with open(part_path, mode) as f:  # noqa: ASYNC230
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded += len(chunk)
                        job.bytes_downloaded = downloaded
                        if on_progress:
                            on_progress(downloaded, total_bytes)
                    f.flush()

        except httpx.HTTPError as exc:
            raise DownloaderError(f"HTTP stream error for {stream_url}: {exc}") from exc

        # Verification step
        verify_downloaded_file(
            part_path, expected_size=job.bytes_total if job.bytes_total > 0 else None
        )

        # Atomic finalization
        if dest_path.exists():
            dest_path.unlink()
        part_path.replace(dest_path)

        return dest_path

    async def cancel(self, job_id: str) -> None:
        """Cancel an ongoing download task."""
        if job_id in self._active_tasks:
            self._active_tasks[job_id].cancel()
