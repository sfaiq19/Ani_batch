"""Core domain exceptions for AniBatch."""


class AniBatchError(Exception):
    """Base exception for all AniBatch errors."""


class ProviderError(AniBatchError):
    """Raised when a provider encounters a failure or error response."""


class DownloaderError(AniBatchError):
    """Raised when a download operation fails."""


class MetadataError(AniBatchError):
    """Raised when metadata lookup fails."""


class MediaProcessingError(AniBatchError):
    """Raised when FFmpeg or media validation fails."""
