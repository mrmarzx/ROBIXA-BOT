from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str = ""
    ADMIN_IDS: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/robixa.db"
    BOT_VERSION: str = "2.0.0"
    BOT_NAME: str = "ROBIXA BOT"
    DEFAULT_LANGUAGE: str = "fa"
    SUPPORT_USERNAME: str = "@Support"
    BACKUP_INTERVAL_HOURS: int = 24
    BACKUP_CHAT_ID: str = ""
    INSTALL_DIR: str = ""

    @property
    def admin_ids(self) -> List[int]:
        if not self.ADMIN_IDS:
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip().isdigit()]


settings = Settings()