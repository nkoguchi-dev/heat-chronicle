from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://heat_user:heat_user@localhost:5432/heat_db"
    debug: bool = False


settings = Settings()
