from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://phara:changeme@localhost:5432/pharalab"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    upload_dir: str = "uploads"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 5


settings = Settings()
