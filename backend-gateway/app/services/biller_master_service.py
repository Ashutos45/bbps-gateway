import os
import json
import zipfile
import base64
import uuid
import asyncio
import httpx
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.repositories.biller_repository import BillerRepository
from app.core.exceptions import BillerNotFoundError, BBPSBaseException
from app.workers.file_generation_worker import FileGenerationWorker
from loguru import logger

# Directory to store the zip archives
BILLER_DIR = "biller_list"

MOCK_BILLERS = [
    {"biller_id": "UPPCL0000UTP01", "biller_name": "Uttar Pradesh Power Corp Ltd - URBAN", "category": "Electricity", "region": "Uttar Pradesh", "metadata": {"min_amount": "10.00", "max_amount": "50000.00"}},
    {"biller_id": "UPPCL0000UTP02", "biller_name": "Uttar Pradesh Power Corp Ltd - RURAL", "category": "Electricity", "region": "Uttar Pradesh", "metadata": {"min_amount": "5.00", "max_amount": "20000.00"}},
    {"biller_id": "AVVNL0000RAJ01", "biller_name": "Ajmer Vidyut Vitran Nigam Ltd", "category": "Electricity", "region": "Rajasthan", "metadata": {"min_amount": "10.00", "max_amount": "100000.00"}},
    {"biller_id": "BESL00000WB01", "biller_name": "Calcutta Electric Supply Corporation", "category": "Electricity", "region": "West Bengal", "metadata": {"min_amount": "1.00", "max_amount": "200000.00"}},
    {"biller_id": "BSNL00000NATHL", "biller_name": "BSNL Landline", "category": "Landline Postpaid", "region": "National", "metadata": {"min_amount": "5.00", "max_amount": "10000.00"}},
    {"biller_id": "AIRT00000NAT87", "biller_name": "Airtel DTH", "category": "DTH", "region": "National", "metadata": {"min_amount": "10.00", "max_amount": "15000.00"}},
    {"biller_id": "TSTO00000NAT01", "biller_name": "Tata Play DTH", "category": "DTH", "region": "National", "metadata": {"min_amount": "20.00", "max_amount": "20000.00"}},
    {"biller_id": "DISHTV000NAT01", "biller_name": "Dish TV", "category": "DTH", "region": "National", "metadata": {"min_amount": "10.00", "max_amount": "25000.00"}},
    {"biller_id": "MGL000000MUM01", "biller_name": "Mahanagar Gas Limited", "category": "Gas", "region": "Maharashtra", "metadata": {"min_amount": "1.00", "max_amount": "10000.00"}},
    {"biller_id": "IGL000000DEL01", "biller_name": "Indraprastha Gas Limited", "category": "Gas", "region": "Delhi", "metadata": {"min_amount": "10.00", "max_amount": "30000.00"}},
]

# Generate 40 additional operators to complete 50+ operators
for i in range(1, 41):
    state = ["Maharashtra", "Karnataka", "Tamil Nadu", "Delhi", "Telangana", "Kerala", "Gujarat"][i % 7]
    category = ["Electricity", "Water", "Gas", "LPG Gas", "Mobile Postpaid", "Broadband"][i % 6]
    biller_id = f"MOCK{category[:3].upper()}{i:03d}{state[:3].upper()}"
    MOCK_BILLERS.append({
        "biller_id": biller_id,
        "biller_name": f"{state} {category} Board {i}",
        "category": category,
        "region": state,
        "metadata": {"min_amount": "5.00", "max_amount": "50000.00"}
    })

class BillerMasterService:
    """
    Handles Biller File Generation and Biller Master downloads.
    """

    @staticmethod
    async def initiate_file_generation(
        session: AsyncSession,
        source_id: str,
        callback_url: str
    ) -> Dict[str, Any]:
        file_id = f"HGA{str(uuid.uuid4().int)[:12]}"
        logger.info(f"Initiating Biller File Generation for channel '{source_id}'. Generated File ID: {file_id}")
        
        # Seed billers into PostgreSQL database asynchronously
        await BillerRepository.seed_billers(session, MOCK_BILLERS)
        await session.commit()

        # Delegate enqueuing task to FileGenerationWorker
        FileGenerationWorker.enqueue_task(file_id, callback_url)

        return {
            "objectid": "file",
            "fileid": file_id,
            "file_status": "INPROCESS",
            "callback_url": callback_url
        }

    @staticmethod
    async def get_file_archive(file_id: str) -> Dict[str, Any]:
        logger.info(f"Retrieving Biller Master File zip for File ID: {file_id}")
        
        # Check in-memory task status registry first
        status_data = FileGenerationWorker.get_task_status(file_id)
        if status_data.get("status") == "INPROCESS":
            return {
                "status": "INPROCESS",
                "progress": status_data.get("progress", 0),
                "message": "File generation is currently in progress."
            }
        elif status_data.get("status") == "FAILED":
            return {
                "status": "FAILED",
                "progress": 0,
                "message": "File generation failed."
            }

        zip_path = os.path.join(BILLER_DIR, f"{file_id}.zip")
        if not os.path.exists(zip_path):
            logger.warning(f"Biller Master File not found on filesystem: {zip_path}")
            raise BillerNotFoundError(f"Biller master file '{file_id}' not found.")

        try:
            with open(zip_path, "rb") as f:
                zip_bytes = f.read()
            base64_content = base64.b64encode(zip_bytes).decode("utf-8")
        except Exception as e:
            logger.exception(f"Error encoding file '{zip_path}': {e}")
            raise BBPSBaseException(status_code=500, message="Error reading zip file archive.")

        return {
            "status": 0,
            "message": "Successfully fetched the zipped file",
            "filePath": f"biller_list/{file_id}.zip",
            "fileName": f"{file_id}.zip",
            "fileContent": base64_content
        }
