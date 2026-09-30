"""Small, dependency-free text helpers shared by several detectors.

These are intentionally simple (regex tokenization, set overlap,
character-level similarity) rather than embedding-based, per the
"deterministic signals first" principle. Swapping in a semantic/embedding
similarity backend later is a natural upgrade and would only require
changing these functions, not the detectors that call them.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_WORD_RE = re.compile(r"[a-zA-Z0-9']+")

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "to",
        "of",
        "and",
        "or",
        "in",
        "on",
        "at",
        "for",
        "with",
        "that",
        "this",
        "it",
        "as",
        "by",
        "from",
        "i",
        "you",
        "we",
        "they",
        "he",
        "she",
        "will",
        "would",
        "can",
        "could",
        "should",
        "do",
        "does",
        "did",
        "not",
        "have",
        "has",
        "had",
        "but",
        "if",
        "so",
        "what",
        "which",
        "who",
        "your",
        "my",
        "our",
        "me",
        "let",
        "us",
        "im",
    }
)


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def content_words(text: str) -> set[str]:
    """Lowercased, stopword-free, length>2 word set used for topical overlap."""
    return {w for w in tokenize(text) if w not in _STOPWORDS and len(w) > 2}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def containment_ratio(subset: set[str], reference: set[str]) -> float:
    """Fraction of `subset` that already appears in `reference`.

    Unlike Jaccard this does not shrink as `reference` grows, which
    matters when comparing a fixed-size window against the accumulated
    vocabulary of a whole session: Jaccard's union denominator would make
    every long session look like it had drifted, purely because it is
    long.
    """
    if not subset:
        return 1.0
    if not reference:
        return 0.0
    return len(subset & reference) / len(subset)


def text_similarity_ratio(a: str, b: str) -> float:
    """Character-level similarity ratio (0..1) for near-duplicate detection."""
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def extract_numbers(text: str) -> list[float]:
    """Every number appearing in `text`, in order."""
    return [float(m) for m in _NUMBER_RE.findall(text)]


def numeric_conflict(a: str, b: str) -> bool | None:
    """Whether two values disagree numerically.

    Returns `None` when the comparison does not apply (either side has no
    number, or they contain different counts of numbers, so there is no
    sensible pairing).

    This exists because character similarity is actively misleading for
    numeric facts: "30 seconds" and "5 seconds" are 84% similar as
    strings, so a purely lexical comparison scores them as *agreeing*
    precisely when they contradict. The more consistent the phrasing
    around a changed number, the more lexical similarity hides the
    conflict -- exactly backwards for detecting contradictions.
    """
    numbers_a = extract_numbers(a)
    numbers_b = extract_numbers(b)
    if not numbers_a or not numbers_b or len(numbers_a) != len(numbers_b):
        return None
    return any(x != y for x, y in zip(numbers_a, numbers_b, strict=True))
