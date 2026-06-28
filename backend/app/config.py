from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    # Stage 1: Supabase connection string
    # postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    database_url: str = "postgresql+asyncpg://phara:changeme@localhost:5432/pharalab"
    use_sqlite: bool = False   # set true on HF Spaces
    sqlite_path: str = "/data/lab.db"

    # ── Cache — Upstash Redis (TLS) ───────────────────────────────────────────
    # Stage 1: rediss://default:[token]@[host].upstash.io:6379
    redis_url: str = "redis://localhost:6379/0"

    # ── Vector DB — Qdrant Cloud ──────────────────────────────────────────────
    # Stage 1: host = xyz.us-east-1.aws.cloud.qdrant.io, port = 6333
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""   # Qdrant Cloud API key (empty = no auth / local)
    qdrant_in_memory: bool = False  # set true on HF Spaces

    # ── Auth ──────────────────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ── LLM ──────────────────────────────────────────────────────────────────
    # Option A (OpenAI / any OpenAI-compatible provider):
    #   LLM_API_KEY=sk-...  LLM_BASE_URL=https://api.openai.com/v1  LLM_MODEL=gpt-4o-mini
    # Option B (OpenRouter — free models, OpenAI-compatible):
    #   OPENROUTER_API_KEY=sk-or-...  (set as a Secret; OPENROUTER_MODEL optional)
    # Option C (HF Serverless Inference — free, rate-limited, subject to credits):
    #   HF_TOKEN=hf_...  (auto-available in HF Spaces; set as a Secret)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    openrouter_api_key: str = ""
    # A currently-available free OpenRouter model. Override with OPENROUTER_MODEL.
    # (llama-3.1-8b-instruct:free was retired; 3.3-70b:free is free + strong.)
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    hf_token: str = ""
    # Default to an ungated, inference-providers-served instruct model so a basic
    # free HF token works out of the box. Llama/Mistral are gated and 403 without
    # license acceptance. Override with HF_LLM_MODEL if you have access to others.
    hf_llm_model: str = "Qwen/Qwen2.5-7B-Instruct"

    @property
    def llm_credentials(self) -> tuple[str, str, str] | None:
        """Returns (base_url, api_key, model) or None when no LLM is configured.
        Priority: explicit LLM_API_KEY → OpenRouter → HF Inference."""
        if self.llm_api_key:
            return (self.llm_base_url, self.llm_api_key, self.llm_model)
        if self.openrouter_api_key:
            return (
                "https://openrouter.ai/api/v1",
                self.openrouter_api_key,
                self.openrouter_model,
            )
        if self.hf_token:
            return (
                "https://router.huggingface.co/v1",
                self.hf_token,
                self.hf_llm_model,
            )
        return None

    # ── File Storage — Cloudflare R2 (S3-compatible) ─────────────────────────
    # Stage 1: set USE_R2_STORAGE=true + all R2_* vars to store PDFs in R2
    # Falls back to local disk when false (fine for Render ephemeral storage)
    use_r2_storage: bool = False
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "uil-papers"
    # R2 endpoint is derived from account_id; override if needed
    r2_endpoint_url: str = ""

    upload_dir: str = "uploads"

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 5

    @property
    def effective_r2_endpoint(self) -> str:
        if self.r2_endpoint_url:
            return self.r2_endpoint_url
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"


settings = Settings()
