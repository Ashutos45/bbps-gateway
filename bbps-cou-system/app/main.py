from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logger import setup_logger
from app.core.exceptions import (
    BBPSBaseException,
    FavoriteBillerException
)

from app.database.db import init_db
from app.api.health import router as health_router

from loguru import logger

# =========================================================
# LOGGER SETUP
# =========================================================

setup_logger()

# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="BBPS COU Integration System",
    description="Production-grade API gateway interfacing with Bank of Baroda BBPS Customer Operating Unit (COU).",
    version="4.0.0",
    debug=settings.DEBUG,
    docs_url="/docs",
    redoc_url="/redoc"
)

# =========================================================
# STARTUP EVENT
# =========================================================

@app.on_event("startup")
async def startup_event():

    logger.info("Initializing BBPS database...")

    try:
        init_db()
        logger.success("Database initialized successfully.")

    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
        raise e

# =========================================================
# ROUTERS
# =========================================================

app.include_router(health_router)

# =========================================================
# ROOT ENDPOINT
# =========================================================

@app.get("/")
async def root():
    return {
        "platform": "BBPS COU Integration System",
        "status": "ONLINE",
        "version": "4.0.0"
    }

# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "BBPS Gateway",
        "version": "4.0.0"
    }

# =========================================================
# REQUEST VALIDATION ERROR
# =========================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):

    trace_id = request.headers.get(
        "BD-Traceid",
        "trace-not-found"
    )

    logger.error(
        f"Validation Error: {exc.errors()} | Trace: {trace_id}"
    )

    return JSONResponse(
        status_code=400,
        content={
            "status": 400,
            "error_type": "request_validation_error",
            "error_code": "ERR_VALIDATION_FAILED",
            "message": "Input validation failed.",
            "trace_id": trace_id,
            "details": exc.errors()
        }
    )

# =========================================================
# BBPS BASE EXCEPTION
# =========================================================

@app.exception_handler(BBPSBaseException)
async def bbps_exception_handler(
    request: Request,
    exc: BBPSBaseException
):

    trace_id = request.headers.get(
        "BD-Traceid",
        "trace-not-found"
    )

    logger.warning(
        f"BBPS Exception: {exc.message} | Trace: {trace_id}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_dict(trace_id)
    )

# =========================================================
# FAVORITE BILLER EXCEPTION
# =========================================================

@app.exception_handler(FavoriteBillerException)
async def favorite_biller_exception_handler(
    request: Request,
    exc: FavoriteBillerException
):

    trace_id = request.headers.get(
        "BD-Traceid",
        "trace-not-found"
    )

    logger.warning(
        f"Favorite Biller Exception | Trace: {trace_id}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_dict(trace_id)
    )

# =========================================================
# GLOBAL FALLBACK EXCEPTION
# =========================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    trace_id = request.headers.get(
        "BD-Traceid",
        "trace-not-found"
    )

    logger.exception(
        f"Unhandled Exception: {exc} | Trace: {trace_id}"
    )

    return JSONResponse(
        status_code=500,
        content={
            "status": 500,
            "error_type": "internal_server_error",
            "error_code": "ERR_INTERNAL_SERVER",
            "message": "Unexpected internal server error occurred.",
            "trace_id": trace_id
        }
    )