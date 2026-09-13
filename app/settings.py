from datetime import timedelta
from pathlib import Path

import pydantic
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: SecretStr = pydantic.Field(min_length=32)
    DATABASE_PATH: Path = Path("var/app.db")
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: SecretStr = SecretStr("")
    TWITTER_REDIRECT_URI: str = "http://127.0.0.1:5000/auth/callback"
    LOGIN_TOKEN_EXPIRY: timedelta = pydantic.Field(
        default=timedelta(days=30), gt=timedelta(0)
    )
    COOKIE_SECURE: bool = True
