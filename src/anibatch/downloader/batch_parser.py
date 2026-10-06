import re

from anibatch.core.exceptions import AniBatchError


class BatchSyntaxError(AniBatchError):
    """Raised when an episode range or syntax is invalid."""


def parse_episode_selection(
    selection_str: str,
    total_episodes: int | None = None,
) -> list[int]:
    """Parse episode range expressions like '1', '1-12', '1,3,7', '1-4,8,12-15', 'all', 'latest'.

    Returns a sorted, deduplicated list of 1-based integer episode numbers.
    """
    clean_str = selection_str.strip().lower()
    if not clean_str:
        raise BatchSyntaxError("Episode selection string cannot be empty.")

    if clean_str == "all":
        if total_episodes is None or total_episodes <= 0:
            raise BatchSyntaxError("Cannot resolve 'all' without total_episodes.")
        return list(range(1, total_episodes + 1))

    if clean_str == "latest":
        if total_episodes is None or total_episodes <= 0:
            raise BatchSyntaxError("Cannot resolve 'latest' without total_episodes.")
        return [total_episodes]

    # Validate against illegal characters or double commas/dashes
    if (
        ",," in clean_str
        or "--" in clean_str
        or clean_str.startswith(",")
        or clean_str.endswith(",")
    ):
        raise BatchSyntaxError(f"Malformed episode selection syntax: '{selection_str}'.")

    parts = clean_str.split(",")
    episodes: set[int] = set()

    for part in parts:
        part = part.strip()
        if not part:
            raise BatchSyntaxError(f"Empty segment in episode selection: '{selection_str}'.")

        # Range pattern: e.g. "1-4"
        if "-" in part:
            range_match = re.match(r"^(\d+)-(\d+)$", part)
            if not range_match:
                raise BatchSyntaxError(f"Invalid range expression: '{part}'.")

            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= 0 or end <= 0:
                raise BatchSyntaxError(f"Episode numbers must be >= 1: '{part}'.")
            if start > end:
                raise BatchSyntaxError(f"Range start cannot exceed range end: '{part}'.")
            if total_episodes is not None and end > total_episodes:
                raise BatchSyntaxError(
                    f"Episode {end} exceeds total available episodes ({total_episodes})."
                )

            episodes.update(range(start, end + 1))
        else:
            # Single integer
            if not part.isdigit():
                raise BatchSyntaxError(f"Invalid episode number: '{part}'.")

            num = int(part)
            if num <= 0:
                raise BatchSyntaxError(f"Episode numbers must be >= 1: '{part}'.")
            if total_episodes is not None and num > total_episodes:
                raise BatchSyntaxError(
                    f"Episode {num} exceeds total available episodes ({total_episodes})."
                )

            episodes.add(num)

    return sorted(episodes)
