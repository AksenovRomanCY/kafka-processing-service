from __future__ import annotations


class TransientProcessingError(Exception):
    """Retryable transient error in task processing."""


class TaskFailedPermanentlyError(Exception):
    """Non-retryable permanent failure in task processing.

    Raised when a task encounters an error that cannot be resolved
    by retrying, such as invalid data or a business rule violation.
    """
