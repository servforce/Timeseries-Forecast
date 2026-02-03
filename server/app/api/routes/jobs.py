import logging
from typing import Any, Dict

from fastapi import APIRouter, status

from app.core.exceptions import DataException, ErrorCode
from app.services.job_queue import job_queue, job_record_to_dict

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Jobs"])


@router.get("/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    record = job_queue.get(job_id)
    if record is None:
        raise DataException(
            error_code=ErrorCode.NOT_FOUND,
            message="未找到对应的任务",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"job_id": job_id},
        )
    return job_record_to_dict(record)
