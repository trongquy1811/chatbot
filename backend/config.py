from functools import lru_cache
import json
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./data/docanalyzer.db"
    data_dir: Path = Path("data")

    # Qdrant Vector Store
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "documents_v1"
    qdrant_memory_collection: str = "memories_v1"

    # Redis Cache & Sessions
    redis_url: str = ""

    # Security & Auth
    api_keys_json: str = '{"sec_tok_0123456789abcdef0123456789": "demo_user"}'

    # Google Gemini AI
    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "models/gemini-embedding-001"

    # Limits & Execution Controls (Harness Guardrails)
    max_upload_mb: int = Field(default=10, ge=1, le=50)
    max_pdf_pages: int = Field(default=30, ge=1, le=200)
    max_chunks: int = Field(default=500, ge=1, le=2000)
    max_tool_rounds: int = Field(default=3, ge=1, le=6)
    llm_timeout: int = Field(default=45, ge=5, le=120)
    max_retries: int = Field(default=1, ge=0, le=5)
    ocr_pdf_images: bool = Field(default=False)

    def keys(self) -> dict[str, str]:
        """Validate and return parsed API tokens mapping to owner identities."""
        try:
            keys = json.loads(self.api_keys_json)
        except Exception as exc:
            raise ValueError(
                "API_KEYS_JSON must be a valid JSON object string"
            ) from exc

        invalid = (
            not isinstance(keys, dict)
            or not keys
            or any(
                not isinstance(token, str)
                or len(token) < 24
                or not isinstance(owner, str)
                or not owner
                for token, owner in keys.items()
            )
        )

        if invalid:
            raise ValueError(
                "API_KEYS_JSON must map tokens (24+ characters) to user IDs"
            )

        return keys


@lru_cache()
def get_settings() -> Settings:
    return Settings()
