import re

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

ILLEGAL_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(filename: str, replacement: str = "-") -> str:
    """Sanitize a filename for Windows and POSIX filesystems."""
    # Replace illegal characters
    cleaned = ILLEGAL_CHARS_PATTERN.sub(replacement, filename)

    # Strip trailing spaces and dots (invalid on Windows)
    cleaned = cleaned.strip(". ")

    if not cleaned:
        cleaned = "unnamed"

    # Check Windows reserved file names
    base = cleaned.split(".")[0].upper()
    if base in WINDOWS_RESERVED_NAMES:
        cleaned = f"_{cleaned}"

    return cleaned
