from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.models.user import OtpInfo, User, UserStatus

settings = get_settings()
logger = logging.getLogger("cantieriapp.otp")


def generate_otp() -> str:
    """Genera un OTP a 6 cifre crittograficamente sicuro."""
    # secrets.randbelow è crittograficamente sicuro (non ripetibile/predicibile)
    return f"{secrets.randbelow(10 ** settings.otp_length):0{settings.otp_length}d}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime | None) -> datetime | None:
    """MongoDB/Beanie restituisce datetime naive; normalizza a timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def create_otp(user: User) -> str:
    """Genera un nuovo OTP, aggiorna il record utente e lo salva. Ritorna il codice."""
    code = generate_otp()
    expires_at = _now() + timedelta(minutes=settings.otp_ttl_minutes)

    user.otp = OtpInfo(
        code=code,
        expires_at=expires_at,
        attempts=0,
        resend_count=user.otp.resend_count if user.otp else 0,
        resend_window_start=user.otp.resend_window_start if user.otp else None,
    )
    return code


def can_resend(user: User) -> bool:
    """Rate limit reinvio OTP: max N ogni finestra di X minuti."""
    if user.otp is None:
        return True

    window_start = _ensure_aware(user.otp.resend_window_start)
    if window_start is None:
        return True

    window_minutes = settings.otp_resend_window_minutes
    window_expires = window_start + timedelta(minutes=window_minutes)

    if _now() > window_expires:
        # La finestra è scaduta: reset del contatore
        return True

    return user.otp.resend_count < settings.otp_resend_max


def register_resend(user: User) -> None:
    """Aggiorna il contatore di reinvio per il rate limit."""
    now = _now()
    if user.otp is None:
        user.otp = OtpInfo(
            code="",
            expires_at=now,
            attempts=0,
            resend_count=1,
            resend_window_start=now,
        )
        return

    window_start = _ensure_aware(user.otp.resend_window_start)
    if window_start is None or now > window_start + timedelta(minutes=settings.otp_resend_window_minutes):
        # Nuova finestra
        user.otp.resend_count = 1
        user.otp.resend_window_start = now
    else:
        user.otp.resend_count += 1


def validate_otp(user: User, code: str) -> tuple[bool, str]:
    """
    Valida l'OTP. Gestisce scadenza, tentativi, single-use.
    Ritorna (successo, messaggio). Aggiorna il record utente (tentativi).
    """
    if user.otp is None:
        return False, "Nessun codice OTP trovato. Richiedi un nuovo codice."

    if user.otp.attempts >= settings.otp_max_attempts:
        return False, "Troppi tentativi errati. Richiedi un nuovo codice."

    expires_at = _ensure_aware(user.otp.expires_at)
    if expires_at is None or _now() > expires_at:
        return False, "Codice OTP scaduto. Richiedi un nuovo codice."

    if user.otp.code != code:
        user.otp.attempts += 1
        logger.warning("OTP verification failed for user %s (attempt %d)", user.id, user.otp.attempts)
        return False, "Codice OTP non valido."

    # Successo: single-use, invalidiamo l'OTP
    user.otp.attempts = 0
    user.otp.code = ""  # invalidato
    logger.info("OTP verified successfully for user %s", user.id)
    return True, "OK"


def log_security_event(event: str, email: str, ip: str | None = None) -> None:
    """Logging eventi di sicurezza (register, verify, resend-guard)."""
    logger.info(
        "SECURITY EVENT | event=%s | email=%s | ip=%s",
        event,
        email,
        ip or "unknown",
    )


async def verify_user_and_otp(user: User, code: str, ip: str | None = None) -> tuple[bool, str]:
    """Verifica l'OTP e, se valido, aggiorna lo stato utente a 'verified'."""
    ok, msg = validate_otp(user, code)
    if not ok:
        log_security_event("verify_failed", user.email, ip)
        await user.save()
        return False, msg

    user.status = UserStatus.VERIFIED
    user.otp = None  # rimuove l'OTP dopo verifica riuscita
    await user.save()
    log_security_event("verify_success", user.email, ip)
    return True, "OK"
