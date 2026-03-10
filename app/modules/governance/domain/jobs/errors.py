"""Shared job execution error types."""

from __future__ import annotations


class JobExecutionError(RuntimeError):
    """Base class for job execution failures that should be recorded on the job."""


class PermanentJobError(JobExecutionError):
    """Raised when a job should go straight to dead letter without retry."""
