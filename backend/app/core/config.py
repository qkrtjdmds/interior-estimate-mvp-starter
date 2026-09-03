from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BASE_DIR.parent


class Settings(BaseSettings):
    app_name: str = "Interior Estimate API"
    database_url: str
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://192.168.219.109:5173"
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
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def get_jwt_secret_key(self) -> str:
        if self.jwt_secret_key is None or len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be configured with at least 32 characters")
        return self.jwt_secret_key


settings = Settings()


