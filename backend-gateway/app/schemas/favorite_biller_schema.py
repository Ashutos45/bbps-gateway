from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.schemas.common_schema import Authenticator

class FavoriteBillerAddRequest(BaseModel):
    billerid: str = Field(..., description="Unique Biller Identifier")
    short_name: Optional[str] = Field(None, description="Short name / Nickname for the biller account")
    authenticators: Optional[List[Authenticator]] = Field(None, description="List of authenticators for the biller")
    autopay_status: Optional[str] = Field("N", description="Autopay status: Y or N")

    model_config = {
        "json_schema_extra": {
            "example": {
                "billerid": "MOCKELE00125MAH"
            }
        }
    }
    autopay_amount: Optional[float] = Field(None, description="Autopay limit amount")
    payment_account: Optional[Dict[str, Any]] = Field(None, description="Associated payment account details")
    frequency: Optional[str] = Field(None, description="Billing frequency if applicable")

class FavoriteBillerUpdateRequest(BaseModel):
    short_name: Optional[str] = Field(None, description="Updated short name")
    autopay_status: Optional[str] = Field(None, description="Updated autopay status")
    autopay_amount: Optional[float] = Field(None, description="Updated autopay limit amount")
    payment_account: Optional[Dict[str, Any]] = Field(None, description="Updated payment account details")
    frequency: Optional[str] = Field(None, description="Updated frequency")

class FavoriteBillerCustomer(BaseModel):
    mobile: str

class FavoriteBillerResponse(BaseModel):
    billeraccountid: str
    objectid: str = "billeraccount"
    sourceid: str
    billerid: str
    short_name: str
    authenticators: List[Dict[str, str]]
    status: str
    registration_date: str
    autopay_status: Optional[str] = "N"
    autopay_start_date: Optional[str] = None
    autopay_end_date: Optional[str] = None
    autopay_amount: Optional[float] = None
    currency: str = "356"
    frequency: Optional[str] = None
    payment_account: Optional[Dict[str, Any]] = None
    activation_date: str
    cprn: str
    customer: FavoriteBillerCustomer
