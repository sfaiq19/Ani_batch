from enum import StrEnum


class DownloadState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnimeStatus(StrEnum):
    FINISHED = "finished"
    RELEASING = "releasing"
    NOT_YET_RELEASED = "not_yet_released"
    CANCELLED = "cancelled"
    HIATUS = "hiatus"
    UNKNOWN = "unknown"
