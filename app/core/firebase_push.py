from __future__ import annotations

from typing import Any

from app.core.config import get_settings

settings = get_settings()


def is_firebase_configured() -> bool:
    return bool(getattr(settings, "firebase_credentials_path", None))


async def send_firebase_push(
    *,
    device_token: str,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> None:
    """
    Non blocca la richiesta principale: qualsiasi errore Firebase viene gestito internamente.
    """
    try:
        # Lazy import: evita crash se firebase-admin non è installato o non configurato.
        import firebase_admin
        from firebase_admin import credentials, messaging  # type: ignore

        if not is_firebase_configured():
            return

        if not firebase_admin._apps:  # type: ignore[attr-defined]
            cred_path = settings.firebase_credentials_path
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

        msg = messaging.Message(
            token=device_token,
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
        )
        # messaging.send is sync; safe enough to run in threadpool if needed,
        # but for simplicity we call it directly. Errors are swallowed.
        messaging.send(msg)

    except Exception:
        # Swallow all Firebase errors (per requirement)
        return
