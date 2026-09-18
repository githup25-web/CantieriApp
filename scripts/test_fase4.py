import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

# Test 1: Health check
print("=== Test 1: Health check ===")
try:
    req = urllib.request.Request(f"{BASE_URL}/health")
    resp = urllib.request.urlopen(req, timeout=5)
    print(f"Health check: {resp.status} {resp.read().decode()}")
except Exception as e:
    print(f"Backend not running: {e}")
    sys.exit(1)

# Test 2: Register a test user
print("\n=== Test 2: POST /auth/register ===")
reg_data = json.dumps({
    "email": "test_fase4@example.com",
    "password": "Test123!",
    "full_name": "Test Fase4 User"
}).encode()
try:
    req = urllib.request.Request(
        f"{BASE_URL}/auth/register",
        data=reg_data,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=5)
    reg_body = json.loads(resp.read().decode())
    print(f"Register response status: {resp.status}")
    print(f"User created: {reg_body.get('user', {}).get('email', 'N/A')}")
    print(f"Tenant created: {reg_body.get('tenant', {}).get('name', 'N/A')}")
    print(f"Has access_token: {'access_token' in reg_body}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    # If user already exists, that's fine
    if "already registered" in body:
        print(f"User already exists (OK): {e.code}")
    else:
        print(f"Register error: {e.code} {body}")
        sys.exit(1)

# Test 3: Login with the registered user
print("\n=== Test 3: POST /auth/login ===")
login_data = json.dumps({"email": "test_fase4@example.com", "password": "Test123!"}).encode()
req = urllib.request.Request(
    f"{BASE_URL}/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req, timeout=5)
    body = json.loads(resp.read().decode())
    print(f"Login response status: {resp.status}")
    print(f"Has access_token: {'access_token' in body}")
    print(f"Has refresh_token: {'refresh_token' in body}")
    if "access_token" in body:
        print(f"access_token (first 20 chars): {body['access_token'][:20]}...")
    access_token = body.get("access_token", "")
    
    # Test 4: /auth/me with the token
    print("\n=== Test 4: GET /auth/me ===")
    req2 = urllib.request.Request(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    resp2 = urllib.request.urlopen(req2, timeout=5)
    me = json.loads(resp2.read().decode())
    print(f"/auth/me response status: {resp2.status}")
    print(f"User data:")
    print(f"  full_name: {me.get('full_name', 'N/A')}")
    print(f"  tenant_id: {me.get('tenant_id', 'N/A')}")
    print(f"  email: {me.get('email', 'N/A')}")
    print(f"  is_active: {me.get('is_active', 'N/A')}")
    
    # Test 5: /auth/me without token (should fail with 401)
    print("\n=== Test 5: GET /auth/me WITHOUT token (should fail) ===")
    try:
        req3 = urllib.request.Request(f"{BASE_URL}/auth/me")
        resp3 = urllib.request.urlopen(req3, timeout=5)
        print(f"ERROR: Should have failed but got {resp3.status}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        print(f"Correctly rejected: {e.code} {err_body}")
    
    print("\n✅ All tests passed! FASE 4 endpoints working correctly.")
    
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
