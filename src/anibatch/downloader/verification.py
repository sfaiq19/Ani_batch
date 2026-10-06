import hashlib
from pathlib import Path

from anibatch.core.exceptions import DownloaderError


def calculate_checksum(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute sha256 checksum of a file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()


def verify_downloaded_file(
    file_path: Path,
    expected_size: int | None = None,
    expected_checksum: str | None = None,
) -> bool:
    """Verify that a downloaded file is non-empty and matches size/checksum if specified."""
    if not file_path.exists():
        raise DownloaderError(f"File {file_path} does not exist.")

    actual_size = file_path.stat().st_size
    if actual_size == 0:
        raise DownloaderError(f"Downloaded file {file_path} is empty (0 bytes).")

    if expected_size is not None and expected_size > 0 and actual_size != expected_size:
        raise DownloaderError(
            f"Size mismatch for {file_path}: expected {expected_size} bytes, got {actual_size} bytes."
        )

    if expected_checksum:
        actual_checksum = calculate_checksum(file_path)
        if actual_checksum.lower() != expected_checksum.lower():
            raise DownloaderError(
                f"Checksum mismatch for {file_path}: expected {expected_checksum}, got {actual_checksum}."
            )

    return True
