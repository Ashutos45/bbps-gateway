from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database.db import get_db
from app.database.models import User
from app.auth.jwt_handler import create_access_token
from app.auth.role_manager import Role
from app.auth.auth_middleware import require_roles
from app.utils.security import verify_password, get_password_hash
from datetime import timedelta
import uuid

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

class ResetPasswordRequest(BaseModel):
  new_password: str

class RoleUpdateRequest(BaseModel):
  role: str

class UserResponse(BaseModel):
  id: str
  username: str
  email: str
  role: str
  is_active: bool

  class Config:
    from_attributes = True

@router.post("/signup", response_model=SignupResponse)
async def signup(
  request: SignupRequest, 
  db: AsyncSession = Depends(get_db),
  admin_user: dict = Depends(require_roles([Role.ADMIN]))
):
  """
  Registers a new user in the system. Restricted to ADMIN users only (user provisioning).
  """
  # 1. Validate and normalize role
  normalized_role = request.role.upper()
  if normalized_role == "OPERATOR":
    normalized_role = "OPERATIONS"
  elif normalized_role == "SECURITY_ANALYST":
    normalized_role = "AUDITOR"
  elif normalized_role == "CUSTOMER_SUPPORT":
    normalized_role = "OPERATIONS"

  allowed_roles = [Role.ADMIN, Role.CLIENT, Role.AUDITOR, Role.OPERATIONS]
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
    role=normalized_role,
    is_active=True
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
  
  # Check if account is active
  if not user.is_active:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Account is deactivated. Contact administrator."
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

@router.get("/users", response_model=List[UserResponse])
async def list_users(
  db: AsyncSession = Depends(get_db),
  admin_user: dict = Depends(require_roles([Role.ADMIN]))
):
  """
  Lists all registered users in the platform (ADMIN only).
  """
  stmt = select(User)
  result = await db.execute(stmt)
  users = result.scalars().all()
  return [
    UserResponse(
      id=str(user.id),
      username=user.username,
      email=user.email,
      role=user.role,
      is_active=user.is_active
    )
    for user in users
  ]

@router.post("/users/{username}/toggle-active")
async def toggle_user_active(
  username: str,
  db: AsyncSession = Depends(get_db),
  admin_user: dict = Depends(require_roles([Role.ADMIN]))
):
  """
  Toggles user activation status between Active and Deactivated (ADMIN only).
  """
  stmt = select(User).where(User.username == username)
  result = await db.execute(stmt)
  user = result.scalar_one_or_none()
  if not user:
    raise HTTPException(status_code=404, detail="User not found")
  
  # Toggle active status
  user.is_active = not user.is_active
  await db.commit()
  return {"success": True, "message": f"User {username} active status set to {user.is_active}"}

@router.post("/users/{username}/role")
async def update_user_role(
  username: str,
  request: RoleUpdateRequest,
  db: AsyncSession = Depends(get_db),
  admin_user: dict = Depends(require_roles([Role.ADMIN]))
):
  """
  Updates a user's assigned authorization role (ADMIN only).
  """
  normalized_role = request.role.upper()
  if normalized_role == "OPERATOR":
    normalized_role = "OPERATIONS"
  elif normalized_role == "SECURITY_ANALYST":
    normalized_role = "AUDITOR"
  elif normalized_role == "CUSTOMER_SUPPORT":
    normalized_role = "OPERATIONS"

  allowed_roles = [Role.ADMIN, Role.CLIENT, Role.AUDITOR, Role.OPERATIONS]
  if normalized_role not in allowed_roles:
    raise HTTPException(
      status_code=400,
      detail=f"Invalid role. Must be one of: {', '.join(allowed_roles)}"
    )

  stmt = select(User).where(User.username == username)
  result = await db.execute(stmt)
  user = result.scalar_one_or_none()
  if not user:
    raise HTTPException(status_code=404, detail="User not found")

  user.role = normalized_role
  await db.commit()
  return {"success": True, "message": f"User {username} role updated to {user.role}"}

@router.post("/users/{username}/reset-password")
async def reset_user_password(
  username: str,
  request: ResetPasswordRequest,
  db: AsyncSession = Depends(get_db),
  admin_user: dict = Depends(require_roles([Role.ADMIN]))
):
  """
  Resets a user's password (ADMIN only).
  """
  stmt = select(User).where(User.username == username)
  result = await db.execute(stmt)
  user = result.scalar_one_or_none()
  if not user:
    raise HTTPException(status_code=404, detail="User not found")

  user.hashed_password = get_password_hash(request.new_password)
  await db.commit()
  return {"success": True, "message": f"Password reset successfully for user {username}"}
