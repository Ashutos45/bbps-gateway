from fastapi import FastAPI, Request, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logger import setup_logger
from app.core.exceptions import BBPSBaseException, FavoriteBillerException
from app.database.db import engine, Base, AsyncSessionLocal
from app.api.health import router as health_router
from app.api.fetch_bill import router as fetch_bill_router
from app.api.pay_bill import router as pay_bill_router
from app.api.favorite_biller import router as favorite_biller_router
from app.api.prepaid_plans import router as prepaid_plans_router
from app.api.biller_master import router as biller_master_router
from app.api.oneview import router as oneview_router
from app.api.reconciliation import router as reconciliation_router
from app.api.telemetry import router as telemetry_router
from app.api.auth import router as auth_router
from app.api.download_router import router as download_router
from app.api.stream_router import router as stream_router
from app.api.demo_router import router as demo_router, router_root as demo_root_router
from app.api.hmac_probe_router import router as hmac_probe_router
from app.core.middleware import HMACSecurityMiddleware, IPWhitelistingMiddleware, GatewayRoutingMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from app.workers.reconciliation_worker import ReconciliationWorker
from app.workers.ambiguous_state_worker import AmbiguousStateWorker
from app.workers.retry_worker import RetryWorker
from app.workers.file_generation_worker import FileGenerationWorker
from sqlalchemy import text, select, func
from loguru import logger
from app.database.models import Biller, User
from app.auth.auth_middleware import require_roles
from app.auth.role_manager import Role
import uuid
from datetime import datetime, timezone

# Setup centralized logging
setup_logger()

# Database initialization helper
async def initialize_database():
    """Create tables and seed test billers if needed"""
    try:
        # Create all tables
        logger.info("Creating database tables if they don't exist...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
        
        # Check if billers already exist
        async with AsyncSessionLocal() as session:
            existing = await session.execute(select(func.count(Biller.id)))
            count = existing.scalar() or 0
            
            if count == 0:
                logger.info("Seeding test billers into database...")
                test_billers = [
                    {
                        "biller_id": "MOCKEDU00001NAT",
                        "biller_name": "National Education Services 1",
                        "category": "Education",
                        "region": "National",
                        "biller_metadata": {
                            "state": "National",
                            "city": "National",
                            "support_email": "support_1@nationaleduc.in",
                            "support_phone": "918051802512",
                            "payment_modes": ["DebitCard", "NetBanking"],
                            "min_amount": "5.00",
                            "max_amount": "500000.00",
                            "active_status": "ACTIVE",
                            "provider_latency_ms": 1058,
                            "failure_probability": 0.0482
                        }
                    },
                    {
                        "biller_id": "MOCKTEL00002RAJ",
                        "biller_name": "Rajasthan Telecom Board 2",
                        "category": "Telecom",
                        "region": "North",
                        "biller_metadata": {
                            "state": "Rajasthan",
                            "city": "Jaipur",
                            "support_email": "support_2@rajasthantel.in",
                            "support_phone": "919410529190",
                            "payment_modes": ["UPI", "CreditCard"],
                            "min_amount": "5.00",
                            "max_amount": "50000.00",
                            "active_status": "ACTIVE",
                            "provider_latency_ms": 121,
                            "failure_probability": 0.0162
                        }
                    },
                    {
                        "biller_id": "MOCKWAT00004WES",
                        "biller_name": "West Bengal Water Board 4",
                        "category": "Water",
                        "region": "East",
                        "biller_metadata": {
                            "state": "West Bengal",
                            "city": "Durgapur",
                            "support_email": "support_4@westbengalwa.in",
                            "support_phone": "919699987374",
                            "payment_modes": ["NetBanking", "UPI", "CreditCard", "DebitCard"],
                            "min_amount": "50.00",
                            "max_amount": "10000.00",
                            "active_status": "ACTIVE",
                            "provider_latency_ms": 216,
                            "failure_probability": 0.0223
                        }
                    },
                    {
                        "biller_id": "MOCKGAS00006JHA",
                        "biller_name": "Jharkhand Gas Board 6",
                        "category": "Gas",
                        "region": "East",
                        "biller_metadata": {
                            "state": "Jharkhand",
                            "city": "Kolkata",
                            "support_email": "support_6@jharkhandgas.in",
                            "support_phone": "919748778024",
                            "payment_modes": ["DebitCard", "NetBanking", "UPI", "CreditCard"],
                            "min_amount": "50.00",
                            "max_amount": "500000.00",
                            "active_status": "ACTIVE",
                            "provider_latency_ms": 116,
                            "failure_probability": 0.0315
                        }
                    },
                    {
                        "biller_id": "MOCKELE00047ARU",
                        "biller_name": "Arunachal Pradesh Electricity Board 47",
                        "category": "Electricity",
                        "region": "NorthEast",
                        "biller_metadata": {
                            "state": "Arunachal Pradesh",
                            "city": "Ahmedabad",
                            "support_email": "support_47@arunachalpra.in",
                            "support_phone": "917453285987",
                            "payment_modes": ["NetBanking", "UPI", "DebitCard"],
                            "min_amount": "10.00",
                            "max_amount": "100000.00",
                            "active_status": "ACTIVE",
                            "provider_latency_ms": 161,
                            "failure_probability": 0.0227
                        }
                    }
                ]
                
                for biller_data in test_billers:
                    biller = Biller(
                        id=uuid.uuid4(),
                        biller_id=biller_data["biller_id"],
                        biller_name=biller_data["biller_name"],
                        category=biller_data["category"],
                        region=biller_data["region"],
                        biller_metadata=biller_data["biller_metadata"],
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(biller)
                
                await session.commit()
                logger.info(f"Successfully seeded {len(test_billers)} test billers")
            else:
                logger.info(f"Database already contains {count} billers. Skipping seeding.")

        # Seed default users
        async with AsyncSessionLocal() as session:
            existing_users = await session.execute(select(func.count(User.id)))
            user_count = existing_users.scalar() or 0
            
            if user_count == 0:
                logger.info("Seeding default users into database...")
                from app.utils.security import get_password_hash
                
                default_users = [
                    {"username": "admin", "password": "admin123", "role": Role.ADMIN, "email": "admin@bbps.com"},
                    {"username": "operator", "password": "operator123", "role": Role.OPERATOR, "email": "operator@bbps.com"},
                    {"username": "client", "password": "client123", "role": Role.CLIENT, "email": "client@bbps.com"},
                    {"username": "auditor", "password": "auditor123", "role": Role.AUDITOR, "email": "auditor@bbps.com"}
                ]
                for user_data in default_users:
                    new_user = User(
                        username=user_data["username"],
                        email=user_data["email"],
                        hashed_password=get_password_hash(user_data["password"]),
                        role=user_data["role"]
                    )
                    session.add(new_user)
                await session.commit()
                logger.info(f"Successfully seeded {len(default_users)} default users.")
            else:
                logger.info(f"Database already contains {user_count} users. Skipping user seeding.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

# Define Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup Actions: Initialize database
    logger.info("Starting database initialization...")
    await initialize_database()
    
    # 2. Startup Actions: Verify DB connection with retries
    logger.info("Verifying PostgreSQL database connection connectivity...")
    import asyncio
    max_retries = 5
    retry_delay = 3
    connected = False
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            connected = True
            logger.info("Successfully established connection with PostgreSQL database.")
            break
        except Exception as e:
            logger.warning(f"Database connection verification attempt {attempt} failed: {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay *= 1.5
            
    if not connected:
        logger.critical("Database connection connectivity verification failed after all attempts.")


    # 3. Startup Actions: Initialize and start background workers
    recon_worker = ReconciliationWorker()
    ambig_worker = AmbiguousStateWorker()
    retry_worker = RetryWorker()
    
    recon_worker.start()
    ambig_worker.start()
    retry_worker.start()
    FileGenerationWorker.start()

    yield

    # 4. Shutdown Actions: Stop background workers
    logger.info("Stopping background workers...")
    await recon_worker.stop()
    await ambig_worker.stop()
    await retry_worker.stop()
    await FileGenerationWorker.stop()
    logger.info("All background workers stopped cleanly.")


# Initialize FastAPI App
app = FastAPI(
    title="BBPS COU Integration System",
    description="Production-grade API gateway interfacing with Bank of Baroda BBPS Customer Operating Unit (COU).",
    version="4.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENV == "production" or request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Register middleware (executed in reverse order: IPWhitelisting -> GatewayRouting -> HMACSecurity)
app.add_middleware(HMACSecurityMiddleware)
app.add_middleware(GatewayRoutingMiddleware)
app.add_middleware(IPWhitelistingMiddleware)

# Custom Swagger UI route with sleek enterprise dark mode
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    from fastapi.responses import HTMLResponse
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title="Enterprise BBPS Gateway Portal",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
    )
    custom_style = """
    <style>
    .swagger-ui .topbar { background-color: #0b0f19; border-bottom: 2px solid #1e293b; }
    body { background-color: #0b0f19 !important; color: #f8fafc; font-family: 'Outfit', 'Inter', sans-serif; }
    .swagger-ui .info .title { color: #38bdf8; font-weight: 800; font-family: 'Outfit', sans-serif; }
    .swagger-ui .info p, .swagger-ui .info li, .swagger-ui .info td, .swagger-ui .info th { color: #94a3b8; }
    .swagger-ui .scheme-container { background-color: #0f172a; box-shadow: none; border: 1px solid #1e293b; border-radius: 8px; }
    .swagger-ui .opblock { border-radius: 8px; border: 1px solid #1e293b; background: #0f172a !important; }
    .swagger-ui .opblock .opblock-summary { border-bottom: 1px solid #1e293b; }
    .swagger-ui .opblock .opblock-summary-path { font-weight: 600; color: #e2e8f0; }
    .swagger-ui input[type=text], .swagger-ui select { background: #0f172a; color: #f8fafc; border: 1px solid #1e293b; border-radius: 6px; }
    .swagger-ui .btn { background: #1e293b; color: #f8fafc; border: 1px solid #1e293b; border-radius: 6px; }
    .swagger-ui .btn:hover { background: #334155; color: #ffffff; }
    .swagger-ui .model-box { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; color: #94a3b8; }
    .swagger-ui th { color: #38bdf8; }
    .swagger-ui table thead tr td, .swagger-ui table thead tr th { border-bottom: 1px solid #1e293b; }
    .swagger-ui .opblock-description-wrapper p, .swagger-ui .opblock-external-docs-wrapper p, .swagger-ui .opblock-title_normal p { color: #94a3b8; }
    .swagger-ui .model-title { color: #38bdf8; }
    .swagger-ui .prop-name { color: #f8fafc; }
    .swagger-ui .prop-type { color: #38bdf8; }
    .swagger-ui .response-col_status { color: #38bdf8; font-weight: bold; }
    .swagger-ui .tabli button { color: #f8fafc; }
    </style>
    """
    html_content = response.body.decode("utf-8")
    html_content = html_content.replace("</head>", f"{custom_style}</head>")
    return HTMLResponse(content=html_content, status_code=response.status_code)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Response-Signature", "Content-Length", "X-Trace-Id"]
)

# Root path endpoint
@app.get("/", tags=["Framework"])
async def root():
    return {
        "platform": "Enterprise BBPS Gateway",
        "status": "running"
    }

# Include routers
app.include_router(health_router)
app.include_router(fetch_bill_router, prefix="/BOBCOU/BBPS", dependencies=[Depends(require_roles([Role.CLIENT]))])
app.include_router(pay_bill_router, prefix="/BOBCOU/BBPS", dependencies=[Depends(require_roles([Role.CLIENT]))])
app.include_router(favorite_biller_router, prefix="/BOBCOU/BBPS", dependencies=[Depends(require_roles([Role.CLIENT]))])
app.include_router(prepaid_plans_router, prefix="/BOBCOU/BBPS", dependencies=[Depends(require_roles([Role.CLIENT]))])
app.include_router(stream_router)
app.include_router(biller_master_router, prefix="/BOBCOU/BBPS")
app.include_router(oneview_router, prefix="/BOBCOU/BBPS", dependencies=[Depends(require_roles([Role.CLIENT]))])
app.include_router(reconciliation_router, prefix="/BOBCOU/BBPS", dependencies=[Depends(require_roles([Role.OPERATOR]))])
app.include_router(telemetry_router, dependencies=[Depends(require_roles([Role.ADMIN, Role.AUDITOR]))])
app.include_router(auth_router)
app.include_router(download_router)
app.include_router(demo_router)
app.include_router(demo_root_router)
app.include_router(hmac_probe_router)


# Custom OpenAPI schema simplification to hide internal/cluttered fields in Swagger
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Enterprise BBPS Gateway Portal",
        version="4.0.0",
        description="Production-grade API gateway interfacing with Bank of Baroda BBPS Customer Operating Unit (COU).",
        routes=app.routes,
    )
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    
    # 1. FetchBillRequest Schema simplification
    if "FetchBillRequest" in schemas:
        schemas["FetchBillRequest"]["properties"] = {
            "billerid": {
                "title": "Billerid",
                "type": "string",
                "description": "Unique Biller Identifier (e.g. MOCKELE00125MAH)"
            },
            "billeraccountid": {
                "title": "Billeraccountid",
                "type": "string",
                "description": "Biller account/consumer number (e.g. ELEC987654321)"
            }
        }
        schemas["FetchBillRequest"]["required"] = ["billerid", "billeraccountid"]

    # 2. PayBillRequest Schema simplification
    if "PayBillRequest" in schemas:
        schemas["PayBillRequest"]["properties"] = {
            "validationid": {
                "title": "Validationid",
                "type": "string",
                "description": "Validation ID retrieved from Fetch Bill response"
            },
            "payment_method": {
                "title": "Payment Method",
                "type": "string",
                "default": "CARD",
                "description": "Payment method (e.g. CARD, UPI, NETBANKING)"
            }
        }
        schemas["PayBillRequest"]["required"] = ["validationid"]

    # 3. FavoriteBillerAddRequest Schema simplification
    if "FavoriteBillerAddRequest" in schemas:
        schemas["FavoriteBillerAddRequest"]["properties"] = {
            "billerid": {
                "title": "Billerid",
                "type": "string",
                "description": "Unique Biller Identifier"
            }
        }
        schemas["FavoriteBillerAddRequest"]["required"] = ["billerid"]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# Exception Handlers

@app.exception_handler(BBPSBaseException)
async def bbps_base_exception_handler(request: Request, exc: BBPSBaseException):
    trace_id = request.headers.get("X-Trace-Id", "trace-not-found")
    logger.warning(f"BBPS Base Exception: [{exc.error_code}] {exc.message} (Trace: {trace_id})")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_dict(trace_id)
    )

@app.exception_handler(FavoriteBillerException)
async def favorite_biller_exception_handler(request: Request, exc: FavoriteBillerException):
    trace_id = request.headers.get("X-Trace-Id", "trace-not-found")
    logger.warning(f"Favorite Biller Exception: {exc.status_description} (Trace: {trace_id})")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_dict(trace_id)
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    trace_id = request.headers.get("X-Trace-Id", "trace-not-found")
    logger.error(f"Pydantic Validation Error: {exc.errors()} (Trace: {trace_id})")
    
    error_msg = "; ".join([f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}" for err in exc.errors()])
    return JSONResponse(
        status_code=400,
        content={
            "status": 400,
            "error_type": "request_validation_error",
            "error_code": "ERR_VALIDATION_FAILED",
            "message": f"Input validation failed: {error_msg}",
            "metadata": [{"name": "traceId", "value": trace_id}]
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    trace_id = request.headers.get("X-Trace-Id", "trace-not-found")
    logger.exception(f"Unhandled system error occurred: {exc} (Trace: {trace_id})")
    return JSONResponse(
        status_code=500,
        content={
            "status": 500,
            "error_type": "internal_server_error",
            "error_code": "ERR_INTERNAL_SERVER",
            "message": "An unexpected internal server error occurred.",
            "metadata": [{"name": "traceId", "value": trace_id}]
        }
    )
