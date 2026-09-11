"""Shared validation helpers for ingestion request schemas.

Payload size limits exist so a single malformed or hostile event cannot
store an unbounded blob in PostgreSQL. Limits are generous enough for real
agent transcripts but bounded enough to reject clearly oversized input at
the validation layer instead of at the database.
"""

from __future__ import annotations

import json
from typing import Any

MAX_TEXT_CONTENT_LENGTH = 50_000
MAX_METADATA_BYTES = 20_000
MAX_TOOL_ARGUMENTS_BYTES = 20_000
MAX_TOOL_OUTPUT_BYTES = 40_000


def ensure_json_payload_within_limit(
    value: dict[str, Any], max_bytes: int, field_name: str
) -> dict[str, Any]:
    serialized_size = len(json.dumps(value).encode("utf-8"))
    if serialized_size > max_bytes:
        raise ValueError(
            f"{field_name} payload of {serialized_size} bytes exceeds the "
            f"{max_bytes} byte limit"
        )
    return value
