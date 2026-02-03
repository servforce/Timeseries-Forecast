"""
API 路由聚合

对外接口（与 CDD 对齐）：
- POST /zeroshot
- POST /finetune
"""

from fastapi import APIRouter

from app.api.routes import finetune_forecast, zero_shot_forecast, jobs

api_router = APIRouter()

api_router.include_router(zero_shot_forecast.router, prefix="/zeroshot")
api_router.include_router(finetune_forecast.router, prefix="/finetune")
api_router.include_router(jobs.router, prefix="/jobs")
