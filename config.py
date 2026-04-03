"""PRISM Data Layer — configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "prism"
    db_user: str = "prism"
    db_password: str = "prism"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Upbit
    upbit_access_key: str = ""
    upbit_secret_key: str = ""

    # KIS (한국투자증권) — Phase 2
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_base_url: str = "https://openapi.koreainvestment.com:9443"

    # Collection — crypto (Upbit)
    default_markets: list[str] = ["KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-SOL", "KRW-ADA"]
    candle_intervals: list[str] = ["1", "3", "5", "15", "60", "240", "D", "W"]
    backfill_days: int = 365

    # Collection — Korean stocks (KIS)
    stock_backfill_days: int = 730   # 2 years of daily data

    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def async_db_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
