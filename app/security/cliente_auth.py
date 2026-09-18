from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()
security_scheme = HTTPBearer(auto_error=False)


class ClienteTokenPayload(BaseModel):
    cliente_id: str
    cantiere_id: str
    exp: datetime


def create_cliente_token(cliente_id: str, cantiere_id: str) -> str:
    # Token minimale: solo identificativi necessari (cliente_id, cantiere_id) + exp
    exp_seconds = settings.access_token_expire_minutes * 60
    now = datetime.now(timezone.utc)

    to_encode: dict[str, Any] = {
        "cliente_id": cliente_id,
        "cantiere_id": cantiere_id,
        "exp": now.timestamp() + exp_seconds,
    }
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_cliente_token(token: str) -> ClienteTokenPayload:
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    try:
        # exp potrebbe essere float; pydantic lo gestisce in modo robusto
        return ClienteTokenPayload(**payload)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token cliente non valido") from exc


async def get_current_cliente(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> ClienteTokenPayload:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non autenticato")

    try:
        payload = decode_cliente_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Token cliente invalido") from exc

    # FASE 8: verifica che il cliente esista ancora e sia attivo nel DB.
    from app.models.cliente import Cliente

    try:
        cliente = await Cliente.get(UUID(payload.cliente_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Cliente non trovato")

    if not cliente or not cliente.is_active:
        raise HTTPException(status_code=401, detail="Cliente non valido o disattivato")

    # FASE 8: se il token contiene un cantiere_id, verifica che l'accesso sia ancora attivo.
    if payload.cantiere_id:
        from app.models.cliente_access_code import ClienteAccessCode

        access = await ClienteAccessCode.find_one(
            {
                "cliente_id": str(cliente.id),
                "cantiere_id": str(payload.cantiere_id),
                "active": True,
            }
        )
        if not access:
            raise HTTPException(
                status_code=403,
                detail="Accesso al cantiere non più attivo",
            )

    return payload


def require_cliente_cantiere_match(cantiere_id: str):
    async def _dep(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> ClienteTokenPayload:
        if str(current_cliente.cantiere_id) != str(cantiere_id):
            raise HTTPException(status_code=403, detail="Accesso non autorizzato al cantiere")
        return current_cliente

    return _dep


def require_cliente_tenant_match(tenant_id: str):
    """Verifica che il cliente autenticato appartenga al tenant specificato."""

    async def _dep(current_cliente: ClienteTokenPayload = Depends(get_current_cliente)) -> ClienteTokenPayload:
        # Il token cliente non contiene direttamente tenant_id; dobbiamo caricare il cliente dal DB.
        from app.models.cliente import Cliente

        try:
            cliente = await Cliente.get(UUID(current_cliente.cliente_id))
        except (ValueError, TypeError):
            raise HTTPException(status_code=401, detail="Cliente non trovato")

        if not cliente:
            raise HTTPException(status_code=401, detail="Cliente non trovato")

        if str(cliente.tenant_id) != str(tenant_id):
            raise HTTPException(status_code=403, detail="Accesso non autorizzato al tenant")
        return current_cliente

    return _dep
