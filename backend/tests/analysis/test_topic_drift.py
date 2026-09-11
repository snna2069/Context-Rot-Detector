from __future__ import annotations

from app.analysis.detectors.topic_drift import TopicDriftDetector
from app.models import MessageRole
from tests.analysis.helpers import make_context, make_message


def test_topic_drift_detects_sharp_vocabulary_change() -> None:
    weather_words = (
        "weather forecast temperature rain sunshine humidity wind clouds storm degrees"
    ).split()
    cooking_words = (
        "recipe pasta garlic tomato basil olive oil simmer saute skillet"
    ).split()

    messages = [
        make_message(i, MessageRole.USER, " ".join(weather_words)) for i in range(1, 5)
    ] + [
        make_message(i, MessageRole.USER, " ".join(cooking_words)) for i in range(5, 9)
    ]
    context = make_context(messages)

    signals = TopicDriftDetector().detect(context)

    assert len(signals) == 1
    assert signals[0].confidence > 0.8


def test_topic_drift_no_signal_for_consistent_topic() -> None:
    words = "weather forecast temperature rain sunshine humidity wind clouds".split()
    messages = [make_message(i, MessageRole.USER, " ".join(words)) for i in range(1, 9)]
    context = make_context(messages)

    signals = TopicDriftDetector().detect(context)

    assert signals == []


def test_topic_drift_no_signal_for_short_session() -> None:
    messages = [make_message(1, MessageRole.USER, "hello there, how are you?")]
    context = make_context(messages)

    signals = TopicDriftDetector().detect(context)

    assert signals == []
