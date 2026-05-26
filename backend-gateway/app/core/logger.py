import sys
import os
from loguru import logger
from app.core.config import settings

def setup_logger():
    """
    Sets up Loguru logger with outputs to stdout and logs/app.log.
    """
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console Handler (With color formatting)
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG
    )

    # File Handler (For production logs)
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="30 days",
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
        backtrace=True,
        diagnose=settings.DEBUG,
        compression="zip"
    )

    logger.info("Centralized logging configured for Backend Gateway.")
