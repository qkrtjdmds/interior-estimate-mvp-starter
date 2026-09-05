from pathlib import Path
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Interior Estimate API"
    app_env: str = "development"
    database_url: str
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480
    pdf_font_path: str | None = None
    pdf_font_bold_path: str | None = None

    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BASE_DIR / ".env"),
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]
        if not origins:
            raise ValueError("CORS_ORIGINS must include at least one origin")
        if self.is_production:
            invalid_origins = [origin for origin in origins if not self._is_production_cors_origin(origin)]
            if invalid_origins:
                raise ValueError("CORS_ORIGINS must contain only HTTPS production origins when APP_ENV=production")
        return origins

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    @staticmethod
    def _is_production_cors_origin(origin: str) -> bool:
        if origin == "*":
            return False
        parsed = urlparse(origin)
        host = parsed.hostname or ""
        if parsed.scheme != "https":
            return False
        if host in {"localhost", "127.0.0.1", "0.0.0.0"}:
            return False
        if host.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")):
            return False
        return True

    def get_jwt_secret_key(self) -> str:
        if self.jwt_secret_key is None or len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be configured with at least 32 characters")
        return self.jwt_secret_key


settings = Settings()
