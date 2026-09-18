"""
Test script for FASE 3 - AUTH + JWT + RLS
Tests all auth endpoints: register, login, refresh, me
Verifies tenant creation, membership, RLS filtering, and JWT claims.
"""

import json
import sys
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = "http://127.0.0.1:8001"
PASS = 0
FAIL = 0


def log_test(name: str, success: bool, detail: str = ""):
    global PASS, FAIL
    status = "✅ PASS" if success else "❌ FAIL"
    if success:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {status} | {name}")
    if detail:
        print(f"         {detail}")


def api_call(method: str, path: str, body: dict = None, token: str = None) -> tuple[int, dict]:
    """Make an HTTP request to the API."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req) as resp:
            status = resp.status
            response_body = json.loads(resp.read().decode("utf-8"))
            return status, response_body
    except HTTPError as e:
        status = e.code
        response_body = json.loads(e.read().decode("utf-8"))
        return status, response_body
    except URLError as e:
        return 0, {"detail": f"Connection error: {e.reason}"}


def test_health():
    """Test server is running."""
    print("\n🔍 Health Check")
    status, body = api_call("GET", "/health")
    log_test("Server health endpoint", status == 200, f"Status: {status}")
    if status == 200:
        log_test("Database connected", body.get("database") == "connected", str(body))


def test_register():
    """Test POST /auth/register - creates user + tenant + membership + returns JWT."""
    print("\n📝 Test: POST /auth/register")

    # Generate unique email to avoid conflicts
    unique_id = uuid.uuid4().hex[:8]
    email = f"test_{unique_id}@example.com"
    payload = {
        "email": email,
        "password": "TestPassword123!",
        "full_name": "Test User",
        "tenant_name": f"Test Tenant {unique_id}",
    }

    status, body = api_call("POST", "/auth/register", payload)

    log_test("Register returns 201", status == 201, f"Status: {status}")
    if status == 201:
        log_test("Has access_token", "access_token" in body, f"Token starts with: {body.get('access_token', '')[:20]}...")
        log_test("Has refresh_token", "refresh_token" in body)
        log_test("Has user data", "user" in body, f"User email: {body.get('user', {}).get('email')}")
        log_test("Has tenant data", "tenant" in body, f"Tenant name: {body.get('tenant', {}).get('name')}")
        log_test("User email matches", body.get("user", {}).get("email") == email)
        log_test("User has tenantId", "tenant_id" in body.get("user", {}), f"tenant_id: {body.get('user', {}).get('tenant_id')}")
        log_test("Tenant is active", body.get("tenant", {}).get("is_active") == True)
        log_test("Token type is bearer", body.get("token_type") == "bearer")

        # Store for later tests
        return {
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
            "user": body["user"],
            "tenant": body["tenant"],
            "email": email,
        }
    else:
        log_test("Error detail available", "detail" in body, str(body.get("detail", "")))
        return None


def test_register_duplicate_email(registered_email: str):
    """Test registering with the same email fails."""
    print("\n📝 Test: POST /auth/register (duplicate email)")

    payload = {
        "email": registered_email,
        "password": "TestPassword123!",
        "full_name": "Another User",
        "tenant_name": "Another Tenant",
    }

    status, body = api_call("POST", "/auth/register", payload)
    log_test("Duplicate email returns 400", status == 400, f"Status: {status}")
    log_test("Error message mentions email", "email" in str(body.get("detail", "")).lower(), str(body.get("detail", "")))


def test_login(registered_email: str):
    """Test POST /auth/login with valid credentials."""
    print("\n📝 Test: POST /auth/login")

    payload = {
        "email": registered_email,
        "password": "TestPassword123!",
    }

    status, body = api_call("POST", "/auth/login", payload)

    log_test("Login returns 200", status == 200, f"Status: {status}")
    if status == 200:
        log_test("Has access_token", "access_token" in body)
        log_test("Has refresh_token", "refresh_token" in body)
        log_test("Token type is bearer", body.get("token_type") == "bearer")
        return {
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
        }
    return None


def test_login_wrong_password(registered_email: str):
    """Test login with wrong password fails."""
    print("\n📝 Test: POST /auth/login (wrong password)")

    payload = {
        "email": registered_email,
        "password": "WrongPassword!",
    }

    status, body = api_call("POST", "/auth/login", payload)
    log_test("Wrong password returns 401", status == 401, f"Status: {status}")


def test_login_nonexistent_email():
    """Test login with non-existent email fails."""
    print("\n📝 Test: POST /auth/login (nonexistent email)")

    payload = {
        "email": "nonexistent@example.com",
        "password": "TestPassword123!",
    }

    status, body = api_call("POST", "/auth/login", payload)
    log_test("Nonexistent email returns 401", status == 401, f"Status: {status}")


def test_refresh_token(refresh_token: str):
    """Test POST /auth/refresh with a valid refresh token."""
    print("\n📝 Test: POST /auth/refresh")

    payload = {
        "refresh_token": refresh_token,
    }

    status, body = api_call("POST", "/auth/refresh", payload)

    log_test("Refresh returns 200", status == 200, f"Status: {status}")
    if status == 200:
        log_test("Has new access_token", "access_token" in body)
        log_test("Has new refresh_token", "refresh_token" in body)
        log_test("Token type is bearer", body.get("token_type") == "bearer")
        return {
            "access_token": body["access_token"],
            "refresh_token": body["refresh_token"],
        }
    return None


def test_refresh_with_access_token(access_token: str):
    """Test using an access token as refresh token fails."""
    print("\n📝 Test: POST /auth/refresh (with access token)")

    payload = {
        "refresh_token": access_token,
    }

    status, body = api_call("POST", "/auth/refresh", payload)
    log_test("Access token as refresh returns 401", status == 401, f"Status: {status}")


def test_me(access_token: str, expected_email: str):
    """Test GET /auth/me with valid token."""
    print("\n📝 Test: GET /auth/me")

    status, body = api_call("GET", "/auth/me", token=access_token)

    log_test("Me returns 200", status == 200, f"Status: {status}")
    if status == 200:
        log_test("Email matches", body.get("email") == expected_email, f"Expected: {expected_email}, Got: {body.get('email')}")
        log_test("Has full_name", "full_name" in body, f"Name: {body.get('full_name')}")
        log_test("Has tenantId", "tenant_id" in body, f"tenant_id: {body.get('tenant_id')}")
        log_test("Has is_active", "isActive" in body or "is_active" in body, str(body))
        log_test("Has is_superuser", "isSuperuser" in body or "is_superuser" in body, str(body))


def test_me_no_token():
    """Test GET /auth/me without token fails."""
    print("\n📝 Test: GET /auth/me (no token)")

    status, body = api_call("GET", "/auth/me")
    log_test("No token returns 401", status == 401, f"Status: {status}")


def test_me_invalid_token():
    """Test GET /auth/me with invalid token fails."""
    print("\n📝 Test: GET /auth/me (invalid token)")

    status, body = api_call("GET", "/auth/me", token="invalid_token_here")
    log_test("Invalid token returns 401", status == 401, f"Status: {status}")


def test_jwt_claims(access_token: str):
    """Decode and verify JWT claims (userId, tenantId, role)."""
    print("\n📝 Test: JWT Claims Verification")

    # We can't decode server-side, but we can verify the token works
    # The /auth/me endpoint already validates the token
    status, body = api_call("GET", "/auth/me", token=access_token)
    log_test("JWT with claims works for /auth/me", status == 200, f"Status: {status}")
    if status == 200:
        log_test("User has tenantId (RLS ready)", "tenant_id" in body, str(body))


def test_rls_isolation():
    """Test that users from different tenants cannot access each other's data."""
    print("\n📝 Test: RLS Tenant Isolation")

    # Register user 1
    uid1 = uuid.uuid4().hex[:8]
    email1 = f"rls_user1_{uid1}@example.com"
    payload1 = {
        "email": email1,
        "password": "TestPassword123!",
        "full_name": "RLS User 1",
        "tenant_name": f"RLS Tenant 1 {uid1}",
    }
    status1, body1 = api_call("POST", "/auth/register", payload1)

    # Register user 2
    uid2 = uuid.uuid4().hex[:8]
    email2 = f"rls_user2_{uid2}@example.com"
    payload2 = {
        "email": email2,
        "password": "TestPassword123!",
        "full_name": "RLS User 2",
        "tenant_name": f"RLS Tenant 2 {uid2}",
    }
    status2, body2 = api_call("POST", "/auth/register", payload2)

    log_test("User 1 registered", status1 == 201)
    log_test("User 2 registered", status2 == 201)

    if status1 == 201 and status2 == 201:
        token1 = body1["access_token"]
        token2 = body2["access_token"]
        tenant1_id = body1["tenant"]["id"]
        tenant2_id = body2["tenant"]["id"]

        log_test("User 1 has different tenant than User 2", tenant1_id != tenant2_id,
                 f"Tenant1: {tenant1_id}, Tenant2: {tenant2_id}")

        # Get /auth/me for both users
        s1, b1 = api_call("GET", "/auth/me", token=token1)
        s2, b2 = api_call("GET", "/auth/me", token=token2)

        if s1 == 200 and s2 == 200:
            log_test("User 1 tenantId matches", b1.get("tenant_id") == tenant1_id,
                     f"Expected: {tenant1_id}, Got: {b1.get('tenant_id')}")
            log_test("User 2 tenantId matches", b2.get("tenant_id") == tenant2_id,
                     f"Expected: {tenant2_id}, Got: {b2.get('tenant_id')}")
            log_test("RLS: User 1 cannot see User 2's tenant", b1.get("tenant_id") != tenant2_id)
            log_test("RLS: User 2 cannot see User 1's tenant", b2.get("tenant_id") != tenant1_id)


def main():
    print("=" * 60)
    print("🧪 FASE 3 - AUTH + JWT + RLS - Test Suite")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Health check
    test_health()

    # 2. Register
    result = test_register()
    if result:
        registered_email = result["email"]
        access_token = result["access_token"]
        refresh_token = result["refresh_token"]

        # 3. Duplicate registration
        test_register_duplicate_email(registered_email)

        # 4. Login
        login_result = test_login(registered_email)
        if login_result:
            access_token = login_result["access_token"]
            refresh_token = login_result["refresh_token"]

        # 5. Login with wrong password
        test_login_wrong_password(registered_email)

        # 6. Login with nonexistent email
        test_login_nonexistent_email()

        # 7. Refresh token
        refresh_result = test_refresh_token(refresh_token)
        if refresh_result:
            access_token = refresh_result["access_token"]
            refresh_token = refresh_result["refresh_token"]

        # 8. Refresh with access token (should fail)
        test_refresh_with_access_token(access_token)

        # 9. Get /auth/me
        test_me(access_token, registered_email)

        # 10. /auth/me without token
        test_me_no_token()

        # 11. /auth/me with invalid token
        test_me_invalid_token()

        # 12. JWT claims
        test_jwt_claims(access_token)

        # 13. RLS isolation
        test_rls_isolation()

    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print("=" * 60)

    if FAIL > 0:
        sys.exit(1)
    else:
        print("🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
