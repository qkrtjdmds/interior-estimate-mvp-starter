import pytest

from app.core.config import Settings


def make_settings(cors_origins: str, app_env: str = "production") -> Settings:
    return Settings(
        _env_file=None,
        app_env=app_env,
        database_url="sqlite+pysqlite:///:memory:",
        cors_origins=cors_origins,
    )


def test_production_cors_accepts_https_public_origins() -> None:
    settings = make_settings("https://frontend.example.com, https://admin.example.com/")

    assert settings.cors_origin_list == ["https://frontend.example.com", "https://admin.example.com"]


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://frontend.example.com",
        "http://localhost:5173",
        "https://localhost:5173",
        "https://127.0.0.1:5173",
        "https://192.168.0.10:5173",
        "https://10.0.0.10:5173",
        "https://172.16.0.10:5173",
        "https://172.31.0.10:5173",
    ],
)
def test_production_cors_rejects_development_or_private_origins(origin: str) -> None:
    settings = make_settings(origin)

    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        _ = settings.cors_origin_list


def test_development_cors_allows_localhost() -> None:
    settings = make_settings("http://localhost:5173", app_env="development")

    assert settings.cors_origin_list == ["http://localhost:5173"]
