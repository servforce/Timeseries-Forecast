from __future__ import annotations

import asyncio
import logging
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class JobRecord:
    job_id: str
    kind: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    params: Dict[str, Any] = field(default_factory=dict)


class JobQueue:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[Tuple[str, Callable[..., Any], tuple, dict]] = asyncio.Queue()
        self.jobs: Dict[str, JobRecord] = {}

    def submit(self, kind: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> JobRecord:
        job_id = str(uuid.uuid4())
        record = JobRecord(
            job_id=job_id,
            kind=kind,
            status="queued",
            created_at=self._now_iso(),
            params=kwargs.get("params", {}),
        )
        self.jobs[job_id] = record
        self.queue.put_nowait((job_id, func, args, kwargs))
        return record

    def get(self, job_id: str) -> Optional[JobRecord]:
        return self.jobs.get(job_id)

    async def worker(self) -> None:
        while True:
            job_id, func, args, kwargs = await self.queue.get()
            record = self.jobs.get(job_id)
            if record is None:
                self.queue.task_done()
                continue
            record.status = "running"
            record.started_at = self._now_iso()
            try:
                result = await asyncio.to_thread(func, *args, **kwargs)
                record.status = "succeeded"
                record.result = result
            except Exception as exc:
                record.status = "failed"
                record.error = {
                    "message": str(exc),
                    "trace": traceback.format_exc(),
                }
                logger.warning("异步任务执行失败: job_id=%s, reason=%s", job_id, exc)
            finally:
                record.finished_at = self._now_iso()
                self.queue.task_done()

    @staticmethod
    def _now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


job_queue = JobQueue()


def job_record_to_dict(record: JobRecord) -> Dict[str, Any]:
    return {
        "job_id": record.job_id,
        "kind": record.kind,
        "status": record.status,
        "created_at": record.created_at,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "result": record.result,
        "error": record.error,
        "params": record.params,
    }
