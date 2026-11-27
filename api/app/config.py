from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24


settings = Settings()

