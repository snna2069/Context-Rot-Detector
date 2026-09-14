from __future__ import annotations

from app.analysis.semantic.detectors import SemanticInstructionDriftDetector
from app.models import MessageRole
from app.services.llm.types import InstructionDriftResult
from tests.analysis.helpers import make_context, make_message
from tests.llm.fake_provider import ScriptedAnalysisProvider, result


def test_flags_semantic_instruction_drift() -> None:
    instruction = "Always respond in formal English, never use slang."
    reply = "yo that's totally chill, no worries dude"
    provider = ScriptedAnalysisProvider(
        drift_by_pair={
            (instruction, reply): InstructionDriftResult(drifted=True, **result(0.8)),
        },
    )
    messages = [
        make_message(1, MessageRole.SYSTEM, instruction),
        make_message(2, MessageRole.ASSISTANT, reply),
    ]

    signals = SemanticInstructionDriftDetector(provider).detect(make_context(messages))

    assert len(signals) == 1
    assert signals[0].related_message_ids == (messages[0].id, messages[1].id)


def test_ignores_user_messages_as_instructions() -> None:
    instruction = "please only use formal English"
    reply = "yo"
    provider = ScriptedAnalysisProvider(
        drift_by_pair={
            (instruction, reply): InstructionDriftResult(drifted=True, **result(0.9)),
        },
    )
    messages = [
        make_message(1, MessageRole.USER, instruction),
        make_message(2, MessageRole.ASSISTANT, reply),
    ]

    signals = SemanticInstructionDriftDetector(provider).detect(make_context(messages))

    assert signals == []


def test_no_signal_when_not_drifted() -> None:
    instruction = "Always respond in formal English."
    reply = "Certainly, I would be happy to assist."
    provider = ScriptedAnalysisProvider(
        drift_by_pair={
            (instruction, reply): InstructionDriftResult(drifted=False, **result(0.9)),
        },
    )
    messages = [
        make_message(1, MessageRole.DEVELOPER, instruction),
        make_message(2, MessageRole.ASSISTANT, reply),
    ]

    signals = SemanticInstructionDriftDetector(provider).detect(make_context(messages))

    assert signals == []
