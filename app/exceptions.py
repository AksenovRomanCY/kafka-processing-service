from __future__ import annotations


class TransientProcessingError(Exception):
    """Retryable transient error in task processing."""
