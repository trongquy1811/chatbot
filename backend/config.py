from functools import lru_cache
import json
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for stable resolution of .env and data directory
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8-sig",  # Supports both UTF-8 and UTF-8 BOM from PowerShell
        extra="ignore",
    )

    # Database
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'docanalyzer.db'}"
    data_dir: Path = BASE_DIR / "data"

    # Qdrant Vector Store
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "documents_v1"
    qdrant_memory_collection: str = "memories_v1"

    # Redis Cache & Sessions
    redis_url: str = ""

    # Security & Auth (No hardcoded default token)
    api_keys_json: str = ""

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
        if not self.api_keys_json or not self.api_keys_json.strip():
            raise ValueError(
                "Biến API_KEYS_JSON chưa được thiết lập trong file .env hoặc môi trường."
            )

        try:
            parsed = json.loads(self.api_keys_json)
        except Exception as exc:
            raise ValueError(
                f"API_KEYS_JSON không phải là chuỗi JSON hợp lệ: {exc}"
            ) from exc

        if not isinstance(parsed, dict) or not parsed:
            raise ValueError(
                'API_KEYS_JSON phải là một JSON Object dạng: {"<token_24_ky_tu_tro_len>": "<user_id>"}'
            )

        for token, owner in parsed.items():
            if not isinstance(token, str) or len(token) < 24:
                raise ValueError(
                    f"Token '{token[:6]}...' không hợp lệ. Mỗi token bắt buộc phải là chuỗi từ 24 ký tự trở lên."
                )
            if not isinstance(owner, str) or not owner.strip():
                raise ValueError(
                    f"User ID liên kết với token '{token[:6]}...' không được để trống."
                )

        return parsed


@lru_cache()
def get_settings() -> Settings:
    return Settings()
