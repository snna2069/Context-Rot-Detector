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


def text_similarity_ratio(a: str, b: str) -> float:
    """Character-level similarity ratio (0..1) for near-duplicate detection."""
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()
