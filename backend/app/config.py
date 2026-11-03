import os

class Settings:
    APP_NAME: str = "Книжный круговорот"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/book_exchange")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()