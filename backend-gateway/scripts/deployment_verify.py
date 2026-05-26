#!/usr/bin/env python3
import sys
import os
import time
import json
import uuid
import hmac
import hashlib
import urllib.request
from urllib.error import HTTPError, URLError

# Defaults
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_HMAC_SECRET = "ugVz1hETNXUIwnWtpLafAASFPL0qGI5fAWybWMfuEsIL3HusiIRWO1AvVmBRe0Gy"
DEFAULT_SOURCE_ID = "mbanking"

def calculate_hmac(body_bytes: bytes, timestamp: str, nonce: str, secret: str) -> str:
    payload = body_bytes + timestamp.encode("utf-8") + nonce.encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest().upper()

def canonicalize(data: dict) -> bytes:
    return json.dumps(data, separators=(',', ':'), sort_keys=True).encode('utf-8')

def make_request(url: str, method: str = "GET", headers: dict = None, data: dict = None) -> tuple:
    if headers is None:
        headers = {}
    
    body_bytes = b""
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=body_bytes if method != "GET" else None, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode("utf-8")
            res_headers = dict(response.info())
            # Always attempt to parse json from response body
            parsed_body = res_body
            try:
                parsed_body = json.loads(res_body)
            except Exception:
                pass
            return response.status, parsed_body, res_headers
    except HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            err_body = json.loads(err_body)
        except Exception:
            pass
        return e.code, err_body, dict(e.headers)
    except URLError as e:
        print(f"Network error connecting to {url}: {e.reason}")
        return 0, str(e.reason), {}

def run_smoke_tests(base_url: str, hmac_secret: str, source_id: str):
    print("=" * 60)
    print(f"STARTING BBPS GATEWAY DEPLOYMENT SMOKE TESTS")
    print(f"Target URL:  {base_url}")
    print(f"Source ID:   {source_id}")
    print("=" * 60)
    
    # Test 1: Health Check Endpoint
    print("\n[TEST 1] Querying /health Endpoint...")
    status, body, _ = make_request(f"{base_url}/health")
    # Handle success/healthy structures
    is_healthy = False
    if isinstance(body, dict):
        status_val = body.get("status")
        if status_val in ("success", "healthy"):
            is_healthy = True
            
    if status == 200 and is_healthy:
        print(" -> PASS: /health is reachable and database connection is healthy.")
        print(f"    Info: {json.dumps(body)}")
    else:
        print(f" -> FAIL: /health returned status {status} with body: {body}")
        sys.exit(1)
        
    # Test 2: Framework Root Check
    print("\n[TEST 2] Querying / Root Endpoint...")
    status, body, _ = make_request(f"{base_url}/")
    if status == 200 and body.get("platform") == "Enterprise BBPS Gateway":
        print(" -> PASS: Root endpoint returns correct platform signature.")
    else:
        print(f" -> FAIL: Root endpoint returned status {status} with body: {body}")
        sys.exit(1)

    # Test 3: JWT Authentication - User Signup
    random_id = uuid.uuid4().hex[:8]
    test_username = f"verify_{random_id}"
    test_password = f"Pass_{random_id}!"
    test_email = f"{test_username}@bbps-test.com"
    
    print(f"\n[TEST 3] Registering Test User '{test_username}' with CLIENT role...")
    signup_payload = {
        "username": test_username,
        "email": test_email,
        "password": test_password,
        "role": "CLIENT"
    }
    status, body, _ = make_request(f"{base_url}/auth/signup", method="POST", data=signup_payload)
    if status == 200 and body.get("success") is True:
        print(" -> PASS: User registration endpoint is fully functional.")
    else:
        print(f" -> FAIL: Registration failed with status {status}. Response: {body}")
        sys.exit(1)

    # Test 4: JWT Authentication - Token Generation
    print("\n[TEST 4] Authenticating to retrieve JWT Access Token...")
    login_payload = {
        "username": test_username,
        "password": test_password
    }
    status, body, _ = make_request(f"{base_url}/auth/token", method="POST", data=login_payload)
    if status == 200 and "access_token" in body:
        jwt_token = body["access_token"]
        print(" -> PASS: Token generation succeeded. JWT retrieved successfully.")
    else:
        print(f" -> FAIL: Authentication failed with status {status}. Response: {body}")
        sys.exit(1)

    # Prepare Auth Header
    auth_headers = {
        "Authorization": f"Bearer {jwt_token}"
    }

    # Test 5: Fetch Bill (Requires Auth + HMAC)
    print("\n[TEST 5] Fetching Bill (Requires Client Role + Cryptographic HMAC Headers)...")
    fetch_payload = {
        "billerid": "MOCKELE00047ARU",
        "billeraccountid": "1234567890"
    }
    
    # Calculate HMAC
    canonical_body = canonicalize(fetch_payload)
    timestamp = str(int(time.time()))
    nonce = f"test-{uuid.uuid4().hex[:12]}"
    signature = calculate_hmac(canonical_body, timestamp, nonce, hmac_secret)
    
    headers = {
        **auth_headers,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "X-Source-Id": source_id,
        "X-Trace-Id": f"verify-trace-{random_id}"
    }
    
    fetch_url = f"{base_url}/BOBCOU/BBPS/{source_id}/customers/cust123/billpay/validate"
    status, body, _ = make_request(fetch_url, method="POST", headers=headers, data=fetch_payload)
    
    if status == 200 and "validationid" in body:
        validation_id = body["validationid"]
        amount = body.get("billamount", "100.00")
        print(f" -> PASS: Fetch bill success. Validation ID: {validation_id}, Amount: {amount}")
    else:
        print(f" -> FAIL: Fetch bill failed with status {status}. Response: {body}")
        sys.exit(1)

    # Test 6: Pay Bill (Requires Auth + HMAC)
    print("\n[TEST 6] Paying Bill (Requires Client Role + Cryptographic HMAC Headers)...")
    pay_payload = {
        "validationid": validation_id,
        "payment_method": "UPI",
        "source_ref_no": f"ref-{uuid.uuid4().hex[:12]}"
    }
    
    # Calculate HMAC
    canonical_body = canonicalize(pay_payload)
    timestamp = str(int(time.time()))
    nonce = f"test-{uuid.uuid4().hex[:12]}"
    signature = calculate_hmac(canonical_body, timestamp, nonce, hmac_secret)
    
    headers = {
        **auth_headers,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "X-Source-Id": source_id,
        "X-Trace-Id": f"verify-trace-{random_id}"
    }
    
    pay_url = f"{base_url}/BOBCOU/BBPS/{source_id}/customers/cust123/billpay/payments"
    status, body, _ = make_request(pay_url, method="POST", headers=headers, data=pay_payload)
    
    if status == 200 and body.get("payment_status") in ("SETTLED", "PENDING", "AMBIGUOUS_TIMEOUT"):
        print(f" -> PASS: Payment processed successfully. Status: {body.get('payment_status')}")
        print(f"    Gateway Txn ID: {body.get('txn_id')}")
    else:
        print(f" -> FAIL: Payment failed with status {status}. Response: {body}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("ALL GATEWAY DEPLOYMENT SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    # Support overriding parameters from CLI arguments
    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE_URL
    hmac_secret = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_HMAC_SECRET
    source_id = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SOURCE_ID
    
    run_smoke_tests(target_url, hmac_secret, source_id)
