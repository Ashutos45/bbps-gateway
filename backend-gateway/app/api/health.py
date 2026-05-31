from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check():
    """
    API Health Check.
    Confirms the BBPS NextGen Gateway system is online and accepting connections.
    """
    return {
        "status": "success",
        "message": "BBPS COU System Running"
    }

@router.get("/heartbeat", tags=["Health"])
async def heartbeat_check():
    """
    Heartbeat service confirming the BBPS Gateway is alive.
    No authentication required.
    """
    return {
        "status": "alive",
        "service": "BBPS Gateway",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

