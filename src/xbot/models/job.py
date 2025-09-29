"""Domain models representing scheduled jobs."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict

from pydantic import Field

from .base import ModelBase


class JobStatus(str, Enum):
    """Execution state of a scheduled job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScheduledJob(ModelBase):
    """Representation of a queued job awaiting execution."""

    job_id: str
    name: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    run_at: datetime
    status: JobStatus = Field(default=JobStatus.PENDING)
    last_error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def mark_running(self) -> "ScheduledJob":
        return self._with_status(JobStatus.RUNNING)

    def mark_completed(self) -> "ScheduledJob":
        return self._with_status(JobStatus.COMPLETED, clear_error=True)

    def mark_failed(self, error: str) -> "ScheduledJob":
        return self._with_status(JobStatus.FAILED, error=error)

    def _with_status(
        self,
        status: JobStatus,
        *,
        error: str | None = None,
        clear_error: bool = False,
    ) -> "ScheduledJob":
        updated = {
            "status": status,
            "updated_at": datetime.now(tz=timezone.utc),
        }
        if clear_error:
            updated["last_error"] = None
        if error is not None:
            updated["last_error"] = error
        return self.model_copy(update=updated)


__all__ = ["ScheduledJob", "JobStatus"]
