from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me-to-a-random-secret"
    DATABASE_URL: str = "sqlite+aiosqlite:///./workspace/sundial.db"
    WORKSPACE_DIR: str = "./workspace"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    ANTHROPIC_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
