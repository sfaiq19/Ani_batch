import re
from difflib import SequenceMatcher

from anibatch.core.models import Anime


def normalize_title(title: str) -> str:
    """Normalize anime title for fuzzy matching."""
    text = title.lower()
    # Normalize season keywords
    text = re.sub(r"\b(season\s*\d+|s\d+|\d+(?:st|nd|rd|th)\s*season)\b", "", text)
    # Remove symbols and punctuation
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse multiple whitespaces
    return " ".join(text.split())


def title_similarity(t1: str, t2: str) -> float:
    """Calculate normalized token-based sequence similarity between two titles."""
    norm1 = normalize_title(t1)
    norm2 = normalize_title(t2)
    if not norm1 or not norm2:
        return 0.0
    if norm1 == norm2:
        return 1.0

    seq_score = SequenceMatcher(None, norm1, norm2).ratio()

    # Token overlap score
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    if tokens1 and tokens2:
        overlap = len(tokens1 & tokens2) / max(len(tokens1), len(tokens2))
        return 0.6 * seq_score + 0.4 * overlap

    return seq_score


def score_candidate(
    query_title: str,
    candidate: Anime,
    year: int | None = None,
    episode_count: int | None = None,
) -> float:
    """Score a candidate Anime against query title, optional year, and episode count."""
    candidate_titles = [candidate.title]
    if candidate.english_title:
        candidate_titles.append(candidate.english_title)
    if candidate.romaji_title:
        candidate_titles.append(candidate.romaji_title)
    candidate_titles.extend(candidate.aliases)

    max_title_sim = max((title_similarity(query_title, ct) for ct in candidate_titles), default=0.0)

    score = max_title_sim

    # Year evaluation
    if year is not None and candidate.year is not None:
        if candidate.year == year:
            score += 0.1
        elif abs(candidate.year - year) == 1:
            score += 0.02
        else:
            score -= 0.15

    # Episode count evaluation
    if episode_count is not None and candidate.episode_count is not None:
        if candidate.episode_count == episode_count:
            score += 0.05
        else:
            score -= 0.05

    return max(0.0, min(1.0, score))


def find_best_match(
    query_title: str,
    candidates: list[Anime],
    threshold: float = 0.75,
    year: int | None = None,
    episode_count: int | None = None,
) -> tuple[Anime | None, float]:
    """Return the highest scoring Anime candidate above threshold, or None."""
    if not candidates:
        return None, 0.0

    scored = [
        (c, score_candidate(query_title, c, year=year, episode_count=episode_count))
        for c in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    best_candidate, best_score = scored[0]
    if best_score >= threshold:
        return best_candidate, round(best_score, 2)
    return None, round(best_score, 2)
