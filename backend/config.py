"""Shared model configuration; process environment overrides backend/.env."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'), override=False)


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
    llm_model: str = os.getenv('LLM_MODEL', 'qwen3.6:35b-a3b')
    embedding_model: str = os.getenv('EMBEDDING_MODEL', 'qwen3-embedding:4b-q4_K_M')
    embedding_dim: int = int(os.getenv('EMBEDDING_DIM', '2560'))
    database_url: str = os.getenv('DATABASE_URL', '')
    timeout_seconds: float = float(os.getenv('OLLAMA_TIMEOUT_SECONDS', '300'))
    llm_num_batch: int = int(os.getenv('LLM_NUM_BATCH', '64'))


settings = Settings()
if settings.embedding_dim <= 0 or settings.timeout_seconds <= 0:
    raise ValueError('Embedding dimension and timeout must be positive')
if settings.llm_num_batch <= 0:
    raise ValueError('LLM_NUM_BATCH must be positive')
