from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.database.db import get_db
from app.services.biller_master_service import BillerMasterService
from app.auth.auth_middleware import require_roles
from app.auth.role_manager import Role
from app.auth.token_service import generate_signed_download_token
from loguru import logger

router = APIRouter()

class BillerFileRequest(BaseModel):
  callback_url: str = Field(..., alias="callbackUrl", description="The callback URL to post file status updates")

  class Config:
    populate_by_name = True

class BillerFileResponse(BaseModel):
  objectid: str = "file"
  fileid: str
  file_status: str
  callback_url: str

@router.post(
  "/{sourceid}/billpay/billers/file",
  response_model=BillerFileResponse,
  tags=["Biller Master"]
)
async def initiate_file_generation(
  sourceid: str,
  request_data: BillerFileRequest,
  db: AsyncSession = Depends(get_db),
  user: dict = Depends(require_roles([Role.ADMIN]))
):
  """
  Triggers asynchronous Biller Master File generation and immediately returns a File ID.
  Requires ADMIN authorization role.
  """
  logger.info(f"Initiated Biller list generation for source: {sourceid}, user: {user['username']}")
  result = await BillerMasterService.initiate_file_generation(
    session=db,
    source_id=sourceid,
    callback_url=request_data.callback_url
  )
  return result

@router.get(
  "/{sourceid}/billpay/billers/file/{fileid}",
  tags=["Biller Master"]
)
async def get_file_archive(
  sourceid: str,
  fileid: str,
  request: Request,
  user: dict = Depends(require_roles([Role.ADMIN, Role.OPERATOR]))
):
  """
  Retrieves compilation status of the zipped master file.
  If completed, appends a temporary cryptographically signed download URL for direct chunked streaming.
  Requires ADMIN or OPERATOR authorization roles.
  """
  logger.info(f"Retrieving biller master file status. File: {fileid}, User: {user['username']}")
  result = await BillerMasterService.get_file_archive(file_id=fileid)
  
  if result.get("status") == 0:
    token = generate_signed_download_token(fileid, user["username"])
    # Resolve absolute download endpoint URL
    base_url = str(request.base_url)
    result["downloadUrl"] = f"{base_url}download/file/{fileid}?token={token}"

  return result

@router.get(
  "/{sourceid}/billpay/billers/{billerid}",
  tags=["Biller Master"]
)
async def get_biller_by_id(
  sourceid: str,
  billerid: str,
  db: AsyncSession = Depends(get_db)
):
  """
  Retrieves detailed information about a specific biller using its unique Biller ID.
  """
  logger.info(f"Retrieving biller by ID: {billerid} for source: {sourceid}")
  from app.database.repositories.biller_repository import BillerRepository
  from app.core.exceptions import BillerNotFoundError
  
  biller = await BillerRepository.get_by_biller_id(db, billerid)
  if not biller:
      raise BillerNotFoundError(billerid)

  meta = biller.biller_metadata or {}
  category = biller.category.upper()
  
  if "ELECT" in category:
      auth_name = "Consumer No"
      auth_regex = "^[0-9]{10}$"
  elif "WATER" in category:
      auth_name = "Connection No"
      auth_regex = "^[0-9]{8}$"
  elif "GAS" in category:
      auth_name = "Customer ID"
      auth_regex = "^[0-9]{10}$"
  elif "MOBILE" in category or "TELE" in category:
      auth_name = "Mobile Number"
      auth_regex = "^[0-9]{10}$"
  else:
      auth_name = "Account Number"
      auth_regex = "^[a-zA-Z0-9]{5,15}$"

  min_lim = meta.get("min_amount", "5.00")
  max_lim = meta.get("max_amount", "100000.00")
  
  return {
      "status": 200,
      "billerid": biller.biller_id,
      "objectid": "biller",
      "sourceid": sourceid,
      "biller_legal_name": biller.biller_name.split("-")[0].strip(),
      "biller_name": biller.biller_name,
      "biller_location": biller.region,
      "biller_location_desc": f"{biller.region} region",
      "biller_category": biller.category,
      "biller_reg_address": f"Registered Office, {biller.region}",
      "biller_reg_city": meta.get("city", "Mumbai"),
      "biller_reg_pin": "400001",
      "biller_reg_state": meta.get("state", "Maharashtra"),
      "biller_reg_country": "India",
      "isbillerbbps": "Y",
      "currency": "356",
      "biller_type": "BILL PRESENTMENT & PAYMENT" if "MOBILE" not in category and "TELE" not in category else "PAYMENT ONLY",
      "biller_mode": "ONLINE",
      "allowed_payment_methods": [
          {
              "payment_method": "CreditCard",
              "payment_method_category": "CreditCard",
              "min_limit": min_lim,
              "max_limit": max_lim,
              "autopay_allowed": "Y",
              "paylater_allowed": "N"
          },
          {
              "payment_method": "UPI",
              "payment_method_category": "UPI",
              "min_limit": min_lim,
              "max_limit": max_lim,
              "autopay_allowed": "Y",
              "paylater_allowed": "N"
          }
      ],
      "payment_channels": [
          {
              "payment_channel": "INT",
              "min_limit": min_lim,
              "max_limit": max_lim
          },
          {
              "payment_channel": "MOB",
              "min_limit": min_lim,
              "max_limit": max_lim
          }
      ],
      "biller_effective_from": "01-01-2020",
      "biller_effective_to": "01-01-2030",
      "biller_status": "ACTIVE",
      "temp_deactivation_start": "",
      "temp_deactivation_end": "",
      "biller_created_date": "01-01-2020",
      "biller_lastmodified_date": "01-01-2026",
      "authenticators": [
          {
              "seq": "1",
              "parameter_name": auth_name,
              "data_type": "NUMERIC" if auth_name == "Mobile Number" or "No" in auth_name else "ALPHANUMERIC",
              "optional": False,
              "regex": auth_regex,
              "error_message": f"Please enter a valid {auth_name}",
              "encryption_required": None,
              "list_of_values": []
          }
      ],
      "biller_logo": "",
      "biller_bill_copy": "",
      "biller_remarks": "",
      "partial_pay": "Y",
      "partial_pay_amount": "Y",
      "pay_after_duedate": "Y",
      "online_validation": "Y",
      "customer_conv_fee": None,
      "plan_available": "Y" if "TELE" in category or "MOBILE" in category else None,
      "paymentamount_validation": None,
      "additional_validation_details": ""
  }
