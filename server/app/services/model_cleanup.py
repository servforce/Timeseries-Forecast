import logging
import shutil
import time
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def cleanup_finetuned_models(retention_days: int | None = None) -> None:
    if retention_days is None:
        retention_days = settings.FINETUNED_MODEL_RETENTION_DAYS
    if retention_days <= 0:
        return
    base_dir = Path(settings.FINETUNED_MODELS_DIR)
    if not base_dir.exists():
        return
    cutoff = time.time() - (retention_days * 24 * 60 * 60)
    for entry in base_dir.iterdir():
        if not entry.is_dir():
            continue
        try:
            mtime = entry.stat().st_mtime
        except Exception as exc:
            logger.warning("读取模型目录时间失败: %s, reason=%s", entry, exc)
            continue
        if mtime < cutoff:
            try:
                shutil.rmtree(entry, ignore_errors=True)
                logger.info("已清理过期模型目录: %s", entry)
            except Exception as exc:
                logger.warning("清理过期模型失败: %s, reason=%s", entry, exc)
