import os


class Settings:
    TABLE_NAME: str = os.environ.get("TABLE_NAME", "clawhub-dev")
    BUCKET_NAME: str = os.environ.get("BUCKET_NAME", "clawhub-dev-skills")
    REGION: str = os.environ.get("REGION", "us-east-1")
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "dev")
    CORS_ORIGINS: list[str] = os.environ.get("CORS_ORIGINS", "*").split(",")


settings = Settings()
