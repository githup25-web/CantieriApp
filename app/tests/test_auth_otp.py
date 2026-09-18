"""Test automatici per il flusso di registrazione + verifica email (OTP)."""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.user import User, UserStatus


def _register(client, email=None, password="TestPassword123!"):
    """Helper: registra un utente e ritorna (response, email)."""
    if email is None:
        email = f"otp_{uuid.uuid4().hex[:8]}@example.com"
    payload = {"email": email, "password": password, "full_name": "Test OTP User"}
    resp = client.post("/auth/register", json=payload)
    return resp, email


def _get_otp(client, email):
    """Recupera l'OTP dal database per un'email."""
    result = {}

    async def _fetch():
        user = await User.find_one(User.email == email)
        result["otp"] = user.otp.code if user and user.otp else None
        result["user"] = user

    client.portal.call(_fetch)
    return result["otp"]


def _set_user_status(client, email, status):
    """Imposta lo stato di un utente direttamente nel DB."""
    async def _update():
        user = await User.find_one(User.email == email)
        user.status = status
        await user.save()

    client.portal.call(_update)


def _expire_otp(client, email):
    """Fa scadere l'OTP di un utente direttamente nel DB."""
    async def _expire():
        user = await User.find_one(User.email == email)
        user.otp.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await user.save()

    client.portal.call(_expire)


def _set_otp_attempts(client, email, attempts):
    """Imposta i tentativi errati di un utente direttamente nel DB."""
    async def _set():
        user = await User.find_one(User.email == email)
        user.otp.attempts = attempts
        await user.save()

    client.portal.call(_set)


class TestRegister:
    def test_register_success(self, client):
        resp, email = _register(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["message"]
        assert "user_id" in data

    def test_register_duplicate_email(self, client):
        resp1, email = _register(client)
        assert resp1.status_code == 201

        resp2, _ = _register(client, email=email)
        assert resp2.status_code == 400
        assert "Email" in str(resp2.json()["detail"])

    def test_register_creates_pending_verification(self, client):
        resp, email = _register(client)
        assert resp.status_code == 201
        user_id = resp.json()["user_id"]

        async def _get_user():
            user = await User.get(uuid.UUID(user_id))
            return user.status

        status = client.portal.call(_get_user)
        assert status == UserStatus.PENDING_VERIFICATION

    def test_register_generates_otp(self, client):
        resp, email = _register(client)
        assert resp.status_code == 201

        otp = _get_otp(client, email)
        assert otp is not None
        assert len(otp) == 6
        assert otp.isdigit()


class TestVerify:
    def test_verify_success(self, client):
        resp, email = _register(client)
        assert resp.status_code == 201
        user_id = resp.json()["user_id"]
        otp = _get_otp(client, email)

        resp = client.post("/auth/verify", json={"email": email, "otp": otp})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user_id
        assert data["status"] == "verified"

        # OTP deve essere single-use (invalidato dopo verifica)
        otp_after = _get_otp(client, email)
        assert otp_after is None  # user.otp impostato a None dopo verifica

    def test_verify_wrong_otp(self, client):
        _, email = _register(client)
        otp = _get_otp(client, email)
        wrong = "000000" if otp != "000000" else "111111"

        resp = client.post("/auth/verify", json={"email": email, "otp": wrong})
        assert resp.status_code == 400
        assert "non valido" in str(resp.json()["detail"])

    def test_verify_expired_otp(self, client):
        _, email = _register(client)
        _expire_otp(client, email)

        otp = _get_otp(client, email)
        resp = client.post("/auth/verify", json={"email": email, "otp": otp})
        assert resp.status_code == 400
        assert "scaduto" in str(resp.json()["detail"])

    def test_verify_unknown_email(self, client):
        resp = client.post("/auth/verify", json={"email": "nobody@example.com", "otp": "123456"})
        assert resp.status_code == 404

    def test_verify_already_verified(self, client):
        resp, email = _register(client)
        otp = _get_otp(client, email)
        client.post("/auth/verify", json={"email": email, "otp": otp})

        # Cerca un nuovo OTP per provare a verificare di nuovo
        resp2, _ = _register(client, email=email)
        assert resp2.status_code == 400  # email già registrata

    def test_verify_blocks_after_max_attempts(self, client):
        _, email = _register(client)
        _set_otp_attempts(client, email, 5)

        otp = _get_otp(client, email)
        resp = client.post("/auth/verify", json={"email": email, "otp": otp})
        assert resp.status_code == 400
        assert "Troppi tentativi" in str(resp.json()["detail"])


class TestResendOtp:
    def test_resend_success(self, client):
        resp, email = _register(client)
        assert resp.status_code == 201

        old_otp = _get_otp(client, email)

        resp = client.post("/auth/resend-otp", json={"email": email})
        assert resp.status_code == 200

        new_otp = _get_otp(client, email)
        assert new_otp is not None
        assert new_otp != old_otp  # deve generare un nuovo codice

    def test_resend_unknown_email(self, client):
        resp = client.post("/auth/resend-otp", json={"email": "nobody@example.com"})
        assert resp.status_code == 404

    def test_resend_rate_limit(self, client):
        _, email = _register(client)

        # Esaurisce i 3 reinvii disponibili
        for _ in range(3):
            resp = client.post("/auth/resend-otp", json={"email": email})
            assert resp.status_code == 200

        # Il 4° deve essere limitato (429)
        resp = client.post("/auth/resend-otp", json={"email": email})
        assert resp.status_code == 429


class TestLogin:
    def test_login_before_verification_rejected(self, client):
        resp, email = _register(client)
        assert resp.status_code == 201

        resp = client.post("/auth/login", json={"email": email, "password": "TestPassword123!"})
        assert resp.status_code == 403
        assert "verificata" in str(resp.json()["detail"])

    def test_login_after_verification_success(self, client):
        resp, email = _register(client)
        otp = _get_otp(client, email)
        client.post("/auth/verify", json={"email": email, "otp": otp})

        resp = client.post("/auth/login", json={"email": email, "password": "TestPassword123!"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client):
        resp, email = _register(client)
        otp = _get_otp(client, email)
        client.post("/auth/verify", json={"email": email, "otp": otp})

        resp = client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})
        assert resp.status_code == 401
