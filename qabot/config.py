from typing import List, Optional

from pydantic import BaseSettings, AnyUrl


class Settings(BaseSettings):
    OPENAI_API_KEY: str

    QABOT_DATABASE_URI: Optional[str] = None
    QABOT_CACHE_DATABASE_URI = "duckdb:///llm-cache.db"

    QABOT_TABLES: Optional[List[str]]
