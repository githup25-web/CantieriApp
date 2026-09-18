from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserStatus
from app.services.email_service import send_otp_email
from app.services.otp_service import (
    can_resend,
    create_otp,
    log_security_event,
    register_resend,
    verify_user_and_otp,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class VerifyRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendOtpRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterResponse(BaseModel):
    message: str
    user_id: str


class VerifyResponse(BaseModel):
    user_id: str
    status: str


class UserResponse(BaseModel):
    id: str | None = None
    email: EmailStr
    full_name: str | None = None
    organization_id: str | None = None
    is_active: bool = True
    status: str | None = None
    roles: list[str] = []
    tenant_ids: list[str] = []


def _get_client_ip(request: Request) -> str | None:
    """Recupera l'IP del client (rispetta proxy reverse)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request) -> RegisterResponse:
    """Crea un utente con stato pending_verification, genera OTP e invia email."""
    existing_user = await User.find_one(User.email == str(payload.email))
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=str(payload.email),
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        status=UserStatus.PENDING_VERIFICATION,
    )
    await user.insert()

    # Genera OTP
    code = create_otp(user)
    await user.save()

    # Invia email (asincrono)
    await send_otp_email(
        email=str(payload.email),
        otp=code,
        full_name=payload.full_name,
        expires_minutes=settings.otp_ttl_minutes,
    )

    log_security_event("register", user.email, _get_client_ip(request))

    return RegisterResponse(message="Registrazione completata. Controlla la tua email per il codice OTP.", user_id=str(user.id))


@router.post("/verify", response_model=VerifyResponse)
async def verify(payload: VerifyRequest, request: Request) -> VerifyResponse:
    """Valida l'OTP e aggiorna lo stato utente a 'verified'."""
    user = await User.find_one(User.email == str(payload.email))
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    if user.status == UserStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="Utente già verificato")

    ok, msg = await verify_user_and_otp(user, payload.otp.strip(), _get_client_ip(request))
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    return VerifyResponse(user_id=str(user.id), status=user.status.value)


@router.post("/resend-otp", response_model=RegisterResponse)
async def resend_otp(payload: ResendOtpRequest, request: Request) -> RegisterResponse:
    """Rigenera OTP con rate limit (max 3 ogni 30 min)."""
    user = await User.find_one(User.email == str(payload.email))
    if not user:
        # Non rivelare se l'email esiste (anti-enumeration)
        raise HTTPException(status_code=404, detail="Email non registrata")

    if user.status == UserStatus.VERIFIED:
        raise HTTPException(status_code=400, detail="Utente già verificato")

    if not can_resend(user):
        log_security_event("resend_rate_limited", user.email, _get_client_ip(request))
        raise HTTPException(status_code=429, detail="Troppi tentativi di reinvio. Riprova più tardi.")

    # Registra il reinvio e genera nuovo OTP
    register_resend(user)
    code = create_otp(user)
    await user.save()

    await send_otp_email(
        email=str(payload.email),
        otp=code,
        full_name=user.full_name,
        expires_minutes=settings.otp_ttl_minutes,
    )

    log_security_event("resend", user.email, _get_client_ip(request))

    return RegisterResponse(message="Nuovo codice OTP inviato.", user_id=str(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    user = await User.find_one(User.email == str(payload.email))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    if user.status != UserStatus.VERIFIED:
        raise HTTPException(
            status_code=403,
            detail="Email non verificata. Completa la verifica tramite il codice OTP inviato.",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        status=current_user.status.value if current_user.status else None,
        roles=current_user.roles,
        tenant_ids=current_user.tenant_ids,
    )
