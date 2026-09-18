from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CantieriApp"
    app_environment: str = "development"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "cantieriapp"
    jwt_secret_key: str = "change-this-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS (limitato. In produzione specificare origine esplicita, es. https://app.cantieriapp.it)
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Logging
    log_level: str = "INFO"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio-access-key"
    minio_secret_key: str = "minio-secret-key"
    minio_bucket: str = "cantieri"
    minio_secure: bool = False
    # URL pubblica base (es. http://localhost:9000 oppure https://s3.my-domain.com)
    minio_public_url: str = "http://localhost:9000"

    # Firebase (FCM)
    firebase_credentials_path: str | None = None

    # SMTP (invio email verifica OTP)
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "noreply@cantieriapp.it"
    smtp_use_tls: bool = True

    # OTP (verifica email)
    otp_ttl_minutes: int = 10
    otp_length: int = 6
    otp_max_attempts: int = 5
    otp_resend_max: int = 3
    otp_resend_window_minutes: int = 30

    # Deep link app mobile
    app_deep_link_scheme: str = "myapp"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
