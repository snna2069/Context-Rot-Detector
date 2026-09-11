"""Domain-level errors that the API layer maps to HTTP responses.

Keeping these separate from FastAPI/HTTP concerns lets services and
repositories raise meaningful, provider-agnostic errors without importing
web-framework types.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-level errors that map to HTTP responses."""


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist."""


class ConflictError(DomainError):
    """Raised when a request conflicts with existing state.

    Used for duplicate events and invalid/out-of-order sequence numbers.
    """


class SessionNotFoundError(NotFoundError):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' was not found.")


class MessageNotFoundError(NotFoundError):
    def __init__(self, message_id: str) -> None:
        self.message_id = message_id
        super().__init__(f"Message '{message_id}' was not found.")


class ToolCallNotFoundError(NotFoundError):
    def __init__(self, tool_call_id: str) -> None:
        self.tool_call_id = tool_call_id
        super().__init__(f"Tool call '{tool_call_id}' was not found.")


class DuplicateMessageError(ConflictError):
    def __init__(self, provider_message_id: str) -> None:
        self.provider_message_id = provider_message_id
        super().__init__(
            f"A message with provider_message_id '{provider_message_id}' "
            "already exists in this session."
        )


class InvalidMessageSequenceError(ConflictError):
    def __init__(self, session_id: str, attempted: int, last_sequence: int) -> None:
        self.session_id = session_id
        self.attempted = attempted
        self.last_sequence = last_sequence
        super().__init__(
            f"sequence_number {attempted} is not greater than the last recorded "
            f"sequence_number {last_sequence} for session '{session_id}'."
        )


class DuplicateToolCallIndexError(ConflictError):
    def __init__(self, message_id: str, call_index: int) -> None:
        self.message_id = message_id
        self.call_index = call_index
        super().__init__(
            f"A tool call with call_index {call_index} already exists for "
            f"message '{message_id}'."
        )


class DuplicateToolResultError(ConflictError):
    def __init__(self, tool_call_id: str) -> None:
        self.tool_call_id = tool_call_id
        super().__init__(
            f"A tool result already exists for tool call '{tool_call_id}'."
        )
