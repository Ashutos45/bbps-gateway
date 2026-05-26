from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any

class Authenticator(BaseModel):
    seq: str = Field(..., description="Order of parameter appearance")
    parameter_name: str = Field(..., description="Name of parameter (e.g. Consumer No)")
    value: str = Field(..., description="Value of the parameter")

class Customer(BaseModel):
    firstname: str = Field(..., description="Customer's first name")
    lastname: str = Field(..., description="Customer's last name")
    mobile: str = Field(..., description="Customer's primary mobile number")
    email: Optional[str] = Field(None, description="Customer's email address")

class Agent(BaseModel):
    agentid: str = Field(..., description="Agent Identifier")
    sub_agentid: Optional[str] = Field(None, description="Sub-agent Identifier")

class Device(BaseModel):
    init_channel: str = Field(..., description="Channel initiating request (e.g. Internet, Mobile)")
    ip: Optional[str] = Field(None, description="Customer's IP address")
    mac: Optional[str] = Field(None, description="MAC address")
    os: Optional[str] = Field(None, description="Operating system")
    app: Optional[str] = Field(None, description="App name")
    user_agent: Optional[str] = Field(None, description="Browser user agent")

class AdditionalInfoItem(BaseModel):
    name: str
    value: str

class Metadata(BaseModel):
    agent: Agent
    device: Device
    additional_info: List[AdditionalInfoItem] = Field(default_factory=list)

class Risk(BaseModel):
    score_provider: str = Field(..., description="Risk score provider")
    score_value: str = Field(..., description="Score rating")
    score_type: str = Field(..., description="Type of risk evaluated")

class ApprovalDetails(BaseModel):
    requestid: str
    makerid: str
    maker_request_date: str
    approverid: str
    approval_date: str
