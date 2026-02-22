from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    dynamodb_endpoint_url: str = "http://localhost:8001"
    dynamodb_region: str = "ap-northeast-1"
    debug: bool = False
    scrape_interval_sec: float = 2.0


settings = Settings()
