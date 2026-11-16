import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "sfmshop"
    db_user: str = "postgres"
    db_password: str = ""
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    exchange_base_url: str = "https://api.exchangerate-api.com/v4/latest"
    order_details_api_url: str = "https://api.orders.sfmshop.ru/order"
    llm_timeout: float = 10.0
    llm_max_tokens: int = 400

    @property
    def db_config(self) -> dict:
        return {
            "host": self.db_host, "port": self.db_port,
            "database": self.db_name, "user": self.db_user,
            "password": self.db_password,
        }

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

    # Пустой SFMShop_ENV_FILE отключает чтение .env, например в тестах и CI.
    model_config = SettingsConfigDict(
        env_file=os.environ.get("SFMShop_ENV_FILE", ".env") or None, extra="ignore",
    )


settings = Settings()
