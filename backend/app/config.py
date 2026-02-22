from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    dynamodb_endpoint_url: str | None = None
    dynamodb_region: str = "ap-northeast-1"
    dynamodb_table_prefix: str = ""
    debug: bool = False
    scrape_interval_sec: float = 2.0
    cors_allow_origins: str = "http://localhost:3000"

    def table_name(self, base_name: str) -> str:
        if self.dynamodb_table_prefix:
            return f"{self.dynamodb_table_prefix}-{base_name}"
        return base_name


settings = Settings()
