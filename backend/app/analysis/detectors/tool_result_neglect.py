"""Tool-result neglect detector.

What it measures
-----------------
Whether a tool call's result is actually used by the assistant afterward:
either the result's content is not referenced by any assistant message
following it within a short window, or (for error results) the error is
never acknowledged.

Why it matters
-----------------
An unused tool result usually means either the agent forgot the result
existed (context rot), or it produced an answer that ignored ground truth
the system already had -- both worth surfacing. An unacknowledged tool
error is worth surfacing even more directly, since silently proceeding
after a failed tool call risks the agent fabricating what the tool would
have returned.

Required inputs
-----------------
Ordered messages with their tool calls and (optionally) tool results.

Limitations
-----------------
- "Referenced" is determined by lexical/token overlap between the tool
  result's serialized output and the following assistant message content;
  it cannot verify deeper semantic usage (e.g. the assistant may
  paraphrase the result entirely without token overlap).
- Only looks a fixed number of messages ahead for a reference before
  concluding the result was neglected.

False positives
-----------------
- A tool result that legitimately did not need to be repeated verbatim
  (e.g. it was only used to make an internal decision) may be flagged
  even though it was not neglected in any meaningful sense.

Confidence calculation
-----------------
0.5 for an unreferenced non-error result; 0.7 for an unacknowledged error
result (errors are more important to acknowledge, so higher confidence
that silence about them is a genuine issue).
"""

from __future__ import annotations

import json

from app.analysis.context import SessionContext, ToolCallView
from app.analysis.signals import Evidence, Signal
from app.analysis.text_utils import content_words, jaccard_similarity
from app.models import DetectionSeverity, DetectionType, MessageRole

LOOKAHEAD_MESSAGES = 3
REFERENCE_OVERLAP_THRESHOLD = 0.15
ERROR_ACK_KEYWORDS = (
    "error",
    "fail",
    "unable",
    "couldn't",
    "could not",
    "issue",
    "problem",
)
UNREFERENCED_CONFIDENCE = 0.5
UNACKNOWLEDGED_ERROR_CONFIDENCE = 0.7


class ToolResultNeglectDetector:
    name = "tool_result_neglect"

    def detect(self, context: SessionContext) -> list[Signal]:
        signals: list[Signal] = []
        messages = context.messages

        for i, message in enumerate(messages):
            for tool_call in message.tool_calls:
                if tool_call.result is None:
                    continue
                follow_up = messages[i + 1 : i + 1 + LOOKAHEAD_MESSAGES]
                assistant_follow_up = [
                    m for m in follow_up if m.role == MessageRole.ASSISTANT
                ]
                if not assistant_follow_up:
                    continue

                if tool_call.result.is_error:
                    acknowledged = any(
                        keyword in m.content.lower()
                        for m in assistant_follow_up
                        for keyword in ERROR_ACK_KEYWORDS
                    )
                    if not acknowledged:
                        signals.append(
                            self._signal(
                                tool_call,
                                message,
                                assistant_follow_up[0],
                                confidence=UNACKNOWLEDGED_ERROR_CONFIDENCE,
                                reason="error result was not acknowledged",
                            )
                        )
                    continue

                result_words = content_words(
                    json.dumps(tool_call.result.output, default=str)
                )
                if not result_words:
                    continue
                referenced = any(
                    jaccard_similarity(result_words, content_words(m.content))
                    >= REFERENCE_OVERLAP_THRESHOLD
                    for m in assistant_follow_up
                )
                if not referenced:
                    signals.append(
                        self._signal(
                            tool_call,
                            message,
                            assistant_follow_up[0],
                            confidence=UNREFERENCED_CONFIDENCE,
                            reason="result content was not referenced",
                        )
                    )
        return signals

    def _signal(
        self,
        tool_call: ToolCallView,
        calling_message,
        next_assistant_message,
        confidence: float,
        reason: str,
    ) -> Signal:
        return Signal(
            detector_name=self.name,
            detection_type=DetectionType.TOOL_RESULT_MISUSE,
            severity=DetectionSeverity.MEDIUM,
            confidence=confidence,
            explanation=(
                f"Tool '{tool_call.tool_name}' (called at sequence "
                f"{calling_message.sequence_number}) {reason} in the assistant's "
                f"following message at sequence "
                f"{next_assistant_message.sequence_number}."
            ),
            evidence=(
                Evidence(tool_call_id=tool_call.id, role="tool_call"),
                Evidence(tool_result_id=tool_call.result.id, role="tool_result"),
                Evidence(
                    message_id=next_assistant_message.id,
                    excerpt=next_assistant_message.content[:200],
                    role="follow_up",
                ),
            ),
            related_message_ids=(calling_message.id, next_assistant_message.id),
            metadata={"tool_name": tool_call.tool_name},
        )
