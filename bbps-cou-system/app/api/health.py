from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check():
    """
    API Health Check Endpoint.
    Returns status and confirmation that the BBPS COU System is operational.
    """
    return {
        "status": "success",
        "message": "BBPS COU System Running"
    }
