from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_db
from app.database.models import User
from app.auth.jwt_handler import create_access_token
from app.auth.role_manager import Role
from app.utils.security import verify_password, get_password_hash
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
  username: str
  password: str

class TokenResponse(BaseModel):
  access_token: str
  token_type: str
  role: str

class SignupRequest(BaseModel):
  username: str
  email: str
  password: str
  role: str

class SignupResponse(BaseModel):
  success: bool
  message: str

@router.post("/signup", response_model=SignupResponse)
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
  """
  Registers a new user in the system with a designated role.
  """
  # 1. Validate role
  normalized_role = request.role.upper()
  allowed_roles = [Role.ADMIN, Role.CLIENT, Role.AUDITOR, Role.OPERATOR, Role.SECURITY_ANALYST, Role.CUSTOMER_SUPPORT]
  if normalized_role not in allowed_roles:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"Invalid role. Must be one of: {', '.join(allowed_roles)}"
    )

  # 2. Check duplicate username
  username_stmt = select(User).where(User.username == request.username)
  username_res = await db.execute(username_stmt)
  if username_res.scalar_one_or_none():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Username already registered"
    )

  # 3. Check duplicate email
  email_stmt = select(User).where(User.email == request.email)
  email_res = await db.execute(email_stmt)
  if email_res.scalar_one_or_none():
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Email already registered"
    )

  # 4. Hash password and save user
  hashed_password = get_password_hash(request.password)
  new_user = User(
    username=request.username,
    email=request.email,
    hashed_password=hashed_password,
    role=normalized_role
  )
  db.add(new_user)
  await db.commit()

  return {
    "success": True,
    "message": "User registered successfully"
  }

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(request: LoginRequest, db: AsyncSession = Depends(get_db)):
  """
  Exchanges credentials for a JWT token indicating user role mapping.
  """
  stmt = select(User).where(User.username == request.username)
  res = await db.execute(stmt)
  user = res.scalar_one_or_none()

  if not user or not verify_password(request.password, user.hashed_password):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid credentials. Verify username and password."
    )
  
  # Create access token with role claim
  access_token = create_access_token(
    data={"sub": user.username, "role": user.role},
    expires_delta=timedelta(minutes=60)
  )
  
  return {
    "access_token": access_token,
    "token_type": "bearer",
    "role": user.role
  }
