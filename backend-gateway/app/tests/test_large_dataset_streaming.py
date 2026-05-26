import pytest
import os
import sys
import csv
import zipfile
import subprocess
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.db import AsyncSessionLocal, engine
from app.database.models import Biller
from sqlalchemy import select, func, delete

# Standard API key for testing CLIENT access
TEST_CLIENT_API_KEY = "client_key_123"
TEST_ADMIN_API_KEY = "admin_key_123"

@pytest.mark.asyncio
async def test_dataset_generation_and_seeding():
  """
  Tests generating 10,000 mock billers via scripts and bulk database seeding.
  """
  await engine.dispose()
  csv_file = "test_mock_billers.csv"
  if os.path.exists(csv_file):
    os.remove(csv_file)

  # 1. Run mock generator CLI script (generate 10,005 records for thorough check)
  logger_output = subprocess.run(
    [sys.executable, "scripts/generate_mock_billers.py", "--count", "10005", "--output", csv_file, "--seed", "42"],
    capture_output=True,
    text=True
  )
  assert logger_output.returncode == 0
  assert os.path.exists(csv_file)

  # 2. Validate CSV layout columns
  with open(csv_file, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    headers = next(reader)
    assert headers[0] == "biller_id"
    assert headers[1] == "biller_name"
    assert "provider_latency_ms" in headers
    
    rows = list(reader)
    assert len(rows) == 10005

  # 3. Clean database billers table before seeding
  async with AsyncSessionLocal() as session:
    async with session.begin():
      await session.execute(delete(Biller))

  # 4. Execute seeding script
  seeding_output = subprocess.run(
    [sys.executable, "scripts/seed_billers.py"],
    env={**os.environ, "SEED_CSV_PATH": csv_file, "PYTHONPATH": "."},
    capture_output=True,
    text=True
  )
  assert seeding_output.returncode == 0

  # 5. Assert PostgreSQL bulk seed success count
  async with AsyncSessionLocal() as session:
    res = await session.execute(select(func.count(Biller.id)))
    count = res.scalar() or 0
    assert count == 10005

  # Clean up test csv file
  if os.path.exists(csv_file):
    os.remove(csv_file)

@pytest.mark.asyncio
async def test_low_memory_database_csv_streaming():
  """
  Tests chunked, iterator-based database streaming.
  Ensures that client downloads all 10,000+ records line-by-line successfully.
  """
  await engine.dispose()
  try:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
      # Request database streaming with Client API Key header
      url = "/BOBCOU/BBPS/mbanking/billpay/billers/stream"
      headers = {"X-API-Key": TEST_CLIENT_API_KEY}
      
      lines_count = 0
      has_header = False
      
      # Use httpx stream to download line-by-line to prevent high RAM allocation
      async with ac.stream("GET", url, headers=headers) as response:
        assert response.status_code == 200
        assert response.headers.get("content-type") == "text/csv; charset=utf-8"
        
        async for line in response.aiter_lines():
          if not line.strip():
            continue
          if not has_header:
            assert "biller_id" in line
            has_header = True
          else:
            lines_count += 1

      # Verify we streamed exactly all 10,005 seeded records
      assert lines_count == 10005
  finally:
    await engine.dispose()

@pytest.mark.asyncio
async def test_zip_generation_and_export():
  """
  Tests async ZIP file generation containing both JSON and CSV files,
  and validates secure download urls.
  """
  await engine.dispose()
  try:
    from app.workers.file_generation_worker import FileGenerationWorker
    from app.tests.test_resilience import generate_signed_headers
    FileGenerationWorker.start()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
      # 1. Trigger export (Requires ADMIN API Key)
      url_init = "/BOBCOU/BBPS/mbanking/billpay/billers/file"
      body = {"callbackUrl": "http://localhost:8000/callback/file"}
      
      payload_bytes = ac.build_request("POST", url_init, json=body).content
      headers = generate_signed_headers(payload_bytes, "mbanking")
      headers["X-API-Key"] = TEST_ADMIN_API_KEY

      res_init = await ac.post(url_init, json=body, headers=headers)
      assert res_init.status_code == 200
      data = res_init.json()
      file_id = data["fileid"]
      assert file_id is not None

      # 2. Wait for async background queue generation to complete
      url_status = f"/BOBCOU/BBPS/mbanking/billpay/billers/file/{file_id}"
      max_retries = 20
      completed = False
      status_data = {}
      for _ in range(max_retries):
        headers_status = generate_signed_headers(b"", "mbanking")
        headers_status["X-API-Key"] = TEST_ADMIN_API_KEY
        res_status = await ac.get(url_status, headers=headers_status)
        assert res_status.status_code == 200
        status_data = res_status.json()
        if status_data.get("status") == 0:
          completed = True
          break
        await asyncio.sleep(0.5)

      assert completed, f"File compilation did not complete in time: {status_data}"
      assert "downloadUrl" in status_data
      download_url = status_data["downloadUrl"]
      
      # 4. Stream and download the zipped archive using the signed URL
      # Download URL bypasses regular route prefix and security middleware
      # We extract the relative path and token param
      path_part, token_query = download_url.split("?")
      token_val = token_query.split("=")[1]
      
      download_endpoint = f"/download/file/{file_id}"
      res_download = await ac.get(download_endpoint, params={"token": token_val})
      assert res_download.status_code == 200
      assert res_download.headers.get("content-type") == "application/zip"

      # Save file locally to test zip integrity
      test_zip_path = f"{file_id}_test.zip"
      with open(test_zip_path, "wb") as f:
        f.write(res_download.content)

      # Assert zip archive contains both JSON and CSV formats
      assert zipfile.is_zipfile(test_zip_path)
      with zipfile.ZipFile(test_zip_path, "r") as z:
        namelist = z.namelist()
        assert f"{file_id}.json" in namelist
        assert f"{file_id}.csv" in namelist

      # Cleanup ZIP artifact
      if os.path.exists(test_zip_path):
        os.remove(test_zip_path)
      zip_archive = f"biller_list/{file_id}.zip"
      if os.path.exists(zip_archive):
        os.remove(zip_archive)

    await FileGenerationWorker.stop()
  finally:
    await engine.dispose()
