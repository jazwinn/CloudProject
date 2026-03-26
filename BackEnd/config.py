from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # AWS Configuration
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_SESSION_TOKEN: str | None = None
    AWS_REGION: str
    S3_BUCKET_NAME: str
    DYNAMO_TABLE_NAME: str
    AWS_LAMBDA_FUNCTION_NAME: str

    # Cognito Configuration
    COGNITO_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings():
    return Settings()
