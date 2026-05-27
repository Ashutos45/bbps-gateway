import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database.db import Base

class TransactionLog(Base):
    __tablename__ = "transaction_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(String(50), index=True, nullable=True)
    biller_id = Column(String(50), index=True, nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)
    transaction_state = Column(String(30), index=True, nullable=False)  # INITIALIZED, PENDING_SUBMISSION, NETWORK_IN_FLIGHT, AMBIGUOUS_TIMEOUT, SETTLED, FAILED
    request_payload = Column(JSONB, nullable=True)
    response_payload = Column(JSONB, nullable=True)
    retry_attempts = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    worker_last_execution = Column(DateTime(timezone=True), nullable=True)
    reconciliation_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class NonceRegistry(Base):
    __tablename__ = "nonce_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nonce = Column(String(255), unique=True, index=True, nullable=False)
    source_id = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PaymentIdempotency(Base):
    __tablename__ = "payment_idempotency"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)
    payment_reference = Column(String(100), unique=True, nullable=False)
    transaction_status = Column(String(30), nullable=False)  # e.g., PENDING, SUCCESS, FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ReconciliationLog(Base):
    __tablename__ = "reconciliation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(50), index=True, nullable=False)
    polling_attempts = Column(Integer, default=0, nullable=False)
    resolved_state = Column(String(30), nullable=True)
    reconciliation_status = Column(String(30), nullable=False)  # e.g., PENDING, RESOLVED, UNRESOLVED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Biller(Base):
    __tablename__ = "billers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    biller_id = Column(String(50), unique=True, index=True, nullable=False)
    biller_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    biller_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class FavoriteBiller(Base):
    __tablename__ = "favorite_billers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    billeraccountid = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(String(50), index=True, nullable=False)
    biller_id = Column(String(50), index=True, nullable=False)
    short_name = Column(String(100), nullable=False)
    authenticators = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False)  # ACTIVE, DELETED
    registration_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deletion_date = Column(DateTime(timezone=True), nullable=True)
    autopay_status = Column(String(1), default="N")  # Y, N
    autopay_start_date = Column(DateTime(timezone=True), nullable=True)
    autopay_end_date = Column(DateTime(timezone=True), nullable=True)
    autopay_amount = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), default="356")
    frequency = Column(String(20), nullable=True)
    payment_account = Column(JSONB, nullable=True)
    cprn = Column(String(50), nullable=True)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)  # SUPER_ADMIN, ADMIN, CLIENT, AUDITOR, OPERATIONS
    is_active = Column(Boolean, default=True, nullable=False)
    organization = Column(String(100), nullable=True)
    company = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AdminAccessKey(Base):
    __tablename__ = "admin_access_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), index=True, nullable=False)
    role = Column(String(30), nullable=False)
    action = Column(String(100), nullable=False)
    details = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

