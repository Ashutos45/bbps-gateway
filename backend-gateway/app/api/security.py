from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from app.database.db import get_db
from app.database.models import IPWhitelist, GatewayRequestLog, Report, AuditLog, User
from app.auth.auth_middleware import require_roles
from app.auth.role_manager import Role, ROLE_HIERARCHY
from app.api.auth import log_admin_action
from app.utils.encryption import decrypt_data
from datetime import datetime
from loguru import logger

router = APIRouter()

# Pydantic Schemas
class IPWhitelistCreate(BaseModel):
    ip_address: str
    is_cidr: bool = False
    organization_id: Optional[str] = None
    description: Optional[str] = None

class IPWhitelistResponse(BaseModel):
    id: str
    ip_address: str
    is_cidr: bool = False
    organization_id: Optional[str] = None
    description: Optional[str] = None
    added_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True



class RequestLogResponse(BaseModel):
    id: str
    request_id: str
    timestamp: datetime
    client_user: Optional[str] = None
    source_ip: Optional[str] = None
    endpoint: str
    request_status: str
    response_code: Optional[int] = None
    processing_time_ms: Optional[float] = None

    class Config:
        from_attributes = True

class ReportResponse(BaseModel):
    id: str
    title: str
    report_type: str
    owner_role: str
    encrypted_preview: str
    created_at: datetime

    class Config:
        from_attributes = True

class DecryptRequest(BaseModel):
    decryption_key: str

class SecurityEventResponse(BaseModel):
    id: str
    timestamp: str
    username: str
    role: str
    action: str
    details: Optional[str] = None
    ip_address: Optional[str] = None

class SecurityStatsResponse(BaseModel):
    active_users: int
    active_ips: int
    failed_login_count: int
    blocked_ip_count: int
    active_sessions: int
    api_usage_statistics: dict
    recent_events: List[SecurityEventResponse]

# --- IP Whitelist Operations (Restricted to ADMIN / SUPER_ADMIN) ---

@router.get("/security/ip-whitelist", response_model=List[IPWhitelistResponse], tags=["IP Whitelist"])
async def get_ip_whitelist(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN, Role.SUPER_ADMIN]))
):
    """
    Lists all whitelisted IPs stored in the database.
    """
    stmt = select(IPWhitelist).order_by(IPWhitelist.created_at.desc())
    res = await db.execute(stmt)
    entries = res.scalars().all()
    return [
        IPWhitelistResponse(
            id=str(e.id),
            ip_address=e.ip_address,
            is_cidr=e.is_cidr,
            organization_id=e.organization_id,
            description=e.description,
            added_by=e.added_by,
            created_at=e.created_at
        ) for e in entries
    ]

@router.post("/security/ip-whitelist", response_model=IPWhitelistResponse, tags=["IP Whitelist"])
async def add_ip_whitelist(
    payload: IPWhitelistCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN, Role.SUPER_ADMIN]))
):
    """
    Adds a new IP address to the whitelist.
    """
    ip_clean = payload.ip_address.strip()
    if not ip_clean:
        raise HTTPException(status_code=400, detail="IP address cannot be empty")

    stmt = select(IPWhitelist).where(IPWhitelist.ip_address == ip_clean)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="IP address already whitelisted")
        
    entry = IPWhitelist(
        ip_address=ip_clean,
        is_cidr=payload.is_cidr,
        organization_id=payload.organization_id,
        description=payload.description or "Manual entry",
        added_by=user["username"]
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    await log_admin_action(
        db,
        user["username"],
        user["role"],
        "IP_WHITELIST_ADD",
        f"Added IP to whitelist: {ip_clean}",
        request
    )
    return entry

@router.delete("/security/ip-whitelist/{ip:path}", tags=["IP Whitelist"])
async def delete_ip_whitelist(
    ip: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN, Role.SUPER_ADMIN]))
):
    """
    Removes an IP address from the whitelist.
    """
    stmt = select(IPWhitelist).where(IPWhitelist.ip_address == ip)
    res = await db.execute(stmt)
    entry = res.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="IP address not found in whitelist")
        
    await db.delete(entry)
    await db.commit()
    
    await log_admin_action(
        db,
        user["username"],
        user["role"],
        "IP_WHITELIST_REMOVE",
        f"Removed IP from whitelist: {ip}",
        request
    )
    return {"success": True, "message": f"IP {ip} removed from whitelist"}



# --- Request Monitoring Dashboard (Restricted to ADMIN / SUPER_ADMIN) ---

@router.get("/security/request-logs", response_model=List[RequestLogResponse], tags=["Security Logs"])
async def get_request_logs(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN, Role.SUPER_ADMIN]))
):
    """
    Retrieves the most recent API transaction logs processed by the gateway.
    """
    stmt = select(GatewayRequestLog)
    if status_filter:
        stmt = stmt.where(GatewayRequestLog.request_status == status_filter)
        
    stmt = stmt.order_by(GatewayRequestLog.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return [
        RequestLogResponse(
            id=str(l.id),
            request_id=l.request_id,
            timestamp=l.created_at,
            client_user=l.client_user,
            source_ip=l.source_ip,
            endpoint=l.endpoint,
            request_status=l.request_status,
            response_code=l.response_code,
            processing_time_ms=float(l.processing_time_ms) if l.processing_time_ms else None
        ) for l in logs
    ]

# --- Secure Reports Portal & Decryption ---

@router.get("/reports", response_model=List[ReportResponse], tags=["Reports"])
async def list_reports(
    db: AsyncSession = Depends(get_db)
):
    """
    Lists report metadata. Searchable without authentication.
    """
    stmt = select(Report).order_by(Report.created_at.desc())
    res = await db.execute(stmt)
    reports = res.scalars().all()
    return [
        ReportResponse(
            id=str(r.id),
            title=r.title,
            report_type=r.report_type,
            owner_role=r.owner_role,
            encrypted_preview=r.encrypted_content[:30] + "...",
            created_at=r.created_at
        ) for r in reports
    ]

@router.post("/reports/{id}/decrypt", tags=["Reports"])
async def decrypt_report(
    id: str,
    payload: DecryptRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN, Role.SUPER_ADMIN, Role.OPERATIONS, Role.AUDITOR, Role.CLIENT]))
):
    """
    Decrypts secure report contents if role checks and decryption key validation pass.
    """
    # 1. Fetch report
    stmt = select(Report).where(Report.id == id)
    res = await db.execute(stmt)
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
    user_role = user["role"]
    username = user["username"]
    
    # 2. Check role authorization clearance:
    # A user can decrypt if they are SUPER_ADMIN, ADMIN, or if their role matches report.owner_role
    is_cleared = False
    if user_role in (Role.SUPER_ADMIN, Role.ADMIN):
        is_cleared = True
    elif user_role == report.owner_role:
        is_cleared = True
    elif user_role in ROLE_HIERARCHY and report.owner_role in ROLE_HIERARCHY[user_role]:
        is_cleared = True
        
    if not is_cleared:
        await log_admin_action(
            db,
            username,
            user_role,
            "REPORT_DECRYPTION_FAILED",
            f"Unauthorized role access attempt for report '{report.title}' (Role: {user_role}, Required: {report.owner_role})",
            request
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Insufficient privileges to decrypt this report (Required role: {report.owner_role})"
        )
        
    # 3. Check key ownership / verification
    from app.utils.security import verify_password
    if not verify_password(payload.decryption_key, report.key_hash):
        await log_admin_action(
            db,
            username,
            user_role,
            "REPORT_DECRYPTION_FAILED",
            f"Incorrect decryption key provided for report '{report.title}'",
            request
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid decryption key")
        
    # 4. Success decrypting
    try:
        decrypted_text = decrypt_data(report.encrypted_content, payload.decryption_key)
        await log_admin_action(
            db,
            username,
            user_role,
            "REPORT_DECRYPTION_SUCCESS",
            f"Decrypted report '{report.title}' successfully",
            request
        )
        return {
            "success": True,
            "title": report.title,
            "decrypted_content": decrypted_text
        }
    except Exception as e:
        logger.error(f"Error decrypting report data: {e}")
        raise HTTPException(status_code=500, detail="Failed to decrypt report content due to formatting error")

# --- Security Operations Dashboard (Restricted to ADMIN / SUPER_ADMIN) ---

@router.get("/security/security-stats", response_model=SecurityStatsResponse, tags=["Security Dashboard"])
async def get_security_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_roles([Role.ADMIN, Role.SUPER_ADMIN]))
):
    """
    Aggregates stats for the Security Operations Dashboard.
    """
    # Active users count
    user_res = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    active_users = user_res.scalar() or 0
    
    # Active IPs in whitelist count
    ip_res = await db.execute(select(func.count(IPWhitelist.id)))
    active_ips = ip_res.scalar() or 0
    
    # Failed logins count
    failed_login_res = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.action.in_(["CLIENT_LOGIN_FAILED", "ADMIN_LOGIN_FAILED"]))
    )
    failed_login_count = failed_login_res.scalar() or 0
    
    # Blocked IP attempts count
    blocked_ip_res = await db.execute(
        select(func.count(AuditLog.id)).where(AuditLog.action == "IP_BLOCKED")
    )
    blocked_ip_count = blocked_ip_res.scalar() or 0
    
    # Recent security events (e.g. failures, blocks, whitelist updates)
    events_stmt = select(AuditLog).where(
        AuditLog.action.in_([
            "CLIENT_LOGIN_FAILED", "ADMIN_LOGIN_FAILED", "IP_BLOCKED",
            "IP_WHITELIST_ADD", "IP_WHITELIST_REMOVE",
            "REPORT_DECRYPTION_FAILED", "REPORT_DECRYPTION_SUCCESS"
        ])
    ).order_by(AuditLog.created_at.desc()).limit(15)
    
    events_res = await db.execute(events_stmt)
    events = events_res.scalars().all()
    
    recent_events = [
        SecurityEventResponse(
            id=str(evt.id),
            timestamp=evt.created_at.isoformat(),
            username=evt.username,
            role=evt.role,
            action=evt.action,
            details=evt.details or "",
            ip_address=evt.ip_address
        ) for evt in events
    ]
    
    # API Usage Statistics
    api_usage_res = await db.execute(
        select(GatewayRequestLog.request_status, func.count(GatewayRequestLog.id))
        .group_by(GatewayRequestLog.request_status)
    )
    api_usage_statistics = {row[0]: row[1] for row in api_usage_res.all()}
    
    # Active Sessions (Simplified mock matching active users for demo)
    active_sessions = active_users
    
    return SecurityStatsResponse(
        active_users=active_users,
        active_ips=active_ips,
        failed_login_count=failed_login_count,
        blocked_ip_count=blocked_ip_count,
        active_sessions=active_sessions,
        api_usage_statistics=api_usage_statistics,
        recent_events=recent_events
    )
