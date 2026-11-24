from fastapi import APIRouter, Request

from app.services.analytics_service import AnalyticsResponse


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse, summary="Summarize imported static schedules")
def analytics(request: Request) -> AnalyticsResponse:
    return request.app.state.analytics.get()
