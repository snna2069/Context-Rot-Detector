from __future__ import annotations

from app.analysis.detectors.tool_result_neglect import ToolResultNeglectDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message, make_tool_call


def test_tool_result_neglect_flags_unreferenced_result() -> None:
    tool_call = make_tool_call(
        message_id="m1",
        tool_name="get_weather",
        result_output={"temp": 72, "condition": "sunny"},
    )
    messages = [
        make_message(
            1,
            MessageRole.ASSISTANT,
            "Let me check the weather.",
            tool_calls=(tool_call,),
        ),
        make_message(2, MessageRole.ASSISTANT, "Anyway, let's continue with the plan."),
    ]
    context = make_context(messages)

    signals = ToolResultNeglectDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence == 0.5


def test_tool_result_neglect_no_signal_when_result_referenced() -> None:
    tool_call = make_tool_call(
        message_id="m1",
        tool_name="get_weather",
        result_output={"temp": 72, "condition": "sunny"},
    )
    messages = [
        make_message(
            1,
            MessageRole.ASSISTANT,
            "Let me check the weather.",
            tool_calls=(tool_call,),
        ),
        make_message(
            2,
            MessageRole.ASSISTANT,
            "The temp is 72 and the condition is sunny.",
        ),
    ]
    context = make_context(messages)

    signals = ToolResultNeglectDetector().detect(context)

    assert signals == []


def test_tool_result_neglect_flags_unacknowledged_error() -> None:
    tool_call = make_tool_call(
        message_id="m1",
        tool_name="get_weather",
        result_output={},
        result_is_error=True,
    )
    messages = [
        make_message(
            1,
            MessageRole.ASSISTANT,
            "Let me check the weather.",
            tool_calls=(tool_call,),
        ),
        make_message(
            2, MessageRole.ASSISTANT, "It's a beautiful sunny day, 72 degrees."
        ),
    ]
    context = make_context(messages)

    signals = ToolResultNeglectDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence == 0.7


def test_tool_result_neglect_no_signal_when_error_acknowledged() -> None:
    tool_call = make_tool_call(
        message_id="m1",
        tool_name="get_weather",
        result_output={},
        result_is_error=True,
    )
    messages = [
        make_message(
            1,
            MessageRole.ASSISTANT,
            "Let me check the weather.",
            tool_calls=(tool_call,),
        ),
        make_message(
            2,
            MessageRole.ASSISTANT,
            "I wasn't able to retrieve the weather due to an error.",
        ),
    ]
    context = make_context(messages)

    signals = ToolResultNeglectDetector().detect(context)

    assert signals == []


def test_tool_result_neglect_ignores_calls_without_follow_up() -> None:
    tool_call = make_tool_call(
        message_id="m1",
        tool_name="get_weather",
        result_output={"temp": 72},
    )
    messages = [
        make_message(
            1,
            MessageRole.ASSISTANT,
            "Let me check the weather.",
            tool_calls=(tool_call,),
        ),
    ]
    context = make_context(messages)

    signals = ToolResultNeglectDetector().detect(context)

    assert signals == []
