from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    DEBUG: bool = False
    RESTAURANT_SERVICE_URL: str = "http://restaurant-service:8002"
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"


settings = Settings()
