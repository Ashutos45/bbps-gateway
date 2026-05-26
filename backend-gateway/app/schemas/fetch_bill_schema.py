from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from app.schemas.common_schema import Authenticator, Customer, Metadata, Risk

class FetchBillRequest(BaseModel):
    billeraccountid: Optional[str] = Field(None, description="Biller account identifier if registered")
    billerid: Optional[str] = Field(None, description="Unique Biller ID")
    authenticators: Optional[List[Authenticator]] = Field(None, description="Authenticator parameters")
    payment_amount: Optional[str] = Field(None, description="Billing payment amount")
    currency: Optional[str] = Field(None, description="ISO currency code (e.g. 356)")
    customer: Optional[Customer] = None
    metadata: Optional[Metadata] = None
    risk: Optional[List[Risk]] = Field(None, description="Risk assessment tags")

    model_config = {
        "json_schema_extra": {
            "example": {
                "billerid": "MOCKELE00125MAH",
                "billeraccountid": "ELEC987654321"
            }
        }
    }

class BillItem(BaseModel):
    objectid: str = "bill"
    billid: str
    billerid: str
    billperiod: Optional[str] = None
    customer_name: Optional[str] = None
    billeraccountid: Optional[str] = None
    authenticators: List[Dict[str, str]]
    billnumber: str
    billdate: str
    billduedate: str
    billamount: str
    early_billduedate: Optional[str] = None
    early_billdiscount: Optional[str] = None
    early_billamount: Optional[str] = None
    late_payment_charges: Optional[str] = None
    late_payment_amount: Optional[str] = None
    net_billamount: str
    currency: str = "356"
    description: Optional[str] = None
    additional_details: List[Any] = []
    line_items: List[Any] = []
    billstatus: str = "UNPAID"

class FetchBillResponse(BaseModel):
    objectid: str = "validation"
    sourceid: str
    customerid: str
    validationid: str
    status: int = 200
    error_code: str = ""
    message: str = "Successful"
    payment_amount: Optional[str] = None
    validation_date: str
    valid_until: str
    billerid: str
    biller_name: str
    biller_category: str
    authenticators: List[Authenticator]
    currency: str = "356"
    billlist: List[BillItem] = []
    planlist: List[Any] = []
    pay_multiple_bills: str = "N"
    additional_validation_details: List[Dict[str, str]] = []
    additional_info: List[Any] = []
