from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    log_level: str = "INFO"
    timeout: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_"
    )


settings = Settings()