"""
Wundio – /api/feedback routes
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.feedback import get_feedback_bus

router = APIRouter(tags=["feedback"])


@router.get("/stream")
async def feedback_stream():
    """
    SSE endpoint – clients connect once and receive all device feedback events.
    Reconnects automatically on disconnect (browser EventSource handles this).
    """
    return StreamingResponse(
        get_feedback_bus().stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )