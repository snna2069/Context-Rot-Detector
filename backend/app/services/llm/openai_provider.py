"""A real `AnalysisProvider` backed by an OpenAI-compatible endpoint.

Uses `httpx` directly (already a project dependency, pulled in via
FastAPI's `TestClient`) instead of adding a vendor SDK, since only one
HTTP request shape (`POST /chat/completions` with JSON-object output) is
needed. This means the same code works against OpenAI, Azure OpenAI, or
any self-hosted server implementing the same API -- satisfying the
project rule that the app must not depend on one LLM provider throughout
the codebase.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from app.services.llm.errors import LLMProviderError
from app.services.llm.prompts import (
    claim_support_prompt,
    important_facts_prompt,
    instruction_drift_prompt,
    relevance_prompt,
    same_fact_prompt,
    semantic_contradiction_prompt,
)
from app.services.llm.types import (
    PROVIDER_ASSESSABLE_CLASSIFICATIONS,
    ClaimSupportResult,
    EvidenceClassification,
    ExtractedFact,
    ImportantFactsResult,
    InstructionDriftResult,
    RelevanceResult,
    SameFactResult,
    SemanticContradictionResult,
)

PROVIDER_NAME = "openai_compatible"


class OpenAIAnalysisProvider:
    """Calls a single OpenAI-compatible `/chat/completions` endpoint.

    Every method sends one narrow, task-specific prompt (see
    `app.services.llm.prompts`) and validates the JSON response into the
    matching result dataclass. Any network failure or unparsable response
    raises `LLMProviderError`, which the semantic detectors treat as "no
    signal this run" rather than crashing the analysis.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 20.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.25,
        max_calls: int = 24,
        client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._max_retries = max(0, max_retries)
        self._retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self._max_calls = max(1, max_calls)
        self._calls_made = 0
        self._client = client or httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def close(self) -> None:
        self._client.close()

    # -- AnalysisProvider protocol ---------------------------------------

    def extract_important_facts(self, text: str) -> ImportantFactsResult:
        system, user = important_facts_prompt(text)
        data = self._complete_json(system, user)
        facts = tuple(
            ExtractedFact(
                text=str(f.get("text", "")).strip(),
                source_excerpt=f.get("source_excerpt"),
            )
            for f in data.get("facts", []) or []
            if str(f.get("text", "")).strip()
        )
        return ImportantFactsResult(
            confidence=_as_confidence(data.get("confidence")),
            explanation=_as_explanation(data),
            provider=PROVIDER_NAME,
            model=self._model,
            facts=facts,
        )

    def same_fact(self, statement_a: str, statement_b: str) -> SameFactResult:
        system, user = same_fact_prompt(statement_a, statement_b)
        data = self._complete_json(system, user)
        return SameFactResult(
            confidence=_as_confidence(data.get("confidence")),
            explanation=_as_explanation(data),
            provider=PROVIDER_NAME,
            model=self._model,
            same=bool(data.get("same", False)),
        )

    def detect_semantic_contradiction(
        self, statement_a: str, statement_b: str
    ) -> SemanticContradictionResult:
        system, user = semantic_contradiction_prompt(statement_a, statement_b)
        data = self._complete_json(system, user)
        return SemanticContradictionResult(
            confidence=_as_confidence(data.get("confidence")),
            explanation=_as_explanation(data),
            provider=PROVIDER_NAME,
            model=self._model,
            is_contradiction=bool(data.get("is_contradiction", False)),
        )

    def detect_instruction_drift(
        self, instruction: str, response: str
    ) -> InstructionDriftResult:
        system, user = instruction_drift_prompt(instruction, response)
        data = self._complete_json(system, user)
        return InstructionDriftResult(
            confidence=_as_confidence(data.get("confidence")),
            explanation=_as_explanation(data),
            provider=PROVIDER_NAME,
            model=self._model,
            drifted=bool(data.get("drifted", False)),
        )

    def assess_relevance(self, task: str, response: str) -> RelevanceResult:
        system, user = relevance_prompt(task, response)
        data = self._complete_json(system, user)
        return RelevanceResult(
            confidence=_as_confidence(data.get("confidence")),
            explanation=_as_explanation(data),
            provider=PROVIDER_NAME,
            model=self._model,
            is_relevant=bool(data.get("is_relevant", True)),
        )

    def assess_claim_support(
        self, claim: str, evidence: tuple[str, ...]
    ) -> ClaimSupportResult:
        system, user = claim_support_prompt(claim, evidence)
        data = self._complete_json(system, user)
        classification = _as_provider_classification(data.get("classification"))
        indexes = data.get("supporting_evidence_indexes") or []
        refs = tuple(
            evidence[i]
            for i in indexes
            if isinstance(i, int) and 0 <= i < len(evidence)
        )
        return ClaimSupportResult(
            confidence=_as_confidence(data.get("confidence")),
            explanation=_as_explanation(data),
            provider=PROVIDER_NAME,
            model=self._model,
            classification=classification,
            supporting_evidence_refs=refs,
        )

    # -- internals --------------------------------------------------------

    def _complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if self._calls_made >= self._max_calls:
            raise LLMProviderError(
                "LLM analysis call budget exhausted for this analysis run"
            )
        self._calls_made += 1

        request_body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        response: httpx.Response | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.post("/chat/completions", json=request_body)
            except httpx.TimeoutException as exc:
                if attempt >= self._max_retries:
                    raise LLMProviderError(
                        "LLM provider request timed out after retries"
                    ) from exc
            except httpx.HTTPError as exc:
                if attempt >= self._max_retries:
                    raise LLMProviderError(
                        "LLM provider request failed after retries"
                    ) from exc
            else:
                if response.status_code < 400:
                    break
                if (
                    response.status_code not in {408, 409, 429}
                    and response.status_code < 500
                ) or attempt >= self._max_retries:
                    raise LLMProviderError(
                        f"LLM provider returned status {response.status_code}"
                    )
            time.sleep(self._retry_backoff_seconds * (2**attempt))

        if response is None or response.status_code >= 400:
            raise LLMProviderError("LLM provider did not return a usable response")

        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise LLMProviderError(
                f"could not parse LLM provider response: {exc}"
            ) from exc


def _as_confidence(value: object) -> float:
    try:
        confidence = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _as_explanation(data: dict[str, Any]) -> str:
    explanation = data.get("explanation")
    return str(explanation) if explanation else "(no explanation provided)"


def _as_provider_classification(value: object) -> EvidenceClassification:
    try:
        classification = EvidenceClassification(str(value))
    except ValueError:
        return EvidenceClassification.INSUFFICIENT_EVIDENCE
    if classification not in PROVIDER_ASSESSABLE_CLASSIFICATIONS:
        # Defensive: even if the model ignores instructions and returns a
        # hallucination-risk label directly, refuse to pass it through.
        return EvidenceClassification.INSUFFICIENT_EVIDENCE
    return classification
