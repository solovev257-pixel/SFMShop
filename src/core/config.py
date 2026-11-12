from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30

    # в docker compose REDIS_HOST=redis (имя сервиса), локально остаётся localhost
    redis_host: str = "localhost"
    redis_port: int = 6379

    # MongoDB для логов (src/services/log_service.py)
    mongo_host: str = "localhost"
    mongo_port: int = 27017

    debug: bool = False
    sentry_dsn: str = ""

    llm_api_key: str = ""
    llm_base_url: str = "https://api.vsegpt.ru/v1"
    llm_model: str = "openai/gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()