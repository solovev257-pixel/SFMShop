from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30

    redis_url: str = "redis://localhost:6379/0"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.vsegpt.ru/v1"
    llm_model: str = "openai/gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()