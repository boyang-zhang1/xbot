"""Lightweight in-memory scheduling built on the JSON job repository."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Dict, List, Sequence
from uuid import uuid4

from xbot.config.settings import Settings, get_settings
from xbot.interfaces.storage import JobRepository
from xbot.models import JobStatus, ScheduledJob

try:  # pragma: no cover - optional dependency
    import structlog
except ImportError:  # pragma: no cover
    structlog = None  # type: ignore[assignment]


@dataclass(frozen=True)
class JobExecution:
    job: ScheduledJob
    success: bool
    error: str | None = None


class SchedulerService:
    """Coordinates scheduled job execution with pluggable handlers."""

    def __init__(
        self,
        repository: JobRepository,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings or get_settings()
        self._handlers: Dict[str, Callable[[ScheduledJob], None]] = {}
        if structlog is not None:
            self._logger = structlog.get_logger(__name__)
        else:
            self._logger = logging.getLogger(__name__)

    def register_handler(self, name: str, handler: Callable[[ScheduledJob], None]) -> None:
        """Register a callable to execute jobs with the given *name*."""

        self._handlers[name] = handler

    def enqueue(
        self,
        name: str,
        *,
        payload: dict | None = None,
        run_at: datetime | None = None,
    ) -> ScheduledJob:
        if name not in self._handlers:
            raise ValueError(f"No handler registered for job '{name}'")
        payload = payload or {}
        run_at = run_at or datetime.now(tz=UTC)
        job = ScheduledJob(job_id=str(uuid4()), name=name, payload=payload, run_at=run_at)
        self._repository.enqueue(job)
        self._log("info", "scheduler.job_enqueued", job_id=job.job_id, name=name)
        return job

    def run_pending(self, *, now: datetime | None = None) -> Sequence[JobExecution]:
        """Execute all jobs whose ``run_at`` is due."""

        now = now or datetime.now(tz=UTC)
        pending = self._due_jobs(now)
        results: List[JobExecution] = []
        for job in pending:
            handler = self._handlers.get(job.name)
            if handler is None:
                self._log("error", "scheduler.missing_handler", job_id=job.job_id, name=job.name)
                updated = job.mark_failed("Handler not registered")
                self._repository.update(updated)
                results.append(JobExecution(job=updated, success=False, error=updated.last_error))
                continue
            running = job.mark_running()
            self._repository.update(running)
            try:
                handler(running)
            except Exception as exc:  # pragma: no cover - defensive
                failed = running.mark_failed(str(exc))
                self._repository.update(failed)
                self._log(
                    "error",
                    "scheduler.job_failed",
                    job_id=job.job_id,
                    name=job.name,
                    error=str(exc),
                )
                results.append(JobExecution(job=failed, success=False, error=str(exc)))
            else:
                completed = running.mark_completed()
                self._repository.update(completed)
                self._log(
                    "info",
                    "scheduler.job_completed",
                    job_id=job.job_id,
                    name=job.name,
                )
                results.append(JobExecution(job=completed, success=True))
        return tuple(results)

    def _due_jobs(self, now: datetime) -> List[ScheduledJob]:
        due: List[ScheduledJob] = []
        for job in self._repository.list_pending():
            if job.status not in {JobStatus.PENDING, JobStatus.FAILED}:
                continue
            if job.run_at <= now:
                due.append(job)
        due.sort(key=lambda job: job.run_at)
        return due

    def _log(self, level: str, event: str, **kwargs) -> None:
        if structlog is not None:
            getattr(self._logger, level)(event, **kwargs)
            return
        message = "{} | {}".format(
            event,
            ", ".join(f"{key}={value}" for key, value in kwargs.items()),
        )
        getattr(self._logger, level)(message)


__all__ = ["SchedulerService", "JobExecution"]
