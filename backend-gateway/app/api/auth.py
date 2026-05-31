from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from app.database.db import get_db
from app.database.models import User, AdminAccessKey, AuditLog, TrustedDevice
from app.auth.jwt_handler import create_access_token
from app.auth.role_manager import Role
from app.auth.auth_middleware import require_role, require_roles
from app.utils.security import verify_password, get_password_hash
from datetime import datetime, timezone, timedelta
import secrets
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic Schemas
class ClientSignupRequest(BaseModel):
    username: str
    email: str
    password: str
    organization: Optional[str] = None
    company: Optional[str] = None

class SignupResponse(BaseModel):
    success: bool
    message: str

class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: Optional[str] = None
    browser_fingerprint: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

class AdminTokenRequest(BaseModel):
    username: str
    password: str
    admin_access_key: str

class AdminCreateRequest(BaseModel):
    username: str
    email: str
    role: str  # ADMIN, OPERATIONS, AUDITOR
    access_level: Optional[int] = 1

class AdminCreateResponse(BaseModel):
    success: bool
    username: str
    admin_access_key: str

class AdminActivationRequest(BaseModel):
    username: str
    password: str
    admin_access_key: str

class StandaloneKeyRequest(BaseModel):
    role: str

class StandaloneKeyResponse(BaseModel):
    success: bool
    role: str
    admin_access_key: str

class AdminSignupRequest(BaseModel):
    username: str
    email: str
    password: str
    admin_access_key: str

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
    organization: Optional[str] = None
    company: Optional[str] = None

    class Config:
        from_attributes = True

class AdminKeyResponse(BaseModel):
    id: str
    user_id: str
    username: Optional[str] = None
    key_hash: str
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

class AuditLogResponse(BaseModel):
    id: str
    username: str
    role: str
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

# Audit Logging Helper
async def log_admin_action(db: AsyncSession, username: str, role: str, action: str, details: str = None, request: Request = None):
    ip_address = request.client.host if request and request.client else None
    audit = AuditLog(
        username=username,
        role=role,
        action=action,
        details=details,
        ip_address=ip_address
    )
    db.add(audit)
    await db.commit()

# Device Registration Helper
async def register_or_update_device(db: AsyncSession, user_id, device_id: str, fingerprint: str, ip_address: str):
    if not device_id:
        return
    stmt = select(TrustedDevice).where(TrustedDevice.device_id == device_id)
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()
    
    if device:
        if device.last_ip != ip_address:
            # IP Changed - Log it
            audit = AuditLog(
                username=str(user_id),
                role="SYSTEM",
                action="DYNAMIC_IP_CHANGE",
                details=f"Trusted device {device_id} changed IP from {device.last_ip} to {ip_address}",
                ip_address=ip_address
            )
            db.add(audit)
        device.last_ip = ip_address
        device.last_login_time = datetime.now(timezone.utc)
    else:
        # Register new device
        new_device = TrustedDevice(
            user_id=user_id,
            device_id=device_id,
            fingerprint=fingerprint or "Unknown",
            last_ip=ip_address,
            last_login_time=datetime.now(timezone.utc),
            is_approved=False
        )
        db.add(new_device)
        audit = AuditLog(
            username=str(user_id),
            role="SYSTEM",
            action="NEW_DEVICE_REGISTERED",
            details=f"New device {device_id} registered from IP {ip_address} and awaits approval.",
            ip_address=ip_address
        )
        db.add(audit)
    await db.commit()

# --- Public Client Onboarding Routes ---

# --- Public Client Onboarding Routes ---

@router.post("/register-client", response_model=SignupResponse)
async def client_signup(payload: ClientSignupRequest, req_obj: Request, db: AsyncSession = Depends(get_db)):
    """
    Public self-registration for standard CLIENT accounts.
    """
    # Check duplicate username
    username_stmt = select(User).where(User.username == payload.username)
    username_res = await db.execute(username_stmt)
    if username_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check duplicate email
    email_stmt = select(User).where(User.email == payload.email)
    email_res = await db.execute(email_stmt)
    if email_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(payload.password)
    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_password,
        role=Role.CLIENT,
        is_active=True,
        organization=payload.organization,
        company=payload.company
    )
    db.add(new_user)
    await db.commit()

    await log_admin_action(
        db,
        payload.username,
        Role.CLIENT,
        "CLIENT_REGISTERED",
        f"Client self-registration successful for user: {payload.username}",
        req_obj
    )

    return {
        "success": True,
        "message": "Client self-registration successful"
    }

@router.post("/login-client", response_model=TokenResponse)
async def client_login(payload: LoginRequest, req_obj: Request, db: AsyncSession = Depends(get_db)):
    """
    Public standard login for CLIENT accounts.
    """
    stmt = select(User).where(User.username == payload.username)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        await log_admin_action(
            db,
            payload.username,
            Role.CLIENT,
            "CLIENT_LOGIN_FAILED",
            f"Failed client login attempt (invalid credentials) for user: {payload.username}",
            req_obj
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials. Verify username and password."
        )

    if user.role != Role.CLIENT:
        await log_admin_action(
            db,
            user.username,
            user.role,
            "CLIENT_LOGIN_FAILED",
            f"Failed client login attempt: Administrative user '{user.username}' with role {user.role} attempted client login.",
            req_obj
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative accounts must authenticate using the Admin Login portal."
        )

    if not user.is_active:
        await log_admin_action(
            db,
            user.username,
            user.role,
            "CLIENT_LOGIN_FAILED",
            f"Failed client login attempt: Account is deactivated for user '{user.username}'.",
            req_obj
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact administrator."
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=60)
    )

    await log_admin_action(
        db,
        user.username,
        user.role,
        "CLIENT_LOGIN_SUCCESS",
        f"Client user '{user.username}' logged in successfully",
        req_obj
    )

    client_ip = req_obj.headers.get("x-forwarded-for", "").split(",")[0].strip() or (req_obj.client.host if req_obj.client else "unknown")
    await register_or_update_device(db, user.id, payload.device_id, payload.browser_fingerprint, client_ip)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }

# --- Separate Admin/Operational Authentication ---

@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(payload: LoginRequest, req_obj: Request, db: AsyncSession = Depends(get_db)):
    """
    Dedicated Admin Login portal requiring username/email and password.
    """
    # 1. Lookup User (by username or email)
    stmt = select(User).where((User.username == payload.username) | (User.email == payload.username))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        await log_admin_action(
            db,
            payload.username,
            "UNKNOWN",
            "ADMIN_LOGIN_FAILED",
            f"Failed admin login attempt: Administrative user '{payload.username}' not found.",
            req_obj
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials. Verify username/email and password."
        )

    if user.role == Role.CLIENT:
        await log_admin_action(
            db,
            user.username,
            user.role,
            "ADMIN_LOGIN_FAILED",
            f"Failed admin login attempt: Client user '{user.username}' attempted administrative login.",
            req_obj
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Client accounts must authenticate using the Client portal."
        )

    if not user.is_active:
        await log_admin_action(
            db,
            user.username,
            user.role,
            "ADMIN_LOGIN_FAILED",
            f"Failed admin login attempt: Deactivated admin user '{user.username}' attempted login.",
            req_obj
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative account is deactivated or not yet activated."
        )

    if not verify_password(payload.password, user.hashed_password):
        await log_admin_action(
            db,
            user.username,
            user.role,
            "ADMIN_LOGIN_FAILED",
            f"Failed admin login attempt (invalid credentials) for user: {user.username}",
            req_obj
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials. Verify username/email and password."
        )

    # Create Access Token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=60)
    )

    # Log login success
    await log_admin_action(db, user.username, user.role, "ADMIN_LOGIN_SUCCESS", "Admin logged in successfully", req_obj)
    
    client_ip = req_obj.headers.get("x-forwarded-for", "").split(",")[0].strip() or (req_obj.client.host if req_obj.client else "unknown")
    await register_or_update_device(db, user.id, payload.device_id, payload.browser_fingerprint, client_ip)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }


@router.post("/admin/generate-key", response_model=StandaloneKeyResponse)
async def generate_standalone_key(
    request: StandaloneKeyRequest,
    req_obj: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.SUPER_ADMIN]))
):
    """
    Allows SUPER_ADMIN to pre-generate a standalone ADMIN_ACCESS_KEY associated with a designated role.
    """
    role_upper = request.role.upper()
    if role_upper not in (Role.ADMIN, Role.OPERATIONS, Role.AUDITOR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid administrative role. Must be one of ADMIN, OPERATIONS, AUDITOR"
        )

    # Generate standalone key
    raw_key = "ADM_" + secrets.token_hex(16)
    access_key = AdminAccessKey(
        user_id=None,  # unassigned
        key_hash=get_password_hash(raw_key),
        role=role_upper,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=90)
    )
    db.add(access_key)
    await db.commit()

    # Log action
    await log_admin_action(
        db, 
        current_user["username"], 
        current_user["role"], 
        "GENERATE_STANDALONE_KEY", 
        f"Generated standalone key for role: {role_upper}",
        req_obj
    )

    return {
        "success": True,
        "role": role_upper,
        "admin_access_key": raw_key
    }



@router.post("/admin/activate", response_model=SignupResponse)
async def activate_admin_account(
    request: AdminActivationRequest,
    req_obj: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    First-time Admin Activation flow verifying key exists, unconsumed, unexpired,
    and sets up username/email and password.
    """
    # 1. Lookup unconsumed and active admin access keys
    key_stmt = select(AdminAccessKey).where(
        AdminAccessKey.is_active == True
    )
    key_res = await db.execute(key_stmt)
    keys = key_res.scalars().all()

    target_key = None
    for access_key in keys:
        if access_key.expires_at and datetime.now(timezone.utc) > access_key.expires_at:
            continue
        if verify_password(request.admin_access_key, access_key.key_hash):
            target_key = access_key
            break

    if not target_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid, expired, or already used activation key."
        )

    # 2. Check if the key is associated with a pre-created invitation (user_id is not None)
    if target_key.user_id:
        user_stmt = select(User).where(User.id == target_key.user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User associated with activation key not found."
            )
            
        # Verify username or email matches
        if request.username.lower() not in (user.username.lower(), user.email.lower()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid credentials: username/email does not match invitation."
            )
            
        # Update user's password and activate
        user.hashed_password = get_password_hash(request.password)
        user.is_active = True
        
        # Mark key as consumed
        target_key.is_active = False
        await db.commit()
        
        # Log action
        await log_admin_action(
            db,
            user.username,
            user.role,
            "ADMIN_ACTIVATION",
            f"Admin account activated for {user.username} using key",
            req_obj
        )
        
        return {
            "success": True,
            "message": f"Administrative account activated successfully for {user.username}. You can now log in."
        }
        
    else:
        # Standalone Key Flow (unassigned key)
        email = request.username
        username = request.username
        if "@" in request.username:
            username = request.username.split("@")[0]
        else:
            email = f"{request.username}@bbps-gateway.in"
            
        # Verify uniqueness
        user_exists_stmt = select(User).where((User.username == username) | (User.email == email))
        if (await db.execute(user_exists_stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
            
        target_role = target_key.role or Role.ADMIN
        new_user_id = uuid.uuid4()
        new_user = User(
            id=new_user_id,
            username=username,
            email=email,
            hashed_password=get_password_hash(request.password),
            role=target_role,
            is_active=True
        )
        db.add(new_user)
        
        # Bind and consume key
        target_key.user_id = new_user_id
        target_key.is_active = False
        await db.commit()
        
        # Log action
        await log_admin_action(
            db,
            username,
            target_role,
            "ADMIN_ACTIVATION",
            f"Admin account registered and activated as role: {target_role} using standalone key",
            req_obj
        )
        
        return {
            "success": True,
            "message": f"Administrative registration and activation successful as role {target_role}"
        }

# --- Super Admin Operations (Restricted to SUPER_ADMIN) ---

@router.post("/admin/create", response_model=AdminCreateResponse)
async def provision_admin_user(
    request: AdminCreateRequest,
    req_obj: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles([Role.SUPER_ADMIN, Role.ADMIN]))
):
    """
    Allows SUPER_ADMIN or ADMIN to provision new ADMIN, OPERATIONS, or AUDITOR staff accounts and generates a unique ADMIN_ACCESS_KEY.
    """
    role_upper = request.role.upper()
    if role_upper not in (Role.ADMIN, Role.OPERATIONS, Role.AUDITOR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid administrative role. Must be one of ADMIN, OPERATIONS, AUDITOR"
        )

    # Check duplicates
    username_stmt = select(User).where(User.username == request.username)
    if (await db.execute(username_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    email_stmt = select(User).where(User.email == request.email)
    if (await db.execute(email_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Save User as inactive
    u_id = uuid.uuid4()
    new_user = User(
        id=u_id,
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash("TEMP_DUMMY_PWD_BBPS_GATEWAY"),
        role=role_upper,
        is_active=False
    )
    db.add(new_user)

    # Generate Admin Key
    raw_key = "ADM_" + secrets.token_hex(16)
    access_key = AdminAccessKey(
        user_id=u_id,
        key_hash=get_password_hash(raw_key),
        role=role_upper,
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=90) # default 90 days expiry
    )
    db.add(access_key)
    await db.commit()

    # Log action
    await log_admin_action(
        db, 
        current_user["username"], 
        current_user["role"], 
        "PROVISION_ADMIN_USER", 
        f"Provisioned admin user: {request.username} as {role_upper}",
        req_obj
    )

    return {
        "success": True,
        "username": request.username,
        "admin_access_key": raw_key
    }

@router.delete("/admin/users/{username}")
async def delete_admin_user(
    username: str,
    req_obj: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.SUPER_ADMIN]))
):
    """
    Deletes an admin/staff user account (SUPER_ADMIN only).
    """
    stmt = select(User).where(User.username == username)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == Role.SUPER_ADMIN:
        raise HTTPException(status_code=400, detail="Cannot delete a SUPER_ADMIN account")

    # Delete access keys and user
    await db.execute(delete(AdminAccessKey).where(AdminAccessKey.user_id == user.id))
    await db.delete(user)
    await db.commit()

    await log_admin_action(
        db, 
        current_user["username"], 
        current_user["role"], 
        "DELETE_ADMIN_USER", 
        f"Deleted admin user: {username}",
        req_obj
    )
    return {"success": True, "message": f"Successfully deleted administrative user {username}"}

@router.get("/admin/keys", response_model=List[AdminKeyResponse])
async def list_admin_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.SUPER_ADMIN]))
):
    """
    Lists metadata and hashes of all provisioning access keys (SUPER_ADMIN only).
    """
    stmt = select(AdminAccessKey, User.username).outerjoin(User, AdminAccessKey.user_id == User.id)
    res = await db.execute(stmt)
    rows = res.all()
    return [
        AdminKeyResponse(
            id=str(row.AdminAccessKey.id),
            user_id=str(row.AdminAccessKey.user_id) if row.AdminAccessKey.user_id else "",
            username=row.username,
            key_hash=row.AdminAccessKey.key_hash[:20] + "...", # obscure secret hash
            is_active=row.AdminAccessKey.is_active,
            expires_at=row.AdminAccessKey.expires_at,
            created_at=row.AdminAccessKey.created_at
        )
        for row in rows
    ]

@router.post("/admin/users/{username}/regenerate-key", response_model=AdminCreateResponse)
async def regenerate_admin_key(
    username: str,
    req_obj: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.SUPER_ADMIN]))
):
    """
    Regenerates a new unique key for an admin/staff user (SUPER_ADMIN only).
    """
    user_stmt = select(User).where(User.username == username)
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Deactivate old keys
    await db.execute(
        select(AdminAccessKey)
        .where(AdminAccessKey.user_id == user.id)
    )
    # We can just delete old keys and write a new one
    await db.execute(delete(AdminAccessKey).where(AdminAccessKey.user_id == user.id))

    # Generate new key
    raw_key = "ADM_" + secrets.token_hex(16)
    access_key = AdminAccessKey(
        user_id=user.id,
        key_hash=get_password_hash(raw_key),
        is_active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=90)
    )
    db.add(access_key)
    await db.commit()

    await log_admin_action(
        db, 
        current_user["username"], 
        current_user["role"], 
        "REGENERATE_ADMIN_KEY", 
        f"Regenerated access key for admin user: {username}",
        req_obj
    )

    return {
        "success": True,
        "username": username,
        "admin_access_key": raw_key
    }

@router.get("/admin/logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.SUPER_ADMIN]))
):
    """
    Lists system security and operational audit logs (SUPER_ADMIN only).
    """
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    logs = (await db.execute(stmt)).scalars().all()
    return [
        AuditLogResponse(
            id=str(log.id),
            username=log.username,
            role=log.role,
            action=log.action,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at
        )
        for log in logs
    ]

# --- Admin Operations (Restricted to ADMIN/SUPER_ADMIN via hierarchy) ---

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.ADMIN]))
):
    """
    Lists all platform users (ADMIN only).
    """
    stmt = select(User)
    users = (await db.execute(stmt)).scalars().all()
    return [
        UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            organization=user.organization,
            company=user.company
        )
        for user in users
    ]

@router.post("/users/{username}/toggle-active")
async def toggle_user_active(
    username: str,
    req_obj: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.ADMIN]))
):
    """
    Toggles client active/inactive status (ADMIN only).
    """
    stmt = select(User).where(User.username == username)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role in (Role.SUPER_ADMIN, Role.ADMIN) and current_user["role"] != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only SUPER_ADMIN can toggle active status of other administrators."
        )

    user.is_active = not user.is_active
    await db.commit()

    await log_admin_action(
        db, 
        current_user["username"], 
        current_user["role"], 
        "TOGGLE_USER_ACTIVE", 
        f"Toggled active state for user {username} to {user.is_active}",
        req_obj
    )
    return {"success": True, "message": f"User {username} active status set to {user.is_active}"}

@router.post("/users/{username}/role")
async def update_user_role(
    username: str,
    request: RoleUpdateRequest,
    req_obj: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.ADMIN]))
):
    """
    Updates a user's role. Assigning or updating admin roles is restricted to SUPER_ADMIN.
    """
    target_role = request.role.upper()
    if target_role == "OPERATOR":
        target_role = Role.OPERATIONS
    elif target_role == "SECURITY_ANALYST":
        target_role = Role.AUDITOR
    elif target_role == "CUSTOMER_SUPPORT":
        target_role = Role.OPERATIONS

    allowed_roles = [Role.SUPER_ADMIN, Role.ADMIN, Role.CLIENT, Role.AUDITOR, Role.OPERATIONS]
    if target_role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(allowed_roles)}"
        )

    stmt = select(User).where(User.username == username)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If updating to or from an Admin role, require SUPER_ADMIN
    is_admin_change = (user.role != Role.CLIENT) or (target_role != Role.CLIENT)
    if is_admin_change and current_user["role"] != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only SUPER_ADMIN can modify administrative/operational role assignments."
        )

    old_role = user.role
    user.role = target_role
    await db.commit()

    await log_admin_action(
        db, 
        current_user["username"], 
        current_user["role"], 
        "UPDATE_USER_ROLE", 
        f"Updated role of {username} from {old_role} to {target_role}",
        req_obj
    )
    return {"success": True, "message": f"User {username} role updated to {user.role}"}

@router.post("/users/{username}/reset-password")
async def reset_user_password(
    username: str,
    request: ResetPasswordRequest,
    req_obj: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role([Role.ADMIN]))
):
    """
    Resets a user's password. Resetting administrator passwords requires SUPER_ADMIN.
    """
    stmt = select(User).where(User.username == username)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_target_admin = user.role != Role.CLIENT
    if is_target_admin and current_user["role"] != Role.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only SUPER_ADMIN can reset passwords for other administrators."
        )

    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    await log_admin_action(
        db, 
        current_user["username"], 
        current_user["role"], 
        "RESET_USER_PASSWORD", 
        f"Reset password for user {username}",
        req_obj
    )
    return {"success": True, "message": f"Password reset successfully for user {username}"}
