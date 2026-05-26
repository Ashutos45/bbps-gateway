from fastapi import APIRouter

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
