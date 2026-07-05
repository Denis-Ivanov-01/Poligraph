from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://app_user:password@postgres:5432/politic_bs_filter"
    redis_url: str = "redis://redis:6379/0"
    app_env: str = "development"
    app_secret_key: str = Field(default="change-me", min_length=8)
    session_cookie_name: str = "politic_bs_session"
    root_admin_username: str = "admin"
    root_admin_password_hash: str = "plain:admin"
    root_admin_enabled: bool = True
    public_base_url: str = "http://localhost:5173"
    backend_base_url: str = "http://localhost:8000"
    media_storage_path: str = "./media"
    cors_allowed_origins: str = "http://localhost:5173"
    diagnostics_panel_enabled: bool = False
    diagnostics_panel_path: str = "/diagnostics_panel"
    diagnostics_dashboard_url: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def diagnostics_route_path(self) -> str:
        path = self.diagnostics_panel_path.strip() or "/diagnostics_panel"
        return path if path.startswith("/") else f"/{path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
