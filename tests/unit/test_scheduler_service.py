from datetime import UTC, datetime, timedelta

from xbot.interfaces.storage import JobRepository
from xbot.models import JobStatus, ScheduledJob
from xbot.services.scheduling import SchedulerService


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self._store: dict[str, ScheduledJob] = {}

    def enqueue(self, job: ScheduledJob) -> None:
        self._store[job.job_id] = job

    def get(self, job_id: str) -> ScheduledJob | None:
        return self._store.get(job_id)

    def list_pending(self):
        return list(self._store.values())

    def update(self, job: ScheduledJob) -> None:
        self._store[job.job_id] = job


def test_scheduler_executes_job():
    repo = InMemoryJobRepository()
    service = SchedulerService(repository=repo)
    executed: list[str] = []

    def handler(job: ScheduledJob) -> None:
        executed.append(job.job_id)

    service.register_handler("test", handler)
    job = service.enqueue("test")
    results = service.run_pending()

    assert executed == [job.job_id]
    assert results[0].success is True
    assert repo.get(job.job_id).status is JobStatus.COMPLETED


def test_scheduler_records_failure():
    repo = InMemoryJobRepository()
    service = SchedulerService(repository=repo)

    def handler(_job: ScheduledJob) -> None:
        raise RuntimeError("boom")

    service.register_handler("fail", handler)
    job = service.enqueue("fail")
    results = service.run_pending()

    assert results[0].success is False
    assert results[0].error == "boom"
    assert repo.get(job.job_id).status is JobStatus.FAILED


def test_scheduler_respects_run_at():
    repo = InMemoryJobRepository()
    service = SchedulerService(repository=repo)
    executed: list[str] = []

    service.register_handler("future", lambda job: executed.append(job.job_id))
    future = datetime.now(tz=UTC) + timedelta(hours=1)
    service.enqueue("future", run_at=future)

    assert service.run_pending(now=datetime.now(tz=UTC)) == ()
    assert executed == []
