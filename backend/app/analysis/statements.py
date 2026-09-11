"""Shared lightweight statement extraction used by several detectors.

This is a narrow, regex-based heuristic used by the contradiction,
stale-context, and fact-loss detectors, all of which need to identify
simple "<subject> is/are/was/were <value>" declarative statements. It is
NOT a natural-language-understanding component: it has no coreference
resolution, no synonym handling, and only recognizes a small set of
English copular sentence patterns. Its purpose is to provide a cheap,
reproducible, and fully deterministic signal -- callers must not treat its
extractions as confirmed facts, only as candidate statements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_STATEMENT_PATTERN = re.compile(
    r"\b(?:the\s+)?(?P<subject>[a-z][a-z0-9 _\-]{2,40}?)\s+"
    r"(?:is|are|was|were)\s+"
    r"(?P<value>[a-z0-9][\w .,'\-:/]{1,80}?)(?:[.!,;]|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedStatement:
    subject: str
    value: str


def extract_statements(content: str) -> list[ExtractedStatement]:
    statements = []
    for match in _STATEMENT_PATTERN.finditer(content):
        subject = match.group("subject").strip().lower()
        value = match.group("value").strip().lower()
        if subject and value:
            statements.append(ExtractedStatement(subject=subject, value=value))
    return statements
