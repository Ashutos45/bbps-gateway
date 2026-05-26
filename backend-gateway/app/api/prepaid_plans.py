from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Dict, Optional
from pydantic import BaseModel, Field
from app.database.db import get_db
from app.services.prepaid_service import PrepaidService
from app.auth.auth_middleware import require_roles
from app.auth.role_manager import Role
from loguru import logger

router = APIRouter()

class PrepaidPlansRequest(BaseModel):
    operator: str = Field(..., description="Telecom Operator Name")
    circle: str = Field(..., description="Telecom Circle Name")
    plan_category_name: Optional[str] = Field("Unlimited", description="Plan Category")

    model_config = {
        "json_schema_extra": {
            "example": {
                "operator": "Tamil Nadu Telecom",
                "circle": "Tamil Nadu"
            }
        }
    }

@router.get(
    "/{sourceid}/billpay/plans",
    tags=["Prepaid Plans"]
)
async def fetch_plans(
    sourceid: str,
    biller_id: Optional[str] = Query(None, alias="billerid"),
    circle_name: Optional[str] = Query(None, alias="circle_name"),
    plan_id: Optional[str] = Query(None, alias="plan_id"),
    plan_category_name: Optional[str] = Query(None, alias="plan_category_name"),
    operator: Optional[str] = Query(None, alias="operator"),
    circle: Optional[str] = Query(None, alias="circle"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT]))
):
    """
    Retrieves mobile prepaid plans for the specified operator and circle.
    """
    logger.info(f"Retrieving prepaid plans for source: {sourceid}, biller: {biller_id}, operator: {operator}, circle: {circle_name or circle}")
    plans = await PrepaidService.fetch_plans(
        session=db,
        biller_id=biller_id,
        circle_name=circle_name or circle,
        plan_id=plan_id,
        plan_category_name=plan_category_name,
        operator=operator
    )
    return plans

@router.post(
    "/{sourceid}/billpay/plans",
    tags=["Prepaid Plans"]
)
async def fetch_plans_post(
    sourceid: str,
    request_data: PrepaidPlansRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN, Role.CLIENT]))
):
    """
    Retrieves mobile prepaid plans via POST request with minimal payload.
    """
    logger.info(f"Retrieving prepaid plans via POST for source: {sourceid}, operator: {request_data.operator}, circle: {request_data.circle}")
    plans = await PrepaidService.fetch_plans(
        session=db,
        biller_id=None,
        circle_name=request_data.circle,
        plan_id=None,
        plan_category_name=request_data.plan_category_name,
        operator=request_data.operator
    )
    return plans
