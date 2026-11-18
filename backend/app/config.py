from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    #определяем сложность вычисления хэша пароля (значения по умолчанию) 
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    #настройки для JWT токена 
    secret_key: str

    algorithm: str = "HS256" #алгоритм подписи JWT

    access_token_expire_minutes: int = 30 #время действия токена

    #дополнительные настройки приложения
    hash_scheme: str = "argon2id" #используемая схема хэширования 
    app_env: str = "development" #режим работы приложения 
    port: int = 8000

#создание объекта класса
settings = Settings()