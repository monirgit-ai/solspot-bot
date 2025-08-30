

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SOL Spot Bot"
    TZ: str = "Asia/Dhaka"
    MODE: str = "paper"
    
    # Database
    DB_URL: str = "sqlite:///./solspot_bot.db"
    
    # Binance API
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    
    # Telegram Bot
    TG_BOT_TOKEN: Optional[str] = None
    TG_CHAT_ID: Optional[int] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
