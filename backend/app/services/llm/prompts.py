"""Prompt construction for each semantic-analysis task.

Each function returns a `(system_prompt, user_prompt)` pair. Prompts are
deliberately narrow and single-purpose -- mirroring the `AnalysisProvider`
protocol -- rather than one general "analyze this" prompt, so each
response can be validated against a small, specific JSON schema.

None of these prompts ever ask "did the agent hallucinate?" or similar;
see `app.analysis.semantic.hallucination` for how the narrower answers
produced here are combined into a hallucination-risk classification.
"""

from __future__ import annotations

_JSON_ONLY_INSTRUCTION = (
    "Respond with a single JSON object only, no prose, no markdown code "
    "fences. Every field listed must be present."
)


def important_facts_prompt(text: str) -> tuple[str, str]:
    system = (
        "You extract atomic, checkable factual claims from a piece of "
        "text written by an AI assistant. Extract only concrete claims "
        "(e.g. dates, names, decisions, numeric values, statuses) -- skip "
        "greetings, hedges, and questions. "
        f"{_JSON_ONLY_INSTRUCTION} Schema: "
        '{"facts": [{"text": string, "source_excerpt": string}], '
        '"confidence": number (0-1), "explanation": string}'
    )
    user = f"Text:\n{text}"
    return system, user


def same_fact_prompt(statement_a: str, statement_b: str) -> tuple[str, str]:
    system = (
        "You determine whether two statements are about the same "
        "underlying fact or subject, regardless of phrasing (e.g. "
        "'the deadline' and 'the due date for the project' may be the "
        f"same subject). {_JSON_ONLY_INSTRUCTION} Schema: "
        '{"same": boolean, "confidence": number (0-1), '
        '"explanation": string}'
    )
    user = f"Statement A: {statement_a}\nStatement B: {statement_b}"
    return system, user


def semantic_contradiction_prompt(
    statement_a: str, statement_b: str
) -> tuple[str, str]:
    system = (
        "Two statements are known to be about the same fact. Determine "
        "whether they conflict with each other in meaning (not just "
        f"wording). {_JSON_ONLY_INSTRUCTION} Schema: "
        '{"is_contradiction": boolean, "confidence": number (0-1), '
        '"explanation": string}'
    )
    user = f"Statement A: {statement_a}\nStatement B: {statement_b}"
    return system, user


def instruction_drift_prompt(instruction: str, response: str) -> tuple[str, str]:
    system = (
        "Determine whether the response fails to follow the given "
        "instruction (ignores it, contradicts it, or only partially "
        f"honors it). {_JSON_ONLY_INSTRUCTION} Schema: "
        '{"drifted": boolean, "confidence": number (0-1), '
        '"explanation": string}'
    )
    user = f"Instruction: {instruction}\nResponse: {response}"
    return system, user


def relevance_prompt(task: str, response: str) -> tuple[str, str]:
    system = (
        "Determine whether the response is relevant to the current task "
        f"or request. {_JSON_ONLY_INSTRUCTION} Schema: "
        '{"is_relevant": boolean, "confidence": number (0-1), '
        '"explanation": string}'
    )
    user = f"Task/request: {task}\nResponse: {response}"
    return system, user


def claim_support_prompt(claim: str, evidence: tuple[str, ...]) -> tuple[str, str]:
    system = (
        "Classify a claim against a list of evidence snippets. Choose "
        "exactly one classification: 'supported' (evidence confirms the "
        "claim), 'contradicted' (evidence conflicts with the claim), "
        "'unsupported' (evidence exists but says nothing about this "
        "claim), or 'insufficient_evidence' (no relevant evidence was "
        "provided to judge the claim either way). Never answer with any "
        "other classification. "
        f"{_JSON_ONLY_INSTRUCTION} Schema: "
        '{"classification": string, "supporting_evidence_indexes": '
        '[integer], "confidence": number (0-1), "explanation": string}'
    )
    evidence_block = (
        "\n".join(f"[{i}] {snippet}" for i, snippet in enumerate(evidence))
        if evidence
        else "(none provided)"
    )
    user = f"Claim: {claim}\n\nEvidence:\n{evidence_block}"
    return system, user
