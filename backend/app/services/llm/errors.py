"""Errors raised by LLM/semantic-analysis providers.

Kept separate from `app.errors` (API/domain errors) since these are an
internal implementation detail of the analysis pipeline: a provider
failure should never crash a whole analysis run (the engine already
catches and logs any detector exception) -- it should just mean that
particular semantic signal could not be computed this time.
"""

from __future__ import annotations


class LLMProviderError(Exception):
    """Raised when a provider cannot produce a usable result.

    Covers network failures, non-2xx responses, and responses that do not
    parse into the expected structured schema. Callers must treat this as
    "no answer available", never as evidence of anything about the claim
    being evaluated.
    """
