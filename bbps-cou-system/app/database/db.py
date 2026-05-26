from sqlalchemy import create_engine, Column, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from app.core.config import settings

# Declare Declarative Base for models
Base = declarative_base()

# Configure SQLite Database Engine
# Note: check_same_thread=False is required for SQLite in multithreaded environments like FastAPI
DATABASE_URL = settings.DATABASE_URL
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# Session factory for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get db session in API routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Transaction Logging Model
class TransactionLog(Base):
    __tablename__ = "transaction_logs"

    trace_id = Column(String(50), primary_key=True, index=True, doc="Unique identifier for the transaction request")
    customer_id = Column(String(50), nullable=True, index=True, doc="Customer ID associated with the bill payment")
    biller_id = Column(String(50), nullable=True, index=True, doc="Biller ID targeted in the transaction")
    amount = Column(Float, nullable=True, doc="Total payment/debit amount")
    request_payload = Column(Text, nullable=True, doc="Raw request body or arguments sent to downstream COU")
    response_payload = Column(Text, nullable=True, doc="Raw response received from downstream COU")
    status = Column(String(20), nullable=False, doc="Current status: INITIATED, SUCCESS, FAILED")
    created_at = Column(DateTime, default=datetime.utcnow, doc="Timestamp when log entry was created")

def init_db():
    """
    Initializes the database tables (creates them if they do not exist).
    In production, this would be managed via Alembic migrations.
    """
    Base.metadata.create_all(bind=engine)
