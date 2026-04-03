from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # On ECS Fargate, credentials are provided automatically via the Task IAM Role.
    # Do not use static credentials — boto3 picks them up from the instance metadata service.
    # For local development, use `aws sso login` or a named AWS profile.
    AWS_REGION: str
    S3_BUCKET_NAME: str
    AWS_LAMBDA_FUNCTION_NAME: str

    # Database Configuration
    DATABASE_URL: str

    # Cognito Configuration
    COGNITO_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings():
    return Settings()
