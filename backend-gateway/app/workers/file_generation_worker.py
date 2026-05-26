import asyncio
import os
import json
import zipfile
import base64
import httpx
import time
from typing import Dict, Any
from app.services.telemetry_service import TelemetryService
from loguru import logger

# Directory for outputs
BILLER_DIR = "biller_list"

class FileGenerationWorker:
    """
    Background worker that queues and executes compilation of the Biller Master File ZIP.
    Exposes generation progress and status, remaining non-blocking to transactional APIs.
    """
    _queue = None
    # In-memory dictionary tracking file status and progress
    # file_id -> { "status": "INPROCESS" | "COMPLETED" | "FAILED", "progress": int, "fileName": str, "filePath": str }
    _status_registry: Dict[str, Dict[str, Any]] = {}
    _task = None
    _running = False

    @classmethod
    def _get_queue(cls) -> asyncio.Queue:
        if cls._queue is None:
            cls._queue = asyncio.Queue()
        return cls._queue

    @classmethod
    def start(cls) -> None:
        # Recreate task if not running or if previous task is done/cancelled
        if cls._running and cls._task and not cls._task.done():
            return
        cls._running = True
        # Always obtain queue in the context of the active loop
        cls._queue = None  # Force re-creation of Queue on new loop start
        cls._task = asyncio.create_task(cls._loop())
        logger.info("File Generation background worker started.")

    @classmethod
    async def stop(cls) -> None:
        if not cls._running:
            return
        cls._running = False
        if cls._task:
            cls._task.cancel()
            try:
                await cls._task
            except asyncio.CancelledError:
                pass
            cls._task = None
        cls._queue = None
        logger.info("File Generation background worker stopped.")

    @classmethod
    def enqueue_task(cls, file_id: str, callback_url: str) -> None:
        """
        Enqueues a compilation job and registers its initial progress.
        """
        cls._status_registry[file_id] = {
            "status": "INPROCESS",
            "progress": 0,
            "callback_url": callback_url,
            "fileName": None,
            "filePath": None
        }
        cls._get_queue().put_nowait((file_id, callback_url))
        logger.info(f"Encheued file generation task for File ID: {file_id}")

    @classmethod
    def get_task_status(cls, file_id: str) -> Dict[str, Any]:
        """
        Retrieves progress metadata for the specified file_id.
        """
        return cls._status_registry.get(file_id, {"status": "NOT_FOUND", "progress": 0})

    @classmethod
    async def _loop(cls) -> None:
        queue = cls._get_queue()
        while cls._running:
            try:
                # Wait for next enqueued file job
                file_id, callback_url = await queue.get()
                start_time = time.time()
                try:
                    await cls._process_generation(file_id, callback_url)
                except Exception as e:
                    logger.exception(f"Error compiling Biller File '{file_id}': {e}")
                    cls._status_registry[file_id]["status"] = "FAILED"
                finally:
                    queue.task_done()
                    duration_ms = (time.time() - start_time) * 1000.0
                    TelemetryService.record_worker_latency("file_generation_worker", duration_ms)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in FileGenerationWorker queue loop: {e}")
                await asyncio.sleep(1.0)

    @classmethod
    async def _process_generation(cls, file_id: str, callback_url: str) -> None:
        """
        Compiles the biller master lists, updates task progress, zip-compresses,
        and triggers callback.
        """
        logger.info(f"Processing file generation task for File ID: {file_id}")
        
        # 1. Update progress to 10%
        cls._status_registry[file_id]["progress"] = 10
        await asyncio.sleep(0.5)

        # Stream Biller records from PostgreSQL database in chunks to keep memory usage flat
        from app.database.db import AsyncSessionLocal
        from app.database.models import Biller
        from sqlalchemy import select
        import csv

        # 2. Update progress to 50%
        cls._status_registry[file_id]["progress"] = 50
        await asyncio.sleep(0.5)

        os.makedirs(BILLER_DIR, exist_ok=True)
        json_path = os.path.join(BILLER_DIR, f"{file_id}.json")
        csv_path = os.path.join(BILLER_DIR, f"{file_id}.csv")
        zip_path = os.path.join(BILLER_DIR, f"{file_id}.zip")

        # Open JSON and CSV files for chunked streaming writes
        json_file = open(json_path, "w", encoding="utf-8")
        json_file.write("[\n")

        csv_file = open(csv_path, "w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        
        csv_headers = [
            "biller_id", "biller_name", "category", "region", "state", "city", 
            "support_email", "support_phone", "payment_modes", "minimum_amount", 
            "maximum_amount", "active_status", "provider_latency_ms", "failure_probability", 
            "created_at"
        ]
        csv_writer.writerow(csv_headers)

        offset = 0
        limit = 1000
        is_first = True

        while True:
            async with AsyncSessionLocal() as session:
                stmt = select(Biller).offset(offset).limit(limit)
                res = await session.execute(stmt)
                chunk = res.scalars().all()
                if not chunk:
                    break

                for biller in chunk:
                    meta = biller.biller_metadata or {}
                    biller_dict = {
                        "biller_id": biller.biller_id,
                        "biller_name": biller.biller_name,
                        "category": biller.category,
                        "region": biller.region,
                        "state": meta.get("state", ""),
                        "city": meta.get("city", ""),
                        "support_email": meta.get("support_email", ""),
                        "support_phone": meta.get("support_phone", ""),
                        "payment_modes": meta.get("payment_modes", []),
                        "minimum_amount": meta.get("min_amount", "0.00"),
                        "maximum_amount": meta.get("max_amount", "0.00"),
                        "active_status": meta.get("active_status", "ACTIVE"),
                        "provider_latency_ms": meta.get("provider_latency_ms", 100),
                        "failure_probability": meta.get("failure_probability", 0.0),
                        "created_at": biller.created_at.isoformat() if biller.created_at else ""
                    }

                    # Write element to JSON array
                    if not is_first:
                        json_file.write(",\n")
                    json_file.write(json.dumps(biller_dict, indent=2))
                    is_first = False

                    # Write row to CSV
                    csv_writer.writerow([
                        biller.biller_id,
                        biller.biller_name,
                        biller.category,
                        biller.region,
                        meta.get("state", ""),
                        meta.get("city", ""),
                        meta.get("support_email", ""),
                        meta.get("support_phone", ""),
                        ";".join(meta.get("payment_modes", [])),
                        meta.get("min_amount", "0.00"),
                        meta.get("max_amount", "0.00"),
                        meta.get("active_status", "ACTIVE"),
                        meta.get("provider_latency_ms", 100),
                        meta.get("failure_probability", 0.0),
                        biller.created_at.isoformat() if biller.created_at else ""
                    ])

            offset += limit
            # Brief sleep to allow other tasks to run
            await asyncio.sleep(0.01)

        json_file.write("\n]\n")
        json_file.close()
        csv_file.close()

        # 3. Update progress to 75%
        cls._status_registry[file_id]["progress"] = 75
        await asyncio.sleep(0.5)

        # Compress both JSON and CSV files into ZIP archive
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(json_path, arcname=f"{file_id}.json")
            zip_file.write(csv_path, arcname=f"{file_id}.csv")

        # Clean up raw files
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(csv_path):
            os.remove(csv_path)

        # 4. Update status to COMPLETED and progress to 100%
        cls._status_registry[file_id].update({
            "status": "COMPLETED",
            "progress": 100,
            "fileName": f"{file_id}.zip",
            "filePath": f"biller_list/{file_id}.zip"
        })
        logger.info(f"Finished zip compilation for File ID: {file_id}")

        # 5. Fire callback notification
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                callback_payload = {
                    "objectid": "file",
                    "fileid": file_id,
                    "file_status": "COMPLETED",
                    "callback_url": callback_url,
                    "filePath": f"biller_list/{file_id}.zip",
                    "fileName": f"{file_id}.zip"
                }
                logger.info(f"Posting file completion callback to: {callback_url}")
                await client.post(callback_url, json=callback_payload)
        except Exception as e:
            logger.error(f"Callback delivery failed for File ID '{file_id}': {e}")
